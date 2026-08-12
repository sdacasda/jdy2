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
        for method in ("daed_start", "daed_stop", "daed_reset_password"):
            self.assertIn(method, write_methods)
            self.assertNotIn(method, read_methods)

    def test_template_workflow_is_not_exposed_but_reference_data_remains_packaged(self):
        view = (
            ROOT
            / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/templates.js"
        )
        self.assertFalse(view.exists())

        rpcd = (
            ROOT / "packages/athena-runtime/files/usr/libexec/rpcd/athena"
        ).read_text(encoding="utf-8", errors="strict")
        self.assertNotIn('"templates":{}', rpcd)
        self.assertNotIn("\n\t\t\ttemplates)", rpcd)

        templates = ROOT / "packages/athena-runtime/files/usr/share/athena/templates"
        rules = ROOT / "packages/athena-runtime/files/usr/share/athena/rules"
        for path in (
            templates / "global.dae.tpl",
            templates / "dns.dae.tpl",
            templates / "routing.dae.tpl",
            rules / "steam-proxy-domains.txt",
            rules / "steam-direct-domains.txt",
        ):
            self.assertTrue(path.is_file(), path)
        self.assertTrue(
            (
                ROOT
                / "packages/athena-runtime/files/usr/lib/athena/templates.sh"
            ).is_file()
        )

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

    def test_daed_panel_only_hides_the_complete_original_ui_when_process_is_stopped(self):
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
        self.assertIn("_('后端未连接')", panel)
        self.assertNotIn("DAED 后端尚未就绪", panel)
        self.assertNotIn("athena-health --verbose", panel)
        self.assertNotIn("recovery_url", panel)
        frame_index = panel.index("E('iframe'")
        running_index = panel.index("if (!backendRunning)")
        self.assertLess(running_index, frame_index)
        self.assertIn("daed_running", panel[:frame_index])

    def test_daed_password_recovery_rpc_is_gated_and_uses_shared_library(self):
        rpcd = (
            ROOT / "packages/athena-runtime/files/usr/libexec/rpcd/athena"
        ).read_text(encoding="utf-8", errors="strict")
        self.assertIn('"daed_reset_password":{"confirmation":"String"}', rpcd)
        self.assertIn('. "$ATHENA_LIBDIR/daed-recovery.sh"', rpcd)
        self.assertIn('daed_reset_password)', rpcd)
        self.assertIn('json_get_type confirmation_type confirmation', rpcd)
        self.assertIn('json_get_var confirmation confirmation', rpcd)
        self.assertIn('[ "$confirmation_type" = string ]', rpcd)
        self.assertIn("[ \"$confirmation\" = 'RESET DAED PASSWORD' ]", rpcd)
        self.assertIn('athena_daed_reset_password "$confirmation"', rpcd)

    def test_daed_password_recovery_requires_luci_write_acl(self):
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
        self.assertIn("daed_reset_password", write_methods)
        self.assertNotIn("daed_reset_password", read_methods)

    def test_daed_password_recovery_modal_requires_confirmation_and_clears_credentials(self):
        panel = (
            ROOT
            / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js"
        ).read_text(encoding="utf-8", errors="strict")
        self.assertIn("method: 'daed_reset_password'", panel)
        self.assertIn("params: [ 'confirmation' ]", panel)
        self.assertIn("RESET DAED PASSWORD", panel)
        self.assertIn("This action resets the DAED password", panel)
        self.assertIn("input.value !== DAED_RESET_CONFIRMATION", panel)
        self.assertIn("callDaedResetPassword(input.value)", panel)
        self.assertNotIn("callDaedResetPassword({", panel)
        self.assertIn("clearDaedRecoveryCredentials", panel)
        self.assertIn("credentialNode.textContent = ''", panel)
        self.assertIn("credentials.username = ''", panel)
        self.assertIn("credentials.password = ''", panel)
        self.assertIn("result.username = ''", panel)
        self.assertIn("result.password = ''", panel)

    def test_daed_password_recovery_panel_does_not_log_or_store_credentials(self):
        panel = (
            ROOT
            / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js"
        ).read_text(encoding="utf-8", errors="strict")
        self.assertNotIn("console.", panel)
        self.assertNotIn("localStorage", panel)
        self.assertNotIn("sessionStorage", panel)
        self.assertNotIn("uci.", panel)

if __name__ == "__main__":
    unittest.main()
