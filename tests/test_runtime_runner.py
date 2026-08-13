from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).parents[1]


class RuntimeRunnerTests(unittest.TestCase):
    def test_runner_discovers_and_exports_python_when_environment_is_unset(self):
        bash = shutil.which("bash")
        if bash is None and os.name == "nt":
            candidate = Path(r"D:\Git\bin\bash.exe")
            bash = str(candidate) if candidate.exists() else None
        if bash is None:
            self.skipTest("bash is unavailable")

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "scripts/tests").mkdir(parents=True)
            (project / "tests/runtime").mkdir(parents=True)
            (project / "bin").mkdir()
            shutil.copy2(
                ROOT / "scripts/test_runtime_scripts.sh",
                project / "scripts/test_runtime_scripts.sh",
            )
            (project / "scripts/tests/test_patch_daed_database.py").write_text(
                "# handled by the test python3 shim\n", encoding="utf-8"
            )
            (project / "tests/runtime/test_python_env.sh").write_text(
                '#!/bin/sh\n[ -n "${PYTHON:-}" ] || { echo "PYTHON unset" >&2; exit 1; }\n'
                'command -v "$PYTHON" >/dev/null 2>&1\n',
                encoding="utf-8",
            )
            (project / "bin/python3").write_text(
                "#!/bin/sh\nexit 0\n", encoding="utf-8"
            )

            env = os.environ.copy()
            env.pop("PYTHON", None)
            result = subprocess.run(
                [
                    bash,
                    "-lc",
                    'PATH="$PWD/bin:$PATH" ATHENA_RUNTIME_TEST_SHELL=bash '
                    'PROJECT_ROOT="$PWD" bash scripts/test_runtime_scripts.sh',
                ],
                cwd=project,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_host_tests_use_bash_and_report_failed_test_names(self):
        runner = (ROOT / "scripts/test_runtime_scripts.sh").read_text(encoding="utf-8")
        self.assertIn('test_shell="${ATHENA_RUNTIME_TEST_SHELL:-bash}"', runner)
        self.assertIn('"$test_shell" "$test_file"', runner)
        self.assertIn("Failed runtime tests:", runner)

    def test_workflow_preserves_source_validation_log(self):
        workflow = (ROOT / ".github/workflows/build-athena-v19.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("source-validation/source-validation.log", workflow)
        self.assertIn(
            'cp -a source-validation "$OUTPUT/diagnostics/source-validation"',
            workflow,
        )

    def test_production_shell_sources_are_syntax_checked_with_dash(self):
        runner = (ROOT / "scripts/test_runtime_scripts.sh").read_text(encoding="utf-8")
        self.assertIn("SYNTAX", runner)
        self.assertIn('dash -n "$shell_file"', runner)


if __name__ == "__main__":
    unittest.main()
