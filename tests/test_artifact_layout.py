from pathlib import Path
import unittest
ROOT=Path(__file__).parents[1]
class ArtifactTests(unittest.TestCase):
 def test_layout_and_strict_images(self):
  t=(ROOT/"scripts/collect_output.sh").read_text(encoding="utf-8")
  for x in ("firmware,metadata,diagnostics,tools,docs","athena-v19-initramfs-uImage.itb","athena-v19-squashfs-sysupgrade.bin","SHA256SUMS.txt"):
   self.assertIn(x,t)
  self.assertIn('\"${#initramfs[@]}\" -eq 1',t)
if __name__=="__main__": unittest.main()
