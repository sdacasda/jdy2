from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]

class PermissionResilienceTests(unittest.TestCase):
    def test_workflow_restores_windows_upload_permissions(self):
        workflow = (ROOT / ".github/workflows/build-athena-v19.yml").read_text(encoding="utf-8")
        self.assertIn("chmod +x packages/athena-runtime/files/usr/bin/athena-*", workflow)
        self.assertIn("chmod +x tests/runtime/*.sh", workflow)

    def test_package_install_forces_runtime_executables(self):
        makefile = (ROOT / "packages/athena-runtime/Makefile").read_text(encoding="utf-8")
        self.assertIn("chmod 0755", makefile)
        self.assertIn("$(1)/usr/bin/athena-*", makefile)
        self.assertIn("$(1)/usr/libexec/rpcd/athena", makefile)

if __name__ == "__main__":
    unittest.main()
