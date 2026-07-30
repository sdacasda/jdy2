from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).parents[1]

DASHBOARD_ROOTFS_FILES = (
    "usr/lib/athena/dashboard.sh",
    "www/luci-static/resources/athena/chart.js",
    "www/luci-static/resources/athena/dashboard.css",
    "www/luci-static/resources/view/athena/dashboard.js",
    "usr/share/luci/menu.d/zz-athena-dashboard.json",
)


class FirmwareInspectionTests(unittest.TestCase):
    def make_fixture(self, root: Path, dashboard_files: bool = False):
        openwrt = root / "openwrt"
        target = openwrt / "bin/targets/qualcommax/ipq60xx"
        target.mkdir(parents=True)
        (target / "libwrt-jdcloud_re-cs-02-initramfs-uImage.itb").write_bytes(
            b"initramfs"
        )
        (target / "libwrt-jdcloud_re-cs-02-squashfs-sysupgrade.bin").write_bytes(
            b"sysupgrade"
        )
        manifest_packages = (
            "daed",
            "luci-app-daede",
            "athena-runtime",
            "luci-app-athena",
            "luci-theme-argon",
            "luci-app-argon-config",
            "nginx-ssl",
            "uhttpd",
        )
        (target / "libwrt.manifest").write_text(
            "".join(f"{package} - 1\n" for package in manifest_packages),
            encoding="utf-8",
        )
        rootfs = openwrt / "build_dir/target-aarch64/root-qualcommax"
        rootfs.mkdir(parents=True)
        persistent = rootfs / "jdcloud_re-cs-02-uImage.itb"
        persistent.write_bytes(b"persistent-kernel")
        if dashboard_files:
            for relative in DASHBOARD_ROOTFS_FILES:
                path = rootfs / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("dashboard\n", encoding="utf-8")
        return openwrt, rootfs

    def inspect(self, openwrt: Path, output: Path):
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/inspect_firmware.py"),
                "--openwrt",
                str(openwrt),
                "--output",
                str(output),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_nginx_ssl_satisfies_the_nginx_runtime_requirement(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, _ = self.make_fixture(root, dashboard_files=True)
            output = root / "inspection"

            result = self.inspect(openwrt, output)

            report = json.loads(
                (output / "firmware-inspection.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report["missing_packages"], [])
            self.assertTrue(report["dashboard_files"]["checked"])
            self.assertEqual(report["dashboard_files"]["missing"], [])

    def test_missing_dashboard_file_fails_when_rootfs_is_available(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, rootfs = self.make_fixture(root, dashboard_files=True)
            (rootfs / "www/luci-static/resources/view/athena/dashboard.js").unlink()
            output = root / "inspection"

            result = self.inspect(openwrt, output)
            report = json.loads(
                (output / "firmware-inspection.json").read_text(encoding="utf-8")
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(report["dashboard_files"]["checked"])
            self.assertIn(
                "/www/luci-static/resources/view/athena/dashboard.js",
                report["dashboard_files"]["missing"],
            )

    def test_dashboard_check_is_skipped_when_rootfs_is_not_available(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, rootfs = self.make_fixture(root, dashboard_files=True)
            shutil.rmtree(rootfs)
            output = root / "inspection"

            result = self.inspect(openwrt, output)
            report = json.loads(
                (output / "firmware-inspection.json").read_text(encoding="utf-8")
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(report["dashboard_files"]["checked"])
            self.assertEqual(report["dashboard_files"]["missing"], [])


if __name__ == "__main__":
    unittest.main()
