#!/usr/bin/env python3
"""Regression tests for the pinned dae-wing SQLite database patch."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).parents[2]
PATCHER = ROOT / "scripts" / "patch_daed_database.py"
FIXTURE_ROOT = Path(__file__).with_name("fixtures") / "daed_database"
FIXTURE_MANIFEST = FIXTURE_ROOT / "manifest.json"
PINNED_SOURCE = (
    "https://github.com/daeuniverse/dae-wing/tree/"
    "dc503088945812c11235b35362d2bfa1a4c3bdf0"
)


class DaedDatabasePatchTests(unittest.TestCase):
    def copy_fixture(self, root: Path) -> tuple[Path, Path]:
        manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["source"], PINNED_SOURCE)
        expected = manifest["files"]
        self.assertEqual(
            set(expected), {"wing/db/db.go", "wing/graphql/mutation.go"}
        )
        for relative, expected_digest in expected.items():
            fixture = FIXTURE_ROOT / relative
            self.assertTrue(fixture.is_file(), f"pinned fixture is missing: {relative}")
            self.assertEqual(
                sha256(fixture.read_bytes()).hexdigest(),
                expected_digest,
                f"pinned fixture diverged: {relative}",
            )
        shutil.copytree(FIXTURE_ROOT / "wing", root / "wing")
        return root / "wing" / "db" / "db.go", root / "wing" / "graphql" / "mutation.go"

    def create_user_body(self, source: str) -> str:
        signature = "func (r *MutationResolver) CreateUser"
        start = source.find(signature)
        self.assertNotEqual(start, -1, "CreateUser is missing")
        body_marker = "}) (token string, err error) {"
        marker = source.find(body_marker, start)
        self.assertNotEqual(marker, -1, "CreateUser must have named token and err returns")
        opening_brace = marker + len(body_marker) - 1
        depth = 0
        for position in range(opening_brace, len(source)):
            if source[position] == "{":
                depth += 1
            elif source[position] == "}":
                depth -= 1
                if depth == 0:
                    return source[opening_brace + 1 : position]
        self.fail("CreateUser has unbalanced braces")

    def assert_create_user_transaction_safety(self, source: str) -> None:
        body = self.create_user_body(source)
        self.assertRegex(
            body,
            re.compile(
                r"tx := db\.BeginTx\(context\.TODO\(\)\)\n"
                r"\tif err = tx\.Error; err != nil \{\n"
                r'\t\treturn "", err\n'
                r"\t\}",
            ),
            "CreateUser must return the initial transaction error",
        )
        self.assertRegex(
            body,
            re.compile(
                r"defer func\(\) \{\n"
                r"\t\tif err == nil \{\n"
                r"\t\t\terr = tx\.Commit\(\)\.Error\n"
                r"\t\t\} else \{\n"
                r"\t\t\ttx\.Rollback\(\)\n"
                r"\t\t\}\n"
                r"\t\}\(\)",
            ),
            "CreateUser must assign commit errors to its named err return",
        )

    def run_patcher(self, source_root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PATCHER), str(source_root)],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_patches_pinned_database_layout_with_serialized_sqlite_and_checked_user_transaction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path, mutation_path = self.copy_fixture(root)

            result = self.run_patcher(root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            patched_db = db_path.read_text(encoding="utf-8")
            self.assertEqual(patched_db.count("sqlDB.SetMaxOpenConns(1)"), 1)
            self.assertEqual(patched_db.count("sqlDB.SetMaxIdleConns(1)"), 1)
            self.assertEqual(
                patched_db.count('sqlDB.Exec("PRAGMA busy_timeout = 10000")'), 1
            )

            create_user = mutation_path.read_text(encoding="utf-8")
            self.assertIn("if err = tx.Error; err != nil", create_user)
            self.assertIn("err = tx.Commit().Error", create_user)
            self.assert_create_user_transaction_safety(create_user)

    def test_second_run_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path, mutation_path = self.copy_fixture(root)

            first = self.run_patcher(root)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            first_contents = (db_path.read_bytes(), mutation_path.read_bytes())

            second = self.run_patcher(root)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual((db_path.read_bytes(), mutation_path.read_bytes()), first_contents)

    def test_unknown_upstream_layout_fails_closed_without_partial_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path, mutation_path = self.copy_fixture(root)
            db_source = db_path.read_text(encoding="utf-8")
            changed_source = db_source.replace(
                "\tdb, err = gorm.Open(sqlite.Open(path), &gorm.Config{\n",
                "\tdatabase, err = gorm.Open(sqlite.Open(path), &gorm.Config{\n",
                1,
            )
            self.assertNotEqual(changed_source, db_source)
            db_path.write_text(changed_source, encoding="utf-8", newline="\n")
            original = (db_path.read_bytes(), mutation_path.read_bytes())

            result = self.run_patcher(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((db_path.read_bytes(), mutation_path.read_bytes()), original)

    def test_partially_patched_source_fails_closed_without_writing_either_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path, mutation_path = self.copy_fixture(root)
            original_mutation = mutation_path.read_bytes()
            patched = self.run_patcher(root)
            self.assertEqual(patched.returncode, 0, patched.stdout + patched.stderr)
            mutation_path.write_bytes(original_mutation)
            original = (db_path.read_bytes(), mutation_path.read_bytes())

            result = self.run_patcher(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("partially database-patched", result.stderr)
            self.assertEqual((db_path.read_bytes(), mutation_path.read_bytes()), original)

    def test_create_user_commit_check_cannot_be_satisfied_by_another_function(self):
        source = (FIXTURE_ROOT / "wing" / "graphql" / "mutation.go").read_text(
            encoding="utf-8"
        )
        source = source.replace(
            "\ttx := db.BeginTx(context.TODO())\n",
            "\ttx := db.BeginTx(context.TODO())\n"
            "\tif err = tx.Error; err != nil {\n"
            "\t\treturn \"\", err\n"
            "\t}\n",
            1,
        )
        source += """
func unrelated() (err error) {
	if err == nil {
		err = tx.Commit().Error
	} else {
		tx.Rollback()
	}
	return err
}
"""

        with self.assertRaisesRegex(AssertionError, "CreateUser must assign"):
            self.assert_create_user_transaction_safety(source)


if __name__ == "__main__":
    unittest.main()
