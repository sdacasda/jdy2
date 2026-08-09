from pathlib import Path
import gzip
import hashlib
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

WEB_ROOTFS_FILES = (
    "etc/nginx/conf.d/athena-daed.locations",
    "etc/uci-defaults/95-athena-web",
    "www/athena-recovery.html",
    "www/luci-static/resources/view/athena/daed-panel.js",
    "usr/share/luci/menu.d/luci-app-athena.json",
    "usr/bin/daed",
)


def static_web_record(files):
    entries = []
    digest = hashlib.sha256()
    for relative in sorted(files):
        payload = files[relative]
        sha256 = hashlib.sha256(payload).hexdigest()
        entries.append(
            {"path": relative, "size": len(payload), "sha256": sha256}
        )
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256.encode("ascii"))
        digest.update(b"\n")
    return {
        "schema": 1,
        "archive": "daed-test.tar.gz",
        "archive_sha256": "0" * 64,
        "root": "daed-test",
        "file_count": len(entries),
        "tree_sha256": digest.hexdigest(),
        "files": entries,
    }


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
            "uhttpd-mod-lua",
        )
        (target / "libwrt.manifest").write_text(
            "".join(f"{package} - 1\n" for package in manifest_packages),
            encoding="utf-8",
        )
        rootfs = openwrt / "build_dir/target-aarch64/root-qualcommax"
        rootfs.mkdir(parents=True)
        persistent = rootfs / "jdcloud_re-cs-02-uImage.itb"
        persistent.write_bytes(b"persistent-kernel")
        web_contents = {
            "etc/nginx/conf.d/athena-daed.locations": (
                "location = /athena-daed/graphql {\n"
                "    proxy_pass http://127.0.0.1:2023/graphql;\n"
                "    proxy_buffering off;\n"
                "}\n"
                "location /athena-daed/ {\n"
                "    root /www;\n"
                "    try_files $uri $uri/ /athena-daed/index.html;\n"
                "}\n"
            ),
            "etc/uci-defaults/95-athena-web": "delete uhttpd.main.listen_http\ndelete uhttpd.main.listen_https\nset daed.config.listen_addr='127.0.0.1:2023'\nset daed.config.enabled='0'\n",
            "www/athena-recovery.html": "<!doctype html><title>Athena recovery</title>\n",
            "www/luci-static/resources/view/athena/daed-panel.js": "src: '/athena-daed/'\n",
            "usr/share/luci/menu.d/luci-app-athena.json": "{}\n",
        }
        for relative, content in web_contents.items():
            path = rootfs / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        daed = rootfs / "usr/bin/daed"
        daed.parent.mkdir(parents=True, exist_ok=True)
        daed.write_bytes(b"ELF\x00/athena-daed/graphql\x00")
        static_files = {
            "index.html": (
                b'<!doctype html><link rel="icon" href="./logo.webp">'
                b'<link rel="stylesheet" href="./assets/index-def.css">'
                b'<script type="module" src="./assets/index-abc.js"></script>'
            ),
            "logo.webp": b"WEBP-logo",
            "assets/index-abc.js": b"const endpoint='/athena-daed/graphql';",
            "assets/index-def.css": b"body{background:#111}",
        }
        for relative, payload in static_files.items():
            path = rootfs / "www/athena-daed" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        provenance = rootfs / "usr/share/athena/daed-static-web.json"
        provenance.parent.mkdir(parents=True, exist_ok=True)
        provenance.write_text(
            json.dumps(static_web_record(static_files), indent=2) + "\n",
            encoding="utf-8",
        )
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
            self.assertTrue(report["web_integration"]["checked"])
            self.assertEqual(report["web_integration"]["missing"], [])
            self.assertEqual(report["web_integration"]["forbidden"], [])
            self.assertEqual(report["web_integration"]["daed_endpoint"], "same-origin")
            self.assertEqual(report["daed_static_ui"]["file_count"], 4)
            self.assertEqual(report["daed_static_ui"]["errors"], [])

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

    def test_missing_daed_locations_fails(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, rootfs = self.make_fixture(root, dashboard_files=True)
            (rootfs / "etc/nginx/conf.d/athena-daed.locations").unlink()
            output = root / "inspection"
            result = self.inspect(openwrt, output)
            report = json.loads((output / "firmware-inspection.json").read_text(encoding="utf-8"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("/etc/nginx/conf.d/athena-daed.locations", report["web_integration"]["missing"])

    def test_old_daed_http_context_file_fails(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, rootfs = self.make_fixture(root, dashboard_files=True)
            (rootfs / "etc/nginx/conf.d/athena-daed.conf").write_text("location /bad {}\n", encoding="utf-8")
            output = root / "inspection"
            result = self.inspect(openwrt, output)
            report = json.loads((output / "firmware-inspection.json").read_text(encoding="utf-8"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("/etc/nginx/conf.d/athena-daed.conf", report["web_integration"]["forbidden"])

    def test_missing_uhttpd_lua_runtime_fails(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, _ = self.make_fixture(root, dashboard_files=True)
            manifest = openwrt / "bin/targets/qualcommax/ipq60xx/libwrt.manifest"
            manifest.write_text(manifest.read_text(encoding="utf-8").replace("uhttpd-mod-lua - 1\n", ""), encoding="utf-8")
            output = root / "inspection"
            result = self.inspect(openwrt, output)
            report = json.loads((output / "firmware-inspection.json").read_text(encoding="utf-8"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("uhttpd-mod-lua", report["missing_packages"])

    def test_browser_visible_daed_port_in_binary_fails(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, rootfs = self.make_fixture(root, dashboard_files=True)
            (rootfs / "usr/bin/daed").write_bytes(b"ELF\x00:2023/graphql\x00")
            output = root / "inspection"
            result = self.inspect(openwrt, output)
            report = json.loads((output / "firmware-inspection.json").read_text(encoding="utf-8"))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(report["web_integration"]["daed_endpoint"], "browser-port")

    def test_same_origin_endpoint_in_gzip_embedded_web_passes(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, rootfs = self.make_fixture(root, dashboard_files=True)
            endpoint = b"/athena-daed/graphql"
            embedded = gzip.compress(b"const endpoint='" + endpoint + b"';", mtime=0)
            self.assertNotIn(endpoint, embedded)
            (rootfs / "usr/bin/daed").write_bytes(b"ELF\x00" + embedded + b"\x00EOF")
            output = root / "inspection"

            result = self.inspect(openwrt, output)
            report = json.loads(
                (output / "firmware-inspection.json").read_text(encoding="utf-8")
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report["web_integration"]["daed_endpoint"], "same-origin")

    def test_browser_port_in_gzip_embedded_web_fails(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, rootfs = self.make_fixture(root, dashboard_files=True)
            browser_port = b":2023/graphql"
            embedded = gzip.compress(b"const endpoint='" + browser_port + b"';", mtime=0)
            self.assertNotIn(browser_port, embedded)
            (rootfs / "usr/bin/daed").write_bytes(b"ELF\x00" + embedded + b"\x00EOF")
            output = root / "inspection"

            result = self.inspect(openwrt, output)
            report = json.loads(
                (output / "firmware-inspection.json").read_text(encoding="utf-8")
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(report["web_integration"]["daed_endpoint"], "browser-port")

    def test_firstboot_must_remove_primary_uhttpd_listener(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, rootfs = self.make_fixture(root, dashboard_files=True)
            defaults = rootfs / "etc/uci-defaults/95-athena-web"
            defaults.write_text(defaults.read_text(encoding="utf-8").replace("delete uhttpd.main.listen_http\n", ""), encoding="utf-8")
            output = root / "inspection"
            result = self.inspect(openwrt, output)
            report = json.loads((output / "firmware-inspection.json").read_text(encoding="utf-8"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("uhttpd-primary-listener", report["web_integration"]["forbidden"])

    def test_firstboot_requires_daed_loopback_default(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, rootfs = self.make_fixture(root, dashboard_files=True)
            defaults = rootfs / "etc/uci-defaults/95-athena-web"
            defaults.write_text(defaults.read_text(encoding="utf-8").replace("set daed.config.listen_addr='127.0.0.1:2023'\n", ""), encoding="utf-8")
            output = root / "inspection"
            result = self.inspect(openwrt, output)
            report = json.loads((output / "firmware-inspection.json").read_text(encoding="utf-8"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("daed-loopback-default", report["web_integration"]["missing"])

    def test_rejects_missing_daed_static_index(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, rootfs = self.make_fixture(root, dashboard_files=True)
            (rootfs / "www/athena-daed/index.html").unlink()
            output = root / "inspection"

            result = self.inspect(openwrt, output)
            report = json.loads((output / "firmware-inspection.json").read_text(encoding="utf-8"))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing:index.html", report["daed_static_ui"]["errors"])

    def test_rejects_missing_daed_index_reference(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, rootfs = self.make_fixture(root, dashboard_files=True)
            index = rootfs / "www/athena-daed/index.html"
            index.write_text(index.read_text(encoding="utf-8").replace("./logo.webp", "./missing.webp"), encoding="utf-8")
            output = root / "inspection"

            result = self.inspect(openwrt, output)
            report = json.loads((output / "firmware-inspection.json").read_text(encoding="utf-8"))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing-reference:missing.webp", report["daed_static_ui"]["errors"])

    def test_rejects_missing_daed_javascript(self):
        self._assert_static_file_rejected("assets/index-abc.js", "missing:assets/index-abc.js")

    def test_rejects_missing_daed_stylesheet(self):
        self._assert_static_file_rejected("assets/index-def.css", "missing:assets/index-def.css")

    def test_rejects_missing_daed_logo(self):
        self._assert_static_file_rejected("logo.webp", "missing:logo.webp")

    def _assert_static_file_rejected(self, relative, error):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, rootfs = self.make_fixture(root, dashboard_files=True)
            (rootfs / "www/athena-daed" / relative).unlink()
            output = root / "inspection"

            result = self.inspect(openwrt, output)
            report = json.loads((output / "firmware-inspection.json").read_text(encoding="utf-8"))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(error, report["daed_static_ui"]["errors"])

    def test_rejects_daed_browser_port_2023(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, rootfs = self.make_fixture(root, dashboard_files=True)
            script = rootfs / "www/athena-daed/assets/index-abc.js"
            script.write_text("const endpoint='http://192.168.50.1:2023/graphql';", encoding="utf-8")
            output = root / "inspection"

            result = self.inspect(openwrt, output)
            report = json.loads((output / "firmware-inspection.json").read_text(encoding="utf-8"))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("browser-port-2023", report["daed_static_ui"]["errors"])

    def test_rejects_daed_static_location_proxy(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, rootfs = self.make_fixture(root, dashboard_files=True)
            config = rootfs / "etc/nginx/conf.d/athena-daed.locations"
            config.write_text(config.read_text(encoding="utf-8").replace("root /www;", "proxy_pass http://127.0.0.1:2023/;"), encoding="utf-8")
            output = root / "inspection"

            result = self.inspect(openwrt, output)
            report = json.loads((output / "firmware-inspection.json").read_text(encoding="utf-8"))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("daed-ui-whole-site-proxy", report["web_integration"]["forbidden"])

    def test_rejects_daed_graphql_proxy_not_loopback(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, rootfs = self.make_fixture(root, dashboard_files=True)
            config = rootfs / "etc/nginx/conf.d/athena-daed.locations"
            config.write_text(config.read_text(encoding="utf-8").replace("127.0.0.1:2023/graphql", "192.168.50.1:2023/graphql"), encoding="utf-8")
            output = root / "inspection"

            result = self.inspect(openwrt, output)
            report = json.loads((output / "firmware-inspection.json").read_text(encoding="utf-8"))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("daed-graphql-loopback-proxy", report["web_integration"]["missing"])

    def test_reports_daed_static_ui_hashes(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            openwrt, _ = self.make_fixture(root, dashboard_files=True)
            output = root / "inspection"

            result = self.inspect(openwrt, output)
            report = json.loads((output / "firmware-inspection.json").read_text(encoding="utf-8"))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(report["daed_static_ui"]["tree_sha256"]), 64)
            self.assertEqual(report["daed_static_ui"]["graphql_endpoint"], "/athena-daed/graphql")


if __name__ == "__main__":
    unittest.main()
