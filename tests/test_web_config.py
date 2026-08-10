import pathlib, re, shutil, subprocess, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).parents[1]


def validate_web(root):
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/verify_web_config.py"),
            "--root",
            str(root),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def copy_web_fixture(root):
    shutil.copytree(
        ROOT / "packages/luci-app-athena",
        root / "packages/luci-app-athena",
    )


class WebTests(unittest.TestCase):
    def test_validator(self):
        subprocess.run([sys.executable, str(ROOT/"scripts/verify_web_config.py"), "--root", str(ROOT)], check=True)

    def test_daed_proxy_uses_server_context_include(self):
        conf_dir = ROOT / "packages/luci-app-athena/root/etc/nginx/conf.d"
        self.assertFalse((conf_dir / "athena-daed.conf").exists())
        locations = (conf_dir / "athena-daed.locations").read_text(
            encoding="utf-8"
        )
        self.assertIn("location /athena-daed/", locations)
        self.assertIn("location = /athena-daed/graphql", locations)

    def test_daed_static_ui_and_graphql_have_separate_responsibilities(self):
        locations = (
            ROOT
            / "packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.locations"
        ).read_text(encoding="utf-8")
        graphql = re.search(
            r"location\s+=\s+/athena-daed/graphql\s*\{([^}]*)\}",
            locations,
            re.S,
        )
        static_ui = re.search(
            r"location\s+/athena-daed/\s*\{([^}]*)\}",
            locations,
            re.S,
        )
        self.assertIsNotNone(graphql)
        self.assertIsNotNone(static_ui)
        self.assertIn(
            "proxy_pass http://127.0.0.1:2023/graphql;", graphql.group(1)
        )
        self.assertIn("proxy_buffering off;", graphql.group(1))
        self.assertIn("proxy_set_header Upgrade $http_upgrade;", graphql.group(1))
        self.assertNotIn("root /www;", graphql.group(1))
        self.assertNotIn("try_files", graphql.group(1))
        self.assertIn("root /www;", static_ui.group(1))
        self.assertIn(
            "try_files $uri $uri/ /athena-daed/index.html;", static_ui.group(1)
        )
        self.assertNotIn("proxy_pass", static_ui.group(1))

    def test_firstboot_assigns_each_web_port_once(self):
        defaults = (
            ROOT
            / "packages/luci-app-athena/root/etc/uci-defaults/95-athena-web"
        ).read_text(encoding="utf-8")
        for option in ("uhttpd.main.listen_http", "uhttpd.main.listen_https"):
            self.assertIn(f"delete {option}", defaults)
        self.assertEqual(defaults.count("192.168.50.1:8080"), 1)
        self.assertIn("/usr/lib/lua/luci/sgi/uhttpd.lua", defaults)

    def test_validator_requires_dashboard_routes_and_assets(self):
        validator = (ROOT / "scripts/verify_web_config.py").read_text(
            encoding="utf-8"
        )
        for required in (
            "zz-athena-dashboard.json",
            "admin/status/overview",
            "athena/dashboard",
            "dashboard.js",
            "dashboard.css",
            "chart.js",
        ):
            self.assertIn(required, validator)

    def test_rejects_whole_daed_site_proxy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            copy_web_fixture(root)
            config = root / "packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.locations"
            text = config.read_text(encoding="utf-8").replace(
                "root /www;\n    try_files $uri $uri/ /athena-daed/index.html;",
                "proxy_pass http://127.0.0.1:2023/;",
            )
            config.write_text(text, encoding="utf-8")

            result = validate_web(root)

            self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_rejects_graphql_proxy_not_loopback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            copy_web_fixture(root)
            config = root / "packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.locations"
            text = config.read_text(encoding="utf-8").replace(
                "http://127.0.0.1:2023/graphql",
                "http://192.168.50.1:2023/graphql",
            )
            config.write_text(text, encoding="utf-8")

            result = validate_web(root)

            self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_rejects_unconditional_daed_iframe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            copy_web_fixture(root)
            panel = root / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js"
            panel.write_text(
                "'use strict';\n"
                "page.appendChild(E('iframe', { src: '/athena-daed/' }));\n",
                encoding="utf-8",
            )

            result = validate_web(root)

            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("readiness gate", result.stdout)

    def test_rejects_browser_visible_port_2023(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            copy_web_fixture(root)
            panel = root / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js"
            text = panel.read_text(encoding="utf-8").replace(
                "src: '/athena-daed/'",
                "src: 'http://192.168.50.1:2023/'",
            )
            panel.write_text(text, encoding="utf-8")

            result = validate_web(root)

            self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_rejects_daed_enabled_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            copy_web_fixture(root)
            defaults = root / "packages/luci-app-athena/root/etc/uci-defaults/95-athena-web"
            text = defaults.read_text(encoding="utf-8").replace(
                "set daed.config.enabled='0'",
                "set daed.config.enabled='1'",
            )
            defaults.write_text(text, encoding="utf-8")

            result = validate_web(root)

            self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_rejects_missing_recovery_listener(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            copy_web_fixture(root)
            defaults = root / "packages/luci-app-athena/root/etc/uci-defaults/95-athena-web"
            text = defaults.read_text(encoding="utf-8").replace(
                "192.168.50.1:8080",
                "192.168.50.1:8081",
            )
            defaults.write_text(text, encoding="utf-8")

            result = validate_web(root)

            self.assertNotEqual(result.returncode, 0, result.stdout)
if __name__ == "__main__":
    unittest.main()
