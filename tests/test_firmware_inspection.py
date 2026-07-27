from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).parents[1]


class FirmwareInspectionTests(unittest.TestCase):
    def test_nginx_ssl_satisfies_the_nginx_runtime_requirement(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt = root / "openwrt"
            target = openwrt / "bin/targets/qualcommax/ipq60xx"
            target.mkdir(parents=True)
            (target / "libwrt-jdcloud_re-cs-02-initramfs-uImage.itb").write_bytes(
                b"initramfs"
            )
            (
                target
                / "libwrt-jdcloud_re-cs-02-squashfs-sysupgrade.bin"
            ).write_bytes(b"sysupgrade")
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
            persistent = (
                openwrt
                / "build_dir/target-aarch64/root-qualcommax"
                / "jdcloud_re-cs-02-uImage.itb"
            )
            persistent.parent.mkdir(parents=True)
            persistent.write_bytes(b"persistent-kernel")
            output = root / "inspection"

            result = subprocess.run(
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

            report = json.loads(
                (output / "firmware-inspection.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report["missing_packages"], [])


if __name__ == "__main__":
    unittest.main()
