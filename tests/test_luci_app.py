import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).parents[1]

class LuciAppTests(unittest.TestCase):
    def test_menu_and_acl(self):
        menu = json.loads((ROOT / "packages/luci-app-athena/root/usr/share/luci/menu.d/luci-app-athena.json").read_text(encoding="utf-8"))
        self.assertIn("admin/services/athena", menu)
        self.assertIn("admin/services/athena/daed", menu)
        acl = json.loads((ROOT / "packages/athena-runtime/files/usr/share/rpcd/acl.d/luci-app-athena.json").read_text(encoding="utf-8"))
        self.assertIn("luci-app-athena", acl)
        self.assertIn("read", acl["luci-app-athena"])
        self.assertIn("write", acl["luci-app-athena"])
        read_methods = acl["luci-app-athena"]["read"]["ubus"]["athena"]
        write_methods = acl["luci-app-athena"]["write"]["ubus"]["athena"]
        self.assertIn("dashboard", read_methods)
        self.assertNotIn("dashboard", write_methods)

    def test_dashboard_overrides_only_the_overview_and_athena_status(self):
        override = json.loads(
            (
                ROOT
                / "packages/luci-app-athena/root/usr/share/luci/menu.d/"
                "zz-athena-dashboard.json"
            ).read_text(encoding="utf-8")
        )
        expected = {"type": "view", "path": "athena/dashboard"}
        self.assertEqual(
            override["admin/status/overview"]["action"],
            expected,
        )
        self.assertEqual(
            override["admin/services/athena/status"]["action"],
            expected,
        )
        self.assertEqual(set(override), {
            "admin/status/overview",
            "admin/services/athena/status",
        })
        self.assertFalse(
            (
                ROOT
                / "packages/luci-app-athena/htdocs/luci-static/argon"
            ).exists()
        )

    def test_views_do_not_shell_out(self):
        text = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "packages/luci-app-athena/htdocs").rglob("*.js"))
        self.assertNotIn("fs.exec", text)
        self.assertNotIn("192.168.50.1:2023", text)
        self.assertIn("/athena-daed/", text)

if __name__ == "__main__":
    unittest.main()
