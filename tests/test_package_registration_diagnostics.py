import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def bash_path(path: Path) -> str:
    if os.name != "nt":
        return str(path)
    candidates = (
        shutil.which("cygpath"),
        r"D:\Git\usr\bin\cygpath.exe",
        r"C:\Program Files\Git\usr\bin\cygpath.exe",
    )
    cygpath = next(value for value in candidates if value and Path(value).is_file())
    return subprocess.check_output(
        [cygpath, "-u", str(path)], text=True
    ).strip()


class PackageRegistrationDiagnosticsTests(unittest.TestCase):
    def test_captures_actual_and_recomputed_package_kconfig(self) -> None:
        """A stale generated Kconfig must remain diagnosable in the Artifact."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            openwrt = root / "openwrt"
            output = root / "diagnostics"
            (openwrt / "tmp" / "info").mkdir(parents=True)
            (openwrt / "scripts").mkdir(parents=True)

            (openwrt / "tmp" / ".packageinfo").write_text(
                "Package: athena-runtime\n"
                "Depends: +libc +curl\n"
                "\n"
                "Package: luci-app-athena\n"
                "Depends: +athena-runtime\n",
                encoding="utf-8",
            )
            (openwrt / "tmp" / ".config-package.in").write_text(
                "config PACKAGE_curl\n\ttristate \"curl\"\n",
                encoding="utf-8",
            )
            (openwrt / "tmp" / "info" / ".files-packageinfo-test").write_text(
                "package/custom/athena-runtime/Makefile\n", encoding="utf-8"
            )
            (openwrt / "scripts" / "package-metadata.pl").write_text(
                "#!/usr/bin/perl\n"
                "print \"config PACKAGE_athena-runtime\\n"
                "\\ttristate \\\"athena-runtime\\\"\\n"
                "config PACKAGE_luci-app-athena\\n"
                "\\ttristate \\\"luci-app-athena\\\"\\n\";\n",
                encoding="utf-8",
            )

            script = ROOT / "scripts" / "capture_package_registration.sh"
            candidates = (
                shutil.which("bash"),
                r"D:\Git\bin\bash.exe",
                r"C:\Program Files\Git\bin\bash.exe",
            )
            bash = next(
                value for value in candidates if value and Path(value).is_file()
            )
            command = [
                bash,
                "-lc",
                "'{}' '{}' '{}'".format(
                    bash_path(script),
                    bash_path(openwrt),
                    bash_path(output),
                ),
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(
                (output / "actual.config-package.in").read_text(encoding="utf-8"),
                "config PACKAGE_curl\n\ttristate \"curl\"\n",
            )
            recomputed = (output / "recomputed.config-package.in").read_text(
                encoding="utf-8"
            )
            self.assertIn("config PACKAGE_athena-runtime", recomputed)
            self.assertIn("config PACKAGE_luci-app-athena", recomputed)
            summary = (output / "registration-summary.txt").read_text(
                encoding="utf-8"
            )
            self.assertIn("actual PACKAGE_athena-runtime: missing", summary)
            self.assertIn("recomputed PACKAGE_athena-runtime: present", summary)
            self.assertTrue(
                (output / "info" / ".files-packageinfo-test").is_file()
            )


if __name__ == "__main__":
    unittest.main()
