import pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).parents[1]
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
if __name__ == "__main__":
    unittest.main()
