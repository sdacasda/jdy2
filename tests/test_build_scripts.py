from pathlib import Path
import unittest
ROOT=Path(__file__).parents[1]
class BuildScriptTests(unittest.TestCase):
 def test_locked_sources_and_defaults(self):
  p=(ROOT/"scripts/prepare_packages.sh").read_text(encoding="utf-8")
  i=(ROOT/"scripts/inject_runtime.sh").read_text(encoding="utf-8")
  self.assertIn("SOURCES.lock.json",p); self.assertNotIn("main}",p); self.assertIn("rev-parse HEAD",p)
  self.assertIn("packages/athena-runtime",p); self.assertIn("packages/luci-app-athena",p)
  self.assertIn("192.168.50.1",i); self.assertIn("127.0.0.1:2023",i)
  self.assertNotIn("cat >\"$FILES/usr/bin/athena-setup",i)
if __name__=="__main__": unittest.main()
