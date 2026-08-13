import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DaedProvenanceTests(unittest.TestCase):
    def test_full_source_static_web_and_compiled_provenance_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packageinfo = root / "packageinfo"
            packageinfo.write_text("Package: daed\nVersion: 2026.07.26-r1\n", encoding="utf-8")
            lock = root / "lock.json"
            lock.write_text(json.dumps({"daede": {"package_version": "2026.07.26-r1"}}), encoding="utf-8")
            makefile = root / "Makefile"
            makefile.write_text("PKG_VERSION:=2026.07.26\nPKG_RELEASE:=1\n", encoding="utf-8")
            build_log = root / "build.log"
            build_log.write_text("Entering directory '/build/package/custom/daed'\n", encoding="utf-8")
            digest = "a" * 64
            assembly = root / "assembly.json"
            assembly.write_text(json.dumps({"pins": {"WEB_PATCH_SHA256": digest, "DATABASE_PATCH_SHA256": "b" * 64}, "sha256": digest, "size": 7, "source_root": "daed-2026.07.26"}), encoding="utf-8")
            archive = root / "archive.json"
            archive.write_text(json.dumps({"source": "daed.tar.gz", "sha256": digest, "size": 7}), encoding="utf-8")
            static_web = root / "static-web.json"
            static_web.write_text(json.dumps({"archive_sha256": digest, "root": "daed-2026.07.26", "tree_sha256": "c" * 64}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "verify_daed_provenance.py"), "--packageinfo", str(packageinfo), "--lock", str(lock), "--makefile", str(makefile), "--build-log", str(build_log), "--assembly-manifest", str(assembly), "--archive-provenance", str(archive), "--static-web-provenance", str(static_web)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
