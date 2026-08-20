import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_NAMES = (
    "libwrt",
    "daede",
    "vmlinux_btf",
    "athena_led",
    "golang",
    "argon",
    "argon_config",
)


def run(script: str, root: pathlib.Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / script), "--root", str(root), *extra],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


class ProjectValidationTests(unittest.TestCase):
    def test_public_release_tree_does_not_require_internal_superpowers_docs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for relative in ("PROJECT.json", "SOURCES.lock.json"):
                shutil.copyfile(ROOT / relative, root / relative)

            result = run("scripts/verify_project.py", root, "--allow-incomplete")

            self.assertEqual(result.returncode, 0, result.stdout)

    def test_ignores_local_superpowers_but_scans_production_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for relative in (
                "PROJECT.json",
                "SOURCES.lock.json",
                "docs/superpowers/specs/2026-07-25-athena-v19-design.md",
                "docs/superpowers/plans/2026-07-25-athena-v19-implementation.md",
            ):
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, destination)

            invalid = b"{{LOCAL_PLACEHOLDER}}\r\n<<<<<<< local\r\n=======\r\n>>>>>>> review\r\n"
            local_review = root / ".superpowers" / "sdd" / "review.diff"
            local_review.parent.mkdir(parents=True)
            local_review.write_bytes(invalid)

            ignored = run("scripts/verify_project.py", root, "--allow-incomplete")
            self.assertEqual(ignored.returncode, 0, ignored.stdout)

            production = root / "packages" / "review.diff"
            production.parent.mkdir(parents=True)
            production.write_bytes(invalid)
            rejected = run("scripts/verify_project.py", root, "--allow-incomplete")
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("packages", rejected.stdout)

    def test_lock_rejects_moving_ref(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            lock = {
                name: {"repository": "https://example.com/repo.git", "commit": "main"}
                for name in SOURCE_NAMES
            }
            (root / "SOURCES.lock.json").write_text(json.dumps(lock), encoding="utf-8")
            result = run("scripts/verify_project.py", root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("40-character commit", result.stdout)

    def test_security_scan_rejects_proxy_link_without_echoing_secret(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            secret = "vless" + "://user-secret@example.com:443"
            (root / "bad.txt").write_text(secret, encoding="utf-8")
            result = run("scripts/security_check.py", root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("node link", result.stdout)
            self.assertNotIn(secret, result.stdout)

    def test_current_repository_validates(self) -> None:
        result = run("scripts/verify_project.py", ROOT, "--allow-incomplete")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_legacy_project_check_uses_the_current_v19_validator(self) -> None:
        result = run("scripts/project_check.py", ROOT)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Athena v19 project structure is valid", result.stdout)

    def test_rejects_retired_template_token_in_production_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            retired = root / "packages/athena-runtime/Makefile"
            retired.parent.mkdir(parents=True)
            retired.write_text("/usr/share/athena/templates\n", encoding="utf-8")

            result = run("scripts/verify_project.py", root, "--allow-incomplete")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("retired template reference", result.stdout)
            self.assertIn("packages/athena-runtime/Makefile", result.stdout)

    def test_daed_lock_declares_expected_package_version(self) -> None:
        lock = json.loads((ROOT / "SOURCES.lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["daede"].get("package_version"), "2026.07.26-r1")

    def test_current_repository_has_no_secrets(self) -> None:
        result = run("scripts/security_check.py", ROOT)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_source_archive_excludes_internal_superpowers_work_products(self) -> None:
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn(".superpowers/ export-ignore", attributes.splitlines())


if __name__ == "__main__":
    unittest.main()
