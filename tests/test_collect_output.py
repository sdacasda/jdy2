import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASH = Path("D:/Git/bin/bash.exe")


def msys(path: Path) -> str:
    value = str(path.resolve()).replace("\\", "/")
    return f"/{value[0].lower()}{value[2:]}"


class CollectOutputTests(unittest.TestCase):
    def _run(self, outcomes: str, *, images: bool) -> tuple[subprocess.CompletedProcess[str], Path, tempfile.TemporaryDirectory[str]]:
        temporary = tempfile.TemporaryDirectory(dir=ROOT)
        root = Path(temporary.name)
        openwrt = root / "openwrt"
        (openwrt / "scripts").mkdir(parents=True)
        (openwrt / "scripts" / "diffconfig.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (openwrt / ".config").write_text("CONFIG_TEST=y\n", encoding="utf-8")
        if images:
            target = openwrt / "bin/targets/qualcommax/ipq60xx"
            target.mkdir(parents=True)
            (target / "openwrt-jdcloud_re-cs-02-initramfs-uImage.itb").write_bytes(b"initramfs")
            (target / "openwrt-jdcloud_re-cs-02-squashfs-sysupgrade.bin").write_bytes(b"sysupgrade")
        output = root / "artifact"
        output.mkdir()
        (output / "firmware").mkdir()
        (output / "firmware" / "stale.bin").write_bytes(b"stale")
        outcome_file = root / "step-outcomes.txt"
        outcome_file.write_text(outcomes, encoding="utf-8")
        relative_root = root.relative_to(ROOT)
        result = subprocess.run(
            [str(BASH), "scripts/collect_output.sh", (relative_root / "openwrt").as_posix(), (relative_root / "artifact").as_posix()],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            cwd=ROOT,
            env={
                **os.environ,
                "PATH": "D:\\Git\\usr\\bin;" + os.environ.get("PATH", ""),
                "ATHENA_STEP_OUTCOMES": (relative_root / "step-outcomes.txt").as_posix(),
            },
        )
        return result, output, temporary

    def test_missing_images_create_diagnostics_without_firmware_directory(self):
        outcomes = "\n".join(f"{stage}=success" for stage in ("validate", "defconfig", "configcheck", "daedsource", "compile", "daedbuild", "inspect")) + "\n"
        result, output, temporary = self._run(outcomes, images=False)
        with temporary:
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((output / "diagnostics" / "BUILD_NOT_AVAILABLE.txt").is_file(), result.stdout + result.stderr)
            self.assertFalse((output / "firmware").exists())

    def test_existing_images_are_diagnostics_only_when_a_required_stage_failed(self):
        outcomes = "validate=success\ndefconfig=success\nconfigcheck=success\ndaedsource=success\ncompile=success\ndaedbuild=failure\ninspect=success\n"
        result, output, temporary = self._run(outcomes, images=True)
        with temporary:
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((output / "diagnostics" / "BUILD_NOT_AVAILABLE.txt").is_file(), result.stdout + result.stderr)
            self.assertFalse((output / "firmware").exists())

    def test_missing_or_unknown_required_outcome_fails_closed(self):
        for outcomes in (
            "validate=success\n",
            "validate=success\ndefconfig=unknown\nconfigcheck=success\ndaedsource=success\ncompile=success\ndaedbuild=success\ninspect=success\n",
        ):
            with self.subTest(outcomes=outcomes):
                result, output, temporary = self._run(outcomes, images=True)
                with temporary:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse((output / "firmware").exists())


if __name__ == "__main__":
    unittest.main()
