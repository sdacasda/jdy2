from pathlib import Path
import unittest
ROOT=Path(__file__).parents[1]
class DocsTests(unittest.TestCase):
 def test_consistency(self):
  files=[ROOT/"README.md",*(ROOT/"docs").glob("*.md")]
  text="\n".join(p.read_text(encoding="utf-8") for p in files)
  self.assertIn("192.168.50.1",text); self.assertIn("192.168.50.1:8080",text)
  self.assertIn("initramfs",text.lower()); self.assertIn("sysupgrade -n",text)
  self.assertIn("athena-iot setup",text); self.assertIn("DAED 默认关闭",text)
  self.assertNotIn("http://192.168.50.1:2023",text)
if __name__=="__main__": unittest.main()
