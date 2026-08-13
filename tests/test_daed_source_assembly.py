from hashlib import sha256
from pathlib import Path
import gzip
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).parents[1]
VALID_PATCH_PIN_ARGUMENTS = [
    "--pin", "WEB_PATCH_SHA256=" + "c" * 64,
    "--pin", "DATABASE_PATCH_SHA256=" + "d" * 64,
]


class DaedSourceAssemblyTests(unittest.TestCase):
    def _write_cache_archive(
        self,
        archive: Path,
        *,
        embedded_endpoint: bool = True,
        static_endpoint: bytes = b"/athena-daed/graphql",
        include_static_css: bool = True,
        database_patched: bool = True,
    ):
        source_endpoint = b"/athena-daed/graphql"
        embedded_value = source_endpoint if embedded_endpoint else b"/graphql"
        database_source = (
            b'sqlDB.SetMaxOpenConns(1)\n'
            b'sqlDB.SetMaxIdleConns(1)\n'
            b'sqlDB.Exec("PRAGMA busy_timeout = 10000")\n'
            if database_patched
            else b"db.AutoMigrate()\n"
        )
        mutation_source = (
            b"if err = tx.Error; err != nil {}\n"
            b"err = tx.Commit().Error\n"
            if database_patched
            else b"tx := db.BeginTx(context.TODO())\ntx.Commit()\n"
        )
        files = {
            "daed-2026.07.26/wing/go.mod": b"module example.invalid/wing\n",
            "daed-2026.07.26/wing/db/db.go": database_source,
            "daed-2026.07.26/wing/graphql/mutation.go": mutation_source,
            "daed-2026.07.26/apps/web/src/constants/default.ts": source_endpoint,
            "daed-2026.07.26/apps/web/dist/index.html": (
                b'<link rel="icon" href="./logo.webp">'
                b'<script type="module" src="./assets/app.js"></script>'
                b'<link rel="stylesheet" href="./assets/app.css">'
            ),
            "daed-2026.07.26/apps/web/dist/logo.webp": b"RIFF-logo",
            "daed-2026.07.26/apps/web/dist/assets/app.js": (
                b"const endpoint='" + static_endpoint + b"';"
            ),
            "daed-2026.07.26/wing/webrender/web/index.html": b"<html></html>\n",
            "daed-2026.07.26/wing/webrender/web/assets/app.js.gz": gzip.compress(
                b"const endpoint='" + embedded_value + b"';", mtime=0
            ),
        }
        if include_static_css:
            files["daed-2026.07.26/apps/web/dist/assets/app.css"] = b"body{}"
        with tarfile.open(archive, "w:gz") as bundle:
            for name, payload in files.items():
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                info.mtime = 0
                bundle.addfile(info, io.BytesIO(payload))

    def test_cache_manifest_binds_pins_digest_and_embedded_web(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "daed-src-test.tar.gz"
            manifest = root / "assembly-manifest.json"
            self._write_cache_archive(archive)
            web_patch_hash = sha256(
                (ROOT / "scripts" / "patch_daed_web.py").read_bytes()
            ).hexdigest()
            database_patch_hash = sha256(
                (ROOT / "scripts" / "patch_daed_database.py").read_bytes()
            ).hexdigest()
            command = [
                sys.executable,
                str(ROOT / "scripts/verify_daed_source_cache.py"),
                "--archive", str(archive),
                "--manifest", str(manifest),
                "--cache-id", "cache-v1",
                "--pin", "DAED_COMMIT=" + "a" * 40,
                "--pin", "WING_COMMIT=" + "b" * 40,
                "--pin", "WEB_PATCH_SHA256=" + web_patch_hash,
                "--pin", "DATABASE_PATCH_SHA256=" + database_patch_hash,
            ]

            written = subprocess.run(
                command + ["--write"], text=True, capture_output=True, check=False
            )
            self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
            verified = subprocess.run(
                command, text=True, capture_output=True, check=False
            )
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)

            record = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(record["schema_version"], 2)
            self.assertEqual(record["pins"]["WEB_PATCH_SHA256"], web_patch_hash)
            self.assertEqual(
                record["pins"]["DATABASE_PATCH_SHA256"], database_patch_hash
            )
            self.assertEqual(record["static_web"]["file_count"], 4)
            self.assertEqual(len(record["static_web"]["tree_sha256"]), 64)
            self.assertEqual(
                [entry["path"] for entry in record["static_web"]["files"]],
                sorted(entry["path"] for entry in record["static_web"]["files"]),
            )

            archive.write_bytes(archive.read_bytes() + b"corrupt")
            rejected = subprocess.run(
                command, text=True, capture_output=True, check=False
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("digest mismatch", rejected.stderr)

    def test_cache_verifier_rejects_unpatched_embedded_web(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "daed-src-test.tar.gz"
            manifest = root / "assembly-manifest.json"
            self._write_cache_archive(archive, embedded_endpoint=False)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/verify_daed_source_cache.py"),
                    "--archive", str(archive),
                    "--manifest", str(manifest),
                    "--cache-id", "cache-v1",
                    "--pin", "DAED_COMMIT=" + "a" * 40,
                    *VALID_PATCH_PIN_ARGUMENTS,
                    "--write",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("embedded Web bundle", result.stderr)

    def test_cache_verifier_rejects_static_web_tree_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "daed-src-test.tar.gz"
            manifest = root / "assembly-manifest.json"
            self._write_cache_archive(archive)
            command = [
                sys.executable,
                str(ROOT / "scripts/verify_daed_source_cache.py"),
                "--archive", str(archive),
                "--manifest", str(manifest),
                "--cache-id", "cache-v1",
                "--pin", "DAED_COMMIT=" + "a" * 40,
                *VALID_PATCH_PIN_ARGUMENTS,
            ]
            written = subprocess.run(
                command + ["--write"], text=True, capture_output=True, check=False
            )
            self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
            record = json.loads(manifest.read_text(encoding="utf-8"))
            record["static_web"]["tree_sha256"] = "0" * 64
            manifest.write_text(json.dumps(record), encoding="utf-8")

            rejected = subprocess.run(
                command, text=True, capture_output=True, check=False
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("manifest does not match", rejected.stderr)

    def test_cache_verifier_rejects_static_web_file_list_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "daed-src-test.tar.gz"
            manifest = root / "assembly-manifest.json"
            self._write_cache_archive(archive)
            command = [
                sys.executable,
                str(ROOT / "scripts/verify_daed_source_cache.py"),
                "--archive", str(archive),
                "--manifest", str(manifest),
                "--cache-id", "cache-v1",
                "--pin", "DAED_COMMIT=" + "a" * 40,
                *VALID_PATCH_PIN_ARGUMENTS,
            ]
            written = subprocess.run(
                command + ["--write"], text=True, capture_output=True, check=False
            )
            self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
            record = json.loads(manifest.read_text(encoding="utf-8"))
            record["static_web"]["files"].pop()
            manifest.write_text(json.dumps(record), encoding="utf-8")

            rejected = subprocess.run(
                command, text=True, capture_output=True, check=False
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("manifest does not match", rejected.stderr)

    def test_cache_verifier_rejects_missing_static_web_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "daed-src-test.tar.gz"
            manifest = root / "assembly-manifest.json"
            self._write_cache_archive(archive, include_static_css=False)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/verify_daed_source_cache.py"),
                    "--archive", str(archive),
                    "--manifest", str(manifest),
                    "--cache-id", "cache-v1",
                    "--pin", "DAED_COMMIT=" + "a" * 40,
                    *VALID_PATCH_PIN_ARGUMENTS,
                    "--write",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("referenced asset is missing", result.stderr)

    def test_cache_verifier_rejects_static_web_browser_port(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "daed-src-test.tar.gz"
            manifest = root / "assembly-manifest.json"
            self._write_cache_archive(
                archive,
                static_endpoint=b"http://127.0.0.1:2023/graphql",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/verify_daed_source_cache.py"),
                    "--archive", str(archive),
                    "--manifest", str(manifest),
                    "--cache-id", "cache-v1",
                    "--pin", "DAED_COMMIT=" + "a" * 40,
                    *VALID_PATCH_PIN_ARGUMENTS,
                    "--write",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("browser-visible DAED port", result.stderr)

    def test_schema_one_manifest_is_not_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "daed-src-test.tar.gz"
            manifest = root / "assembly-manifest.json"
            self._write_cache_archive(archive)
            command = [
                sys.executable,
                str(ROOT / "scripts/verify_daed_source_cache.py"),
                "--archive", str(archive),
                "--manifest", str(manifest),
                "--cache-id", "cache-v1",
                "--pin", "DAED_COMMIT=" + "a" * 40,
                *VALID_PATCH_PIN_ARGUMENTS,
            ]
            written = subprocess.run(
                command + ["--write"], text=True, capture_output=True, check=False
            )
            self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
            record = json.loads(manifest.read_text(encoding="utf-8"))
            record["schema_version"] = 1
            manifest.write_text(json.dumps(record), encoding="utf-8")

            rejected = subprocess.run(
                command, text=True, capture_output=True, check=False
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("manifest does not match", rejected.stderr)

    def test_installer_copies_local_archive_and_pins_its_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_name = "daed-src-2026.07.26-test.tar.gz"
            archive = root / source_name
            archive.write_bytes(b"pinned daed source\n")
            makefile = root / "Makefile"
            makefile.write_text(
                "PKG_NAME:=daed\n"
                f"PKG_SOURCE:={source_name}\n"
                "PKG_SOURCE_URL:=https://example.invalid/pruned-release\n"
                f"PKG_HASH:={'0' * 64}\n",
                encoding="utf-8",
            )
            dl = root / "dl"
            provenance = root / "provenance.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/install_daed_source.py"),
                    "--makefile", str(makefile),
                    "--archive", str(archive),
                    "--dl-dir", str(dl),
                    "--provenance", str(provenance),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            expected_hash = sha256(archive.read_bytes()).hexdigest()
            self.assertEqual((dl / source_name).read_bytes(), archive.read_bytes())
            patched = makefile.read_text(encoding="utf-8")
            self.assertIn(f"PKG_HASH:={expected_hash}", patched)
            record = json.loads(provenance.read_text(encoding="utf-8"))
            self.assertEqual(record["source"], source_name)
            self.assertEqual(record["sha256"], expected_hash)

    def test_assembly_uses_immutable_pins_and_patches_web_before_build(self):
        path = ROOT / "scripts/assemble_daed_source.sh"
        self.assertTrue(path.is_file(), "DAED source assembly script is missing")
        script = path.read_text(encoding="utf-8")
        self.assertIn("ci/pins.env", script)
        self.assertIn("rev-parse HEAD", script)
        self.assertIn("immutable checkout mismatch", script)
        self.assertIn("scripts/patch_daed_web.py", script)
        self.assertIn("scripts/patch_daed_database.py", script)
        self.assertIn("DATABASE_PATCH_HASH", script)
        self.assertIn('"$PATCH_HASH" "$DATABASE_PATCH_HASH"', script)
        self.assertIn('"DATABASE_PATCH_SHA256=$DATABASE_PATCH_HASH"', script)
        self.assertLess(script.index("scripts/patch_daed_web.py"), script.index("pnpm build"))
        self.assertLess(
            script.index("scripts/patch_daed_database.py"),
            script.index("tar --numeric-owner"),
        )
        self.assertIn("compiled DAED Web does not contain the same-origin endpoint", script)
        self.assertIn("tar -tzf", script)
        self.assertIn("archive-contents.txt", script)
        self.assertIn("gzip -n", script)
        self.assertIn("assembly-manifest.json", script)
        self.assertIn("verify_daed_source_cache.py", script)
        self.assertIn("scripts/install_daed_web.py", script)
        self.assertIn("root/www/athena-daed", script)
        self.assertIn("root/usr/share/athena/daed-static-web.json", script)
        self.assertIn("static-web.json", script)
        self.assertLess(
            script.index("scripts/install_daed_web.py"),
            script.index("scripts/install_daed_source.py"),
        )
        self.assertIsNone(
            re.search(r"tar -xOzf[^\n]*\n\s*\| grep -q", script),
            "pipefail would treat tar SIGPIPE as an archive validation failure",
        )


if __name__ == "__main__":
    unittest.main()
