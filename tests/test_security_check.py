from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def scan(contents: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "docs").mkdir()
        (root / "docs" / "checked.txt").write_text(contents, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "security_check.py"), "--root", str(root)],
            text=True,
            capture_output=True,
            check=False,
        )


class SecurityCheckTests(unittest.TestCase):
    def test_rejects_sensitive_link_and_credential_forms(self):
        cases = {
            "node link": "v" + "less://example.invalid/node",
            "subscription token": "subscription" + "_token=" + "abcdefghijklmnop",
            "private key": "-----BEGIN " + "PRIVATE KEY-----",
            "realistic UUID": "11111111-2222-" + "4333-8444-555555555555",
            "GraphQL password variable": "variables: {" + '"pass' + 'word": "not-a-real-secret"}',
            "DAED password value": "DAED " + "Password: " + "temporary-value",
            "DAED sentinel": "SENTINEL_" + "DAED_PASSWORD_DO_NOT_RENDER",
        }
        for label, contents in cases.items():
            with self.subTest(label=label):
                result = scan(contents)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(label, result.stdout)

    def test_allows_documented_inert_examples(self):
        result = scan("example.com\nAA:BB:CC:DD:EE:FF\n00000000-0000-0000-0000-000000000000\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_inline_allow_marker_cannot_hide_a_production_credential(self):
        result = scan("v" + "less://example.invalid/node SECURITY-SCAN-ALLOW\n")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("node link", result.stdout)


if __name__ == "__main__":
    unittest.main()
