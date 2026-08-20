import importlib.util
import os
from pathlib import Path
from unittest import mock
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tests" / "test_collect_output.py"


def load_collect_output_module():
    spec = importlib.util.spec_from_file_location(
        "collect_output_portability_target", MODULE_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CollectOutputPortabilityTests(unittest.TestCase):
    def test_uses_bash_resolved_from_current_runner_path(self):
        with mock.patch("shutil.which", return_value="/usr/bin/bash"):
            module = load_collect_output_module()

        self.assertEqual(module.BASH, "/usr/bin/bash")

    def test_posix_runner_path_is_preserved(self):
        module = load_collect_output_module()
        original = "/opt/toolchain/bin:/usr/local/bin:/usr/bin:/bin"

        with mock.patch.dict(os.environ, {"PATH": original}):
            env = module.collect_subprocess_env(platform_name="posix")

        self.assertEqual(env["PATH"], original)


if __name__ == "__main__":
    unittest.main()
