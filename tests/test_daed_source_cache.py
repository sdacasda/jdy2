from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import tests.test_daed_source_assembly as assembly


ROOT = Path(__file__).parents[1]
VERIFIER = ROOT / "scripts" / "verify_daed_source_cache.py"


class DaedSourceCacheTests(unittest.TestCase):
    def write_archive(self, archive: Path, *, database_patched: bool) -> None:
        assembly.DaedSourceAssemblyTests()._write_cache_archive(
            archive, database_patched=database_patched
        )

    def test_cache_verifier_rejects_archive_without_database_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "daed-src-test.tar.gz"
            manifest = root / "assembly-manifest.json"
            self.write_archive(archive, database_patched=False)

            result = subprocess.run(
                [
                    sys.executable,
                    str(VERIFIER),
                    "--archive", str(archive),
                    "--manifest", str(manifest),
                    "--cache-id", "cache-v1",
                    "--pin", "DAED_COMMIT=" + "a" * 40,
                    "--pin", "WEB_PATCH_SHA256=" + "b" * 64,
                    "--pin", "DATABASE_PATCH_SHA256=" + "c" * 64,
                    "--write",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("database patch", result.stderr)

    def test_cache_manifest_write_requires_both_patch_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "daed-src-test.tar.gz"
            self.write_archive(archive, database_patched=True)

            for missing_pin in ("WEB_PATCH_SHA256", "DATABASE_PATCH_SHA256"):
                with self.subTest(missing_pin=missing_pin):
                    manifest = root / f"{missing_pin}.json"
                    pins = [
                        "DAED_COMMIT=" + "a" * 40,
                        "WEB_PATCH_SHA256=" + "b" * 64,
                        "DATABASE_PATCH_SHA256=" + "c" * 64,
                    ]
                    pins = [pin for pin in pins if not pin.startswith(missing_pin + "=")]
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(VERIFIER),
                            "--archive", str(archive),
                            "--manifest", str(manifest),
                            "--cache-id", "cache-v1",
                            *(argument for pin in pins for argument in ("--pin", pin)),
                            "--write",
                        ],
                        text=True,
                        capture_output=True,
                        check=False,
                    )

                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(missing_pin, result.stderr)
                    self.assertFalse(manifest.exists())

    def test_cache_manifest_write_rejects_non_sha256_patch_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "daed-src-test.tar.gz"
            manifest = root / "assembly-manifest.json"
            self.write_archive(archive, database_patched=True)

            result = subprocess.run(
                [
                    sys.executable,
                    str(VERIFIER),
                    "--archive", str(archive),
                    "--manifest", str(manifest),
                    "--cache-id", "cache-v1",
                    "--pin", "DAED_COMMIT=" + "a" * 40,
                    "--pin", "WEB_PATCH_SHA256=not-a-sha256",
                    "--pin", "DATABASE_PATCH_SHA256=" + "c" * 64,
                    "--write",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("WEB_PATCH_SHA256", result.stderr)
            self.assertFalse(manifest.exists())


if __name__ == "__main__":
    unittest.main()
