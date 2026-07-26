import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "packages/athena-runtime/files/usr/share/athena/templates"
RULES = ROOT / "packages/athena-runtime/files/usr/share/athena/rules"


class TemplatePolicyTests(unittest.TestCase):
    def test_static_template_validator(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/verify_templates.py"),
                "--templates",
                str(TEMPLATES),
                "--rules",
                str(RULES),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_routing_has_safe_order_and_no_global_udp_direct(self) -> None:
        text = (TEMPLATES / "routing.dae.tpl").read_text(encoding="utf-8")
        self.assertLess(text.index("geoip:private"), text.index("{{PROXY_GROUP}}"))
        self.assertLess(text.index("{{CHINA_DNS_PRIMARY}}"), text.rindex("fallback: {{PROXY_GROUP}}"))
        self.assertIn("dscp(0x4) -> direct", text)
        self.assertIn("dport(25565) -> direct", text)
        self.assertNotIn("l4proto(udp) -> direct", text)
        self.assertNotIn("ff00::/0", text)

    def test_node_dns_rules_precede_fallback(self) -> None:
        text = (TEMPLATES / "dns.dae.tpl").read_text(encoding="utf-8")
        fallback = text.index("fallback: global_doh")
        for selector in ("node()", "subnode()", "sub()"):
            self.assertLess(text.index(selector), fallback)

    def test_domain_lists_are_normalized_and_distinct(self) -> None:
        steam_proxy = set((RULES / "steam-proxy-domains.txt").read_text().splitlines())
        steam_direct = set((RULES / "steam-direct-domains.txt").read_text().splitlines())
        self.assertTrue(steam_proxy)
        self.assertTrue(steam_direct)
        self.assertFalse(steam_proxy & steam_direct)
        for value in steam_proxy | steam_direct:
            if value and not value.startswith("#"):
                self.assertNotIn("://", value)
                self.assertEqual(value, value.lower())


if __name__ == "__main__":
    unittest.main()
