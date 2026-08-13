import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).parents[1]

class LuciAppTests(unittest.TestCase):
    def test_menu_and_acl(self):
        menu = json.loads((ROOT / "packages/luci-app-athena/root/usr/share/luci/menu.d/luci-app-athena.json").read_text(encoding="utf-8"))
        self.assertIn("admin/services/athena", menu)
        self.assertIn("admin/services/athena/daed", menu)
        self.assertNotIn("admin/services/athena/templates", menu)
        acl = json.loads((ROOT / "packages/athena-runtime/files/usr/share/rpcd/acl.d/luci-app-athena.json").read_text(encoding="utf-8"))
        self.assertIn("luci-app-athena", acl)
        self.assertIn("read", acl["luci-app-athena"])
        self.assertIn("write", acl["luci-app-athena"])
        read_methods = acl["luci-app-athena"]["read"]["ubus"]["athena"]
        write_methods = acl["luci-app-athena"]["write"]["ubus"]["athena"]
        self.assertIn("dashboard", read_methods)
        self.assertNotIn("dashboard", write_methods)
        self.assertNotIn("templates", read_methods)
        self.assertNotIn("templates", write_methods)
        for method in ("daed_start", "daed_stop"):
            self.assertIn(method, write_methods)
            self.assertNotIn(method, read_methods)
        self.assertNotIn("daed_reset_password", write_methods)

    def test_template_subsystem_is_completely_absent(self):
        retired_paths = (
            "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/templates.js",
            "packages/athena-runtime/files/usr/lib/athena/templates.sh",
            "packages/athena-runtime/files/usr/share/athena/templates/global.dae.tpl",
            "packages/athena-runtime/files/usr/share/athena/templates/dns.dae.tpl",
            "packages/athena-runtime/files/usr/share/athena/templates/routing.dae.tpl",
            "packages/athena-runtime/files/usr/share/athena/rules/steam-direct-domains.txt",
            "packages/athena-runtime/files/usr/share/athena/rules/steam-proxy-domains.txt",
            "packages/athena-runtime/files/usr/share/athena/rules/xbox-direct-domains.txt",
            "packages/athena-runtime/files/usr/share/athena/rules/xbox-proxy-domains.txt",
            "scripts/verify_templates.py",
            "tests/test_templates.py",
        )
        for relative in retired_paths:
            self.assertFalse((ROOT / relative).exists(), relative)

        rpcd = (
            ROOT / "packages/athena-runtime/files/usr/libexec/rpcd/athena"
        ).read_text(encoding="utf-8", errors="strict")
        self.assertNotIn("templates", rpcd)
        self.assertNotIn("athena_render_templates", rpcd)

        acl = (ROOT / "packages/athena-runtime/files/usr/share/rpcd/acl.d/luci-app-athena.json").read_text(encoding="utf-8", errors="strict")
        self.assertNotIn("templates", acl)
        self.assertNotIn("athena_render_templates", acl)

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

    def test_daed_panel_is_same_origin_and_menu_json_is_utf8(self):
        for name in ("luci-app-athena.json", "zz-athena-dashboard.json"):
            json.loads(
                (
                    ROOT
                    / "packages/luci-app-athena/root/usr/share/luci/menu.d"
                    / name
                ).read_text(encoding="utf-8", errors="strict")
            )
        panel = (
            ROOT
            / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js"
        ).read_text(encoding="utf-8", errors="strict")
        self.assertIn("/athena-daed/", panel)
        self.assertNotIn(":2023", panel)
        for field in ("daed_enabled", "daed_running", "daed_api_reachable"):
            self.assertIn(field, panel)
        for method in ("daed_start", "daed_stop"):
            self.assertIn(method, panel)
        self.assertNotIn("http://", panel)
        self.assertNotIn("https://", panel)

    def test_daed_panel_stopped_branch_returns_only_the_disconnected_message(self):
        panel = (
            ROOT
            / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js"
        ).read_text(encoding="utf-8", errors="strict")
        self.assertIn("src: '/athena-daed/'", panel)
        self.assertIn("allow: 'clipboard-read; clipboard-write'", panel)
        self.assertIn("allow-same-origin", panel)
        self.assertIn("allow-scripts", panel)
        self.assertIn("var backendRunning = !!s.daed_running", panel)
        self.assertIn("if (!backendRunning)", panel)
        self.assertNotIn("DAED 后端尚未就绪", panel)
        self.assertNotIn("athena-health --verbose", panel)
        self.assertNotIn("recovery_url", panel)
        stopped_index = panel.index("if (!backendRunning)")
        running_index = panel.index("var apiReachable")
        stopped_branch = panel[stopped_index:running_index]
        self.assertIn("return E('div'", stopped_branch)
        disconnected_message = "\u540e\u7aef\u672a\u8fde\u63a5"
        self.assertEqual(stopped_branch.count(disconnected_message), 1)
        for forbidden in (
            "statusChip(",
            "athena-daed-summary",
            "athena-daed-actions",
            "handleStart",
            "handleRefresh",
            "E('iframe'",
        ):
            self.assertNotIn(forbidden, stopped_branch)
        for running_content in (
            "E('h2'",
            "athena-daed-summary",
            "athena-daed-actions",
            "E('iframe'",
        ):
            self.assertLess(stopped_index, panel.index(running_content, stopped_index))

    def test_daed_panel_keeps_the_same_origin_ui_when_api_is_unreachable(self):
        panel = (
            ROOT
            / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js"
        ).read_text(encoding="utf-8", errors="strict")
        self.assertIn("var apiReachable = !!s.daed_api_reachable", panel)
        self.assertIn("if (backendRunning && !apiReachable)", panel)
        self.assertIn("athena-daed-api-warning", panel)
        self.assertIn("handleRecoveryCommand", panel)
        self.assertLess(
            panel.index("if (backendRunning && !apiReachable)"),
            panel.index("E('iframe'"),
        )

    def test_daed_password_recovery_is_not_exposed_over_rpc(self):
        rpcd = (
            ROOT / "packages/athena-runtime/files/usr/libexec/rpcd/athena"
        ).read_text(encoding="utf-8", errors="strict")
        self.assertNotIn("daed_reset_password", rpcd)
        self.assertNotIn("daed-recovery.sh", rpcd)

    def test_daed_password_recovery_is_not_in_luci_acl(self):
        acl_paths = list(
            (ROOT / "packages").rglob(
                "usr/share/rpcd/acl.d/luci-app-athena.json"
            )
        )
        self.assertEqual(
            acl_paths,
            [
                ROOT
                / "packages/athena-runtime/files/usr/share/rpcd/acl.d/"
                "luci-app-athena.json"
            ],
        )
        acl = json.loads(
            (
                ROOT
                / "packages/athena-runtime/files/usr/share/rpcd/acl.d/luci-app-athena.json"
            ).read_text(encoding="utf-8", errors="strict")
        )
        read_methods = acl["luci-app-athena"]["read"]["ubus"]["athena"]
        write_methods = acl["luci-app-athena"]["write"]["ubus"]["athena"]
        self.assertNotIn("daed_reset_password", write_methods)
        self.assertNotIn("daed_reset_password", read_methods)

    def test_daed_password_recovery_panel_only_offers_the_interactive_cli(self):
        panel = (
            ROOT
            / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js"
        ).read_text(encoding="utf-8", errors="strict")
        self.assertIn("athena-daed-reset-password", panel)
        self.assertNotIn("daed_reset_password", panel)
        self.assertNotIn("Generated password", panel)
        self.assertNotIn("credentials.password", panel)
        self.assertNotIn("result.password", panel)

    def test_daed_password_recovery_panel_does_not_log_or_store_credentials(self):
        panel = (
            ROOT
            / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js"
        ).read_text(encoding="utf-8", errors="strict")
        self.assertNotIn("console.", panel)
        self.assertNotIn("localStorage", panel)
        self.assertNotIn("sessionStorage", panel)
        self.assertNotIn("uci.", panel)
        self.assertNotIn("daed_reset_password", panel)

if __name__ == "__main__":
    unittest.main()
