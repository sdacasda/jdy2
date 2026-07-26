from pathlib import Path
import unittest
ROOT=Path(__file__).parents[1]
class WorkflowTests(unittest.TestCase):
 def test_v19_workflow(self):
  t=(ROOT/".github/workflows/build-athena-v19.yml").read_text(encoding="utf-8")
  for x in ("SOURCES.lock.json","build_profile","release_stage","6291456","131072","inspect_firmware.py","Athena-AX6600-v19","Restore executable permissions","BUILD_NOT_AVAILABLE.txt"):
   self.assertIn(x,t)
  self.assertNotIn("create-release",t.lower())
if __name__=="__main__": unittest.main()
