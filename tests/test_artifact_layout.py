from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).parents[1]
REQUIRED_OUTCOMES=(
 "validate",
 "defconfig",
 "configcheck",
 "daedsource",
 "compile",
 "daedbuild",
 "inspect",
)


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


def run_collect(topdir,output,inspection,build_log,outcomes):
 script=shell_path(ROOT/"scripts/collect_output.sh")
 outcomes_path=Path(output).parent/"step-outcomes.txt"
 outcomes_path.write_text(
  "".join(f"{stage}={outcomes[stage]}\n" for stage in REQUIRED_OUTCOMES),
  encoding="utf-8",
 )
 arguments=" ".join(
  f"'{shell_path(path)}'" for path in (topdir,output,inspection,build_log)
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
  command=[
   "bash",
   str(ROOT/"scripts/collect_output.sh"),
   *map(str,(topdir,output,inspection,build_log)),
  ]
 environment=os.environ.copy()
 environment["ATHENA_PYTHON"]=sys.executable
 environment["ATHENA_STEP_OUTCOMES"]=shell_path(outcomes_path)
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
  for x in ('mkdir -p "$OUTPUT"/{metadata,diagnostics,tools,docs}','mkdir -p "$OUTPUT/firmware"',"athena-v19-initramfs-uImage.itb","athena-v19-squashfs-sysupgrade.bin","SHA256SUMS.txt","verify_after_flash.sh","WEB_RECOVERY.md","firmware-inspection.json","kernel-size.txt"):
   self.assertIn(x,t)
  self.assertIn('\"${#initramfs[@]}\" -eq 1',t)

 def test_after_flash_checks_both_web_entries_and_daed_isolation(self):
  t=(ROOT/"scripts/verify_after_flash.sh").read_text(encoding="utf-8")
  for token in (
   "nginx -t",
   "pidof nginx",
   "192.168.50.1:8080",
   "athena-recovery.html",
   "daed.config.enabled",
   "127.0.0.1:2023",
   "/athena-daed/graphql",
   "0.0.0.0:2023",
   "[::]:2023",
  ):
   self.assertIn(token,t)

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
   (target/"sha256sums").write_text(
    "upstream checksum evidence\n",
    encoding="utf-8",
   )
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
   build_log=root/"build.log"
   build_log.write_text("build succeeded\n",encoding="utf-8")

   outcomes={stage:"success" for stage in REQUIRED_OUTCOMES}
   self.assertEqual(len(outcomes),7)
   result=run_collect(topdir,output,inspection,build_log,outcomes)

   self.assertEqual(result.returncode,0,result.stderr)
   self.assertEqual(
    (output/"firmware/athena-v19-initramfs-uImage.itb").read_bytes(),
    b"initramfs",
   )
   self.assertEqual(
    (output/"firmware/athena-v19-squashfs-sysupgrade.bin").read_bytes(),
    b"sysupgrade",
   )
   self.assertEqual(
    (output/"firmware/UPSTREAM_SHA256SUMS").read_text(encoding="utf-8"),
    "upstream checksum evidence\n",
   )
   firmware_names=[
    path.name for path in (output/"firmware").iterdir() if path.is_file()
   ]
   self.assertEqual(
    len(firmware_names),
    len({name.casefold() for name in firmware_names}),
    "Artifact contains filenames that collide on Windows",
   )

 def test_failed_outcome_produces_diagnostics_without_firmware(self):
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
   build_log=root/"build.log"
   build_log.write_text(
    "bash: line 1: pahole: command not found\n"
    "ERROR: package/custom/vmlinux-btf failed to build.\n",
    encoding="utf-8",
   )

   outcomes={stage:"success" for stage in REQUIRED_OUTCOMES}
   outcomes["daedbuild"]="failure"
   result=run_collect(topdir,output,inspection,build_log,outcomes)

   self.assertNotEqual(result.returncode,0)
   self.assertTrue(
    (output/"diagnostics/ARTIFACT_COLLECTION_ERROR.txt").is_file()
   )
   self.assertTrue(
    (output/"diagnostics/BUILD_NOT_AVAILABLE.txt").is_file()
   )
   self.assertFalse((output/"firmware").exists())
   self.assertEqual(
    (output/"diagnostics/step-outcomes.txt").read_text(encoding="utf-8"),
    "".join(f"{stage}={outcomes[stage]}\n" for stage in REQUIRED_OUTCOMES),
   )
   error=(output/"diagnostics/ARTIFACT_COLLECTION_ERROR.txt").read_text(
    encoding="utf-8",
   )
   self.assertEqual(
    error,
    "Required build stage did not succeed: daedbuild\n",
   )
if __name__=="__main__": unittest.main()
