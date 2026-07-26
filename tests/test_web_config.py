import pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).parents[1]
class WebTests(unittest.TestCase):
    def test_validator(self):
        subprocess.run([sys.executable, str(ROOT/"scripts/verify_web_config.py"), "--root", str(ROOT)], check=True)
if __name__ == "__main__":
    unittest.main()
