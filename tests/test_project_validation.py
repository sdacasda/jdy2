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

    def test_current_repository_has_no_secrets(self) -> None:
        result = run("scripts/security_check.py", ROOT)
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
