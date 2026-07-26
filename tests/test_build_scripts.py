from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).parents[1]
class BuildScriptTests(unittest.TestCase):
 def test_locked_sources_and_defaults(self):
  p=(ROOT/"scripts/prepare_packages.sh").read_text(encoding="utf-8")
  s=(ROOT/"scripts/stage_local_packages.sh").read_text(encoding="utf-8")
  i=(ROOT/"scripts/inject_runtime.sh").read_text(encoding="utf-8")
  self.assertIn("SOURCES.lock.json",p); self.assertNotIn("main}",p); self.assertIn("rev-parse HEAD",p)
  self.assertIn("athena-runtime luci-app-athena",s)
  self.assertIn('PROJECT_ROOT/packages/$package',s)
  self.assertIn("192.168.50.1",i); self.assertIn("127.0.0.1:2023",i)
  self.assertNotIn("cat >\"$FILES/usr/bin/athena-setup",i)

 def test_local_packages_are_staged_before_feed_metadata_is_built(self):
  workflow=(ROOT/".github/workflows/build-athena-v19.yml").read_text(encoding="utf-8")
  self.assertIn("bash scripts/stage_local_packages.sh openwrt",workflow)
  stage=workflow.index("bash scripts/stage_local_packages.sh openwrt")
  feed_update=workflow.index("./scripts/feeds update -a")
  self.assertLess(stage,feed_update)

 def test_local_package_staging_is_idempotent_and_not_nested(self):
  with tempfile.TemporaryDirectory() as directory:
   topdir=Path(directory)/"openwrt"
   (topdir/"package").mkdir(parents=True)
   script=str(ROOT/"scripts/stage_local_packages.sh")
   argument=str(topdir)
   if os.name=="nt":
    cygpath=shutil.which("cygpath") or r"D:\Git\usr\bin\cygpath.exe"
    bash=shutil.which("bash") or r"D:\Git\bin\bash.exe"
    script=subprocess.check_output([cygpath,"-u",script],text=True).strip()
    argument=subprocess.check_output([cygpath,"-u",argument],text=True).strip()
    command=[bash,"-lc",f"'{script}' '{argument}'"]
   else:
    command=["bash",script,argument]
   subprocess.run(command,cwd=ROOT,check=True,capture_output=True,text=True)
   subprocess.run(command,cwd=ROOT,check=True,capture_output=True,text=True)
   for package in ("athena-runtime","luci-app-athena"):
    destination=topdir/"package/custom"/package
    self.assertTrue((destination/"Makefile").is_file())
    self.assertFalse((destination/package).exists())
if __name__=="__main__": unittest.main()
