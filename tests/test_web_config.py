import pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).parents[1]
class WebTests(unittest.TestCase):
    def test_validator(self):
        subprocess.run([sys.executable, str(ROOT/"scripts/verify_web_config.py"), "--root", str(ROOT)], check=True)

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
