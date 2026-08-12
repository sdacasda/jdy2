from pathlib import Path
import unittest
ROOT=Path(__file__).parents[1]
class WorkflowTests(unittest.TestCase):
 def test_v19_workflow(self):
  t=(ROOT/".github/workflows/build-athena-v19.yml").read_text(encoding="utf-8")
  for x in ("SOURCES.lock.json","build_profile","release_stage","6291456","131072","inspect_firmware.py","Athena-AX6600-v19","Restore executable permissions","BUILD_NOT_AVAILABLE.txt","Generate effective OpenWrt config","Verify effective OpenWrt config","effective.config"):
   self.assertIn(x,t)
  self.assertIn("node tests/js/test_dashboard_chart.js",t)
  self.assertIn("python3 scripts/verify_web_config.py --root .",t)
  self.assertIn("python3 scripts/inspect_firmware.py",t)
  self.assertIn("firmware-inspection.json",t)
  self.assertNotIn("create-release",t.lower())

 def test_vmlinux_btf_host_dependency_is_installed_and_verified(self):
  t=(ROOT/".github/workflows/build-athena-v19.yml").read_text(encoding="utf-8")
  self.assertRegex(t, r"apt-get install[^\n]*\bpahole\b")
  self.assertIn("command -v pahole", t)

 def test_complete_host_bpf_toolchain_is_installed_and_verified(self):
  t=(ROOT/".github/workflows/build-athena-v19.yml").read_text(encoding="utf-8")
  self.assertRegex(t, r"apt-get install[^\n]*\bclang\b[^\n]*\bllvm\b")
  for tool in ("clang","llc","llvm-dis","opt","llvm-strip"):
   self.assertIn(f"command -v {tool}",t)

 def test_artifact_upload_preserves_hidden_files_listed_in_checksums(self):
  t=(ROOT/".github/workflows/build-athena-v19.yml").read_text(encoding="utf-8")
  self.assertRegex(
   t,
   r"actions/upload-artifact@v6[\s\S]*?include-hidden-files:\s*true",
  )

 def test_locked_daed_replaces_feed_before_feed_install_and_is_verified(self):
  t=(ROOT/".github/workflows/build-athena-v19.yml").read_text(encoding="utf-8")
  feed_update=t.index("./scripts/feeds update -a")
  remove_conflict=t.index("bash scripts/remove_feed_conflicts.sh openwrt")
  prepare_locked=t.index("bash scripts/prepare_packages.sh openwrt")
  feed_install=t.index("./scripts/feeds install -a")
  self.assertLess(feed_update,remove_conflict)
  self.assertLess(remove_conflict,prepare_locked)
  self.assertLess(prepare_locked,feed_install)
  self.assertIn("verify_daed_provenance.py",t)
  self.assertIn("daed-provenance/prebuild.txt",t)
  self.assertIn("daed-provenance/postbuild.txt",t)
  self.assertIn('"$OUTPUT/diagnostics/daed-provenance"',t)
  self.assertRegex(
   t,
   r"name: Verify effective OpenWrt config[\s\S]*?run: \|\n\s+set -euo pipefail",
  )
  self.assertRegex(
   t,
   r"name: Verify compiled DAED provenance[\s\S]*?run: \|\n\s+set -euo pipefail",
  )
  self.assertRegex(
   t,
   r"name: Build both images[\s\S]*?run: \|\n\s+set -euo pipefail",
  )

 def test_pinned_daed_source_is_assembled_before_openwrt_download(self):
  t=(ROOT/".github/workflows/build-athena-v19.yml").read_text(encoding="utf-8")
  self.assertRegex(t,r"actions/setup-go@v6[\s\S]*?go-version:\s*[\"']1\.26\.0[\"']")
  self.assertRegex(t,r"actions/setup-node@v5[\s\S]*?node-version:\s*24")
  assemble=t.index("bash scripts/assemble_daed_source.sh openwrt")
  self.assertIn("make -C openwrt package/daed/download V=s",t)
  validate_archive=t.index("make -C openwrt package/daed/download V=s")
  download=t.index("make -C openwrt download -j2")
  self.assertLess(assemble,validate_archive)
  self.assertLess(validate_archive,download)
  self.assertLess(assemble,download)
  self.assertIn("daed-source-provenance",t)

 def test_node_is_installed_before_unittest_discovery(self):
  t=(ROOT/".github/workflows/build-athena-v19.yml").read_text(encoding="utf-8")
  setup_node=t.index("actions/setup-node@v5")
  validate=t.index("name: Validate source project")
  discovery=t.index("python3 -m unittest discover -s tests")
  self.assertLess(setup_node,validate)
  self.assertLess(setup_node,discovery)

 def test_setup_go_does_not_probe_for_a_root_go_module(self):
  t=(ROOT/".github/workflows/build-athena-v19.yml").read_text(encoding="utf-8")
  self.assertRegex(
   t,
   r"actions/setup-go@v6[\s\S]*?go-version:\s*[\"']1\.26\.0[\"'][\s\S]*?cache:\s*false",
  )

 def test_daed_cache_is_saved_immediately_after_source_preflight(self):
  t=(ROOT/".github/workflows/build-athena-v19.yml").read_text(encoding="utf-8")
  restore=t.index("actions/cache/restore@v5")
  assemble=t.index("name: Assemble pinned DAED source")
  save=t.index("actions/cache/save@v5")
  compile_step=t.index("name: Build both images")
  self.assertLess(restore,assemble)
  self.assertLess(assemble,save)
  self.assertLess(save,compile_step)
  self.assertIn("steps.daedcache.outputs.cache-hit != 'true'",t)

 def test_daed_cache_key_includes_static_web_installer(self):
  t=(ROOT/".github/workflows/build-athena-v19.yml").read_text(encoding="utf-8")
  keys = [line for line in t.splitlines() if "key: daed-source-" in line]
  self.assertGreaterEqual(len(keys), 2)
  for key in keys:
   self.assertIn("scripts/install_daed_web.py", key)

 def test_daed_static_ui_is_verified_before_long_firmware_build(self):
  t=(ROOT/".github/workflows/build-athena-v19.yml").read_text(encoding="utf-8")
  assemble=t.index("bash scripts/assemble_daed_source.sh openwrt")
  staged_index=t.index("root/www/athena-daed/index.html")
  package_manifest=t.index("root/usr/share/athena/daed-static-web.json")
  provenance=t.index("daed-source-provenance/static-web.json")
  verify_web=t.index("python3 scripts/verify_web_config.py --root .", assemble)
  compile_step=t.index("name: Build both images")
  for check in (staged_index, package_manifest, provenance, verify_web):
   self.assertLess(assemble, check)
   self.assertLess(check, compile_step)
if __name__=="__main__": unittest.main()
