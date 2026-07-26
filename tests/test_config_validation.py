from pathlib import Path
import unittest
ROOT=Path(__file__).parents[1]
class ConfigTests(unittest.TestCase):
 def test_v19_config(self):
  t=(ROOT/"config/athena-v19.config").read_text(encoding="utf-8")
  for token in ("CONFIG_TARGET_ROOTFS_INITRAMFS=y","CONFIG_PACKAGE_luci-theme-argon=y","CONFIG_PACKAGE_luci-app-athena=y","CONFIG_PACKAGE_nginx-ssl=y"):
   self.assertIn(token,t)
  self.assertNotIn("CONFIG_PACKAGE_nginx=y",t)
 def test_exclusions(self):
  t=(ROOT/"config/athena-v19.config").read_text(encoding="utf-8")
  self.assertNotIn("CONFIG_PACKAGE_smartdns=y",t)
  self.assertIn("CONFIG_PACKAGE_athena-runtime=y",t)
if __name__=="__main__": unittest.main()
