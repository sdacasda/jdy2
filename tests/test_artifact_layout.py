from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).parents[1]


def shell_path(path):
 path=Path(path).resolve()
 try:
  return path.relative_to(ROOT.resolve()).as_posix()
 except ValueError:
  pass
 if os.name != "nt":
  return str(path)
 cygpath=shutil.which("cygpath") or r"D:\Git\usr\bin\cygpath.exe"
 return subprocess.check_output([cygpath,"-u",str(path)],text=True).strip()


def run_collect(topdir,output,inspection):
 script=shell_path(ROOT/"scripts/collect_output.sh")
 arguments=" ".join(
  f"'{shell_path(path)}'" for path in (topdir,output,inspection)
 )
 if os.name == "nt":
  bash=shutil.which("bash") or r"D:\Git\bin\bash.exe"
  command=[
   bash,
   "-lc",
   (
    "export PATH=/usr/bin:/mingw64/bin:$PATH; "
    f"export ATHENA_PYTHON='{shell_path(sys.executable)}'; "
    f"'{script}' {arguments}"
   ),
  ]
 else:
  command=["bash",str(ROOT/"scripts/collect_output.sh"),*map(str,(topdir,output,inspection))]
 environment=os.environ.copy()
 environment["ATHENA_PYTHON"]=sys.executable
 return subprocess.run(
  command,
  cwd=ROOT,
  env=environment,
  capture_output=True,
  text=True,
  encoding="utf-8",
  errors="replace",
 )


class ArtifactTests(unittest.TestCase):
 def test_layout_and_strict_images(self):
  t=(ROOT/"scripts/collect_output.sh").read_text(encoding="utf-8")
  for x in ("firmware,metadata,diagnostics,tools,docs","athena-v19-initramfs-uImage.itb","athena-v19-squashfs-sysupgrade.bin","SHA256SUMS.txt"):
   self.assertIn(x,t)
  self.assertIn('\"${#initramfs[@]}\" -eq 1',t)

 def test_collection_reuses_the_images_that_inspection_validated(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as directory:
   root=Path(directory)
   topdir=root/"openwrt"
   target=topdir/"bin/targets/qualcommax/ipq60xx"
   target.mkdir(parents=True)
   initramfs=target/"validated-initramfs.itb"
   sysupgrade=target/"validated-sysupgrade.bin"
   initramfs.write_bytes(b"initramfs")
   sysupgrade.write_bytes(b"sysupgrade")
   inspection=root/"firmware-inspection.json"
   inspection.write_text(
    json.dumps({
     "initramfs":[shell_path(initramfs)],
     "sysupgrade":[shell_path(sysupgrade)],
     "kernel_bytes":1,
     "kernel_limit":6291456,
     "kernel_margin":6291455,
     "missing_packages":[],
     "forbidden_packages":[],
    }),
    encoding="utf-8",
   )
   output=root/"artifact"

   result=run_collect(topdir,output,inspection)

   self.assertEqual(result.returncode,0,result.stderr)
   self.assertEqual(
    (output/"firmware/athena-v19-initramfs-uImage.itb").read_bytes(),
    b"initramfs",
   )
   self.assertEqual(
    (output/"firmware/athena-v19-squashfs-sysupgrade.bin").read_bytes(),
    b"sysupgrade",
   )

 def test_failed_collection_still_preserves_inspection_evidence(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as directory:
   root=Path(directory)
   topdir=root/"openwrt"
   (topdir/"bin/targets/qualcommax/ipq60xx").mkdir(parents=True)
   inspection=root/"firmware-inspection.json"
   inspection.write_text(
    json.dumps({"initramfs":[],"sysupgrade":[]}),
    encoding="utf-8",
   )
   output=root/"artifact"

   result=run_collect(topdir,output,inspection)

   self.assertNotEqual(result.returncode,0)
   self.assertTrue(
    (output/"diagnostics/firmware-inspection.json").is_file()
   )
   self.assertTrue(
    (output/"diagnostics/ARTIFACT_COLLECTION_ERROR.txt").is_file()
   )
if __name__=="__main__": unittest.main()
