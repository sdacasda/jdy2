from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]
VIEW = (
    ROOT
    / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/dashboard.js"
)
CSS = (
    ROOT
    / "packages/luci-app-athena/htdocs/luci-static/resources/athena/dashboard.css"
)
CHART = (
    ROOT
    / "packages/luci-app-athena/htdocs/luci-static/resources/athena/chart.js"
)


class DashboardAssetTests(unittest.TestCase):
    def setUp(self):
        self.view = VIEW.read_text(encoding="utf-8")
        self.css = CSS.read_text(encoding="utf-8")
        self.chart = CHART.read_text(encoding="utf-8")

    def test_dashboard_uses_read_only_rpc_and_bounded_polling(self):
        self.assertRegex(
            self.view,
            r"rpc\.declare\(\{\s*object:\s*'athena',\s*method:\s*'dashboard'",
        )
        self.assertIn("'require poll';", self.view)
        self.assertIn("'require athena.chart as chart';", self.view)
        self.assertIn("athena/dashboard.css", self.view)
        self.assertRegex(self.view, r"var\s+POLL_SECONDS\s*=\s*3\s*;")
        self.assertRegex(self.view, r"var\s+MAX_POINTS\s*=\s*200\s*;")
        self.assertIn("poll.add", self.view)
        self.assertIn("consecutiveFailures", self.view)
        self.assertRegex(self.view, r"consecutiveFailures\s*>=\s*2")

    def test_dashboard_covers_required_metrics_and_warnings(self):
        for label in (
            "WAN",
            "CPU",
            "内存",
            "温度",
            "Wi-Fi",
            "IoT",
            "DAED",
            "NSS",
            "ECM",
            "Flow Offload",
            "数据已中断",
            "最近成功更新",
            "DAED 内核组件不兼容",
            "时间未同步",
        ):
            self.assertIn(label, self.view)
        self.assertIn("ebpf_local_tcp_sockops", self.view)
        self.assertIn("role: 'status'", self.view)
        self.assertIn("aria-label", self.view)

    def test_dashboard_has_no_external_assets_or_write_operations(self):
        combined = "\n".join((self.view, self.css, self.chart))
        for forbidden in (
            "http://",
            "https://",
            "fs.exec",
            "uci.set",
            "uci.commit",
            "localStorage",
            "sessionStorage",
            "runtime_apply",
            "rollback",
        ):
            self.assertNotIn(forbidden, combined)

    def test_css_is_argon_compatible_and_responsive(self):
        self.assertIn("repeat(4, minmax(0, 1fr))", self.css)
        self.assertIn("repeat(2, minmax(0, 1fr))", self.css)
        self.assertRegex(
            self.css,
            r"@media\s*\(max-width:\s*1199px\)",
        )
        self.assertRegex(
            self.css,
            r"@media\s*\(max-width:\s*767px\)",
        )
        self.assertIn("grid-template-columns: minmax(0, 1fr)", self.css)
        self.assertIn("--athena-accent", self.css)
        self.assertIn("var(--", self.css)
        self.assertNotRegex(self.css, r"(?m)^\s*width:\s*\d+px")


if __name__ == "__main__":
    unittest.main()
