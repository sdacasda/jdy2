from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
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

 def test_feed_daed_conflict_is_removed_without_touching_other_packages(self):
  with tempfile.TemporaryDirectory() as directory:
   topdir=Path(directory)/"openwrt"
   conflicting=(
    topdir/"feeds/packages/net/daed",
    topdir/"package/feeds/packages/daed",
   )
   preserved=(
    topdir/"feeds/packages/net/dae",
    topdir/"feeds/packages/net/curl",
   )
   for path in conflicting+preserved:
    path.mkdir(parents=True)
    (path/"Makefile").write_text(path.name,encoding="utf-8")
   script=str(ROOT/"scripts/remove_feed_conflicts.sh")
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
   for path in conflicting:
    self.assertFalse(path.exists())
   for path in preserved:
    self.assertTrue((path/"Makefile").is_file())

 def test_daed_provenance_rejects_feed_version_and_accepts_locked_version(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   lock={"daede":{"package_version":"2026.07.26-r1"}}
   (root/"SOURCES.lock.json").write_text(json.dumps(lock),encoding="utf-8")
   (root/"Makefile").write_text(
    "PKG_NAME:=daed\nPKG_VERSION:=2026.07.26\nPKG_RELEASE:=1\n",
    encoding="utf-8",
   )
   packageinfo=root/"packageinfo"
   script=ROOT/"scripts/verify_daed_provenance.py"
   packageinfo.write_text(
    "Package: daed\nVersion: 1.27.0-r1\nRepository: packages\n@@\n",
    encoding="utf-8",
   )
   bad=subprocess.run(
    [
     sys.executable,str(script),
     "--packageinfo",str(packageinfo),
     "--lock",str(root/"SOURCES.lock.json"),
     "--makefile",str(root/"Makefile"),
    ],
    text=True,capture_output=True,check=False,
   )
   self.assertNotEqual(bad.returncode,0)
   self.assertIn("expected 2026.07.26-r1",bad.stdout)
   packageinfo.write_text(
    "Package: daed\nVersion: 2026.07.26-r1\nRepository: base\n@@\n",
    encoding="utf-8",
   )
   good=subprocess.run(
    [
     sys.executable,str(script),
     "--packageinfo",str(packageinfo),
     "--lock",str(root/"SOURCES.lock.json"),
     "--makefile",str(root/"Makefile"),
    ],
    text=True,capture_output=True,check=False,
   )
   self.assertEqual(good.returncode,0,good.stdout+good.stderr)

 def test_daed_patch_selects_the_openwrt_bpf_toolchain(self):
  with tempfile.TemporaryDirectory() as directory:
   makefile=Path(directory)/"Makefile"
   makefile.write_text(
    """include $(TOPDIR)/rules.mk
PKG_BUILD_DEPENDS:=golang/host bpf-headers
include $(INCLUDE_DIR)/package.mk
include $(INCLUDE_DIR)/bpf.mk
define Package/daed
  DEPENDS:=+ca-bundle +kmod-sched-bpf \\
    +DAED_USE_VMLINUX_BTF:vmlinux-btf
endef
define Package/daed/config
\tchoice
\t\tprompt "BTF source for CO-RE"
\tconfig DAED_USE_KERNEL_BTF
\t\tbool "Use kernel BTF"
\tconfig DAED_USE_VMLINUX_BTF
\t\tbool "Use vmlinux-btf package"
\tendchoice
endef
""",
    encoding="utf-8",
   )
   result=subprocess.run(
    [sys.executable,str(ROOT/"scripts/patch_daed_btf.py"),str(makefile)],
    text=True,capture_output=True,check=False,
   )
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   patched=makefile.read_text(encoding="utf-8")
   self.assertIn("$(BPF_DEPENDS)",patched)
   self.assertIn("+vmlinux-btf",patched)
   self.assertNotIn("DAED_USE_VMLINUX_BTF",patched)

 def test_config_verifier_rejects_an_unresolved_bpf_toolchain(self):
  required=(
   "CONFIG_TARGET_qualcommax=y",
   "CONFIG_TARGET_qualcommax_ipq60xx=y",
   "CONFIG_TARGET_qualcommax_ipq60xx_DEVICE_jdcloud_re-cs-02=y",
   "CONFIG_TARGET_ROOTFS_INITRAMFS=y",
   "CONFIG_TARGET_ROOTFS_SQUASHFS=y",
   "CONFIG_PACKAGE_daed=y",
   "CONFIG_PACKAGE_luci-app-daede=y",
   "CONFIG_PACKAGE_athena-runtime=y",
   "CONFIG_PACKAGE_luci-app-athena=y",
   "CONFIG_PACKAGE_luci-theme-argon=y",
   "CONFIG_PACKAGE_luci-app-argon-config=y",
   "CONFIG_PACKAGE_uhttpd=y",
   "CONFIG_PACKAGE_ath11k-firmware-qcn9074=y",
   "CONFIG_PACKAGE_nginx-ssl=y",
  )
  with tempfile.TemporaryDirectory() as directory:
   config=Path(directory)/".config"
   config.write_text("\n".join(required)+"\n",encoding="utf-8")
   script=str(ROOT/"scripts/verify_config.sh")
   argument=str(config)
   if os.name=="nt":
    cygpath=shutil.which("cygpath") or r"D:\Git\usr\bin\cygpath.exe"
    bash=shutil.which("bash") or r"D:\Git\bin\bash.exe"
    script=subprocess.check_output([cygpath,"-u",script],text=True).strip()
    argument=subprocess.check_output([cygpath,"-u",argument],text=True).strip()
    command=[bash,"-lc",f"'{script}' '{argument}'"]
   else:
    command=["bash",script,argument]
   missing=subprocess.run(
    command,cwd=ROOT,text=True,capture_output=True,check=False,
   )
   self.assertNotEqual(missing.returncode,0)
   self.assertIn("BPF toolchain",missing.stderr)
   config.write_text(
    "\n".join(required+("CONFIG_USE_LLVM_HOST=y",))+"\n",
    encoding="utf-8",
   )
   resolved=subprocess.run(
    command,cwd=ROOT,text=True,capture_output=True,check=False,
   )
   self.assertEqual(resolved.returncode,0,resolved.stdout+resolved.stderr)
if __name__=="__main__": unittest.main()
