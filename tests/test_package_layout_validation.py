from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]

DASHBOARD_FILES = (
    "packages/athena-runtime/files/usr/lib/athena/dashboard.sh",
    "packages/luci-app-athena/htdocs/luci-static/resources/athena/chart.js",
    "packages/luci-app-athena/htdocs/luci-static/resources/athena/dashboard.css",
    "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/dashboard.js",
    "packages/luci-app-athena/root/usr/share/luci/menu.d/zz-athena-dashboard.json",
)


def write_minimum_layout(root: Path, runtime_makefile: str, luci_makefile: str) -> None:
    files = {
        "packages/athena-runtime/Makefile": runtime_makefile,
        "packages/luci-app-athena/Makefile": luci_makefile,
        "packages/athena-runtime/files/usr/bin/athena-setup": "#!/bin/sh\n",
        "packages/athena-runtime/files/usr/bin/athena-iot": "#!/bin/sh\n",
        "packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.conf": (
            "location /athena-daed/ {}\n"
        ),
        "packages/athena-runtime/files/usr/lib/athena/dashboard.sh": "#!/bin/sh\n",
        "packages/luci-app-athena/htdocs/luci-static/resources/athena/chart.js": (
            "'use strict';\n"
        ),
        "packages/luci-app-athena/htdocs/luci-static/resources/athena/dashboard.css": (
            ".athena-dashboard {}\n"
        ),
        "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/dashboard.js": (
            "'use strict';\n"
        ),
        "packages/luci-app-athena/root/usr/share/luci/menu.d/zz-athena-dashboard.json": (
            '{"admin/status/overview":{"action":{"type":"view","path":"athena/dashboard"}},'
            '"admin/services/athena/status":{"action":{"type":"view","path":"athena/dashboard"}}}\n'
        ),
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def validate(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "verify_package_layout.py"),
            "--root",
            str(root),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


class PackageLayoutValidationTests(unittest.TestCase):
    def test_accepts_complete_dashboard_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_minimum_layout(
                root,
                "$(eval $(call BuildPackage,athena-runtime))\n",
                "# call BuildPackage - OpenWrt buildroot signature\n"
                "include $(TOPDIR)/feeds/luci/luci.mk\n",
            )

            result = validate(root)

            self.assertEqual(result.returncode, 0, result.stdout)

    def test_rejects_each_missing_dashboard_file(self) -> None:
        for relative in DASHBOARD_FILES:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                write_minimum_layout(
                    root,
                    "$(eval $(call BuildPackage,athena-runtime))\n",
                    "# call BuildPackage - OpenWrt buildroot signature\n"
                    "include $(TOPDIR)/feeds/luci/luci.mk\n",
                )
                (root / relative).unlink()

                result = validate(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(relative, result.stdout)

    def test_rejects_dashboard_menu_that_does_not_override_overview(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_minimum_layout(
                root,
                "$(eval $(call BuildPackage,athena-runtime))\n",
                "# call BuildPackage - OpenWrt buildroot signature\n"
                "include $(TOPDIR)/feeds/luci/luci.mk\n",
            )
            menu = root / DASHBOARD_FILES[-1]
            menu.write_text("{}", encoding="utf-8")

            result = validate(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("admin/status/overview", result.stdout)

    def test_rejects_dashboard_write_or_external_url(self) -> None:
        for token in ("uci.commit", "https://example.com/chart.js"):
            with self.subTest(token=token), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                write_minimum_layout(
                    root,
                    "$(eval $(call BuildPackage,athena-runtime))\n",
                    "# call BuildPackage - OpenWrt buildroot signature\n"
                    "include $(TOPDIR)/feeds/luci/luci.mk\n",
                )
                dashboard = root / DASHBOARD_FILES[3]
                dashboard.write_text(token, encoding="utf-8")

                result = validate(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("forbidden", result.stdout)

    def test_rejects_luci_package_missing_openwrt_scan_signature(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_minimum_layout(
                root,
                "$(eval $(call BuildPackage,athena-runtime))\n",
                "include $(TOPDIR)/feeds/luci/luci.mk\n",
            )

            result = validate(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not discoverable by OpenWrt package scan", result.stdout)

    def test_rejects_optional_gnu_archive_dependencies_from_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_minimum_layout(
                root,
                "DEPENDS:=+busybox +tar +gzip\n"
                "$(eval $(call BuildPackage,athena-runtime))\n",
                "# call BuildPackage - OpenWrt buildroot signature\n"
                "include $(TOPDIR)/feeds/luci/luci.mk\n",
            )

            result = validate(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must use base BusyBox tar/gzip applets", result.stdout)


if __name__ == "__main__":
    unittest.main()
