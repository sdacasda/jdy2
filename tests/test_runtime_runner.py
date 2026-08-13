from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).parents[1]


class RuntimeRunnerTests(unittest.TestCase):
    def _shell(self, name):
        shell = shutil.which(name)
        if shell is None and os.name == "nt":
            candidate = Path(rf"D:\Git\bin\{name}.exe")
            shell = str(candidate) if candidate.exists() else None
        if shell is None:
            self.skipTest(f"{name} is unavailable")
        return shell

    def test_runner_discovers_and_exports_python_when_environment_is_unset(self):
        bash = self._shell("bash")

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
        self.assertEqual(result.stdout.count("PASS: all runtime tests"), 1)

    def test_runner_stops_and_reports_the_first_failing_runtime_test(self):
        bash = self._shell("bash")

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "scripts/tests").mkdir(parents=True)
            (project / "tests/runtime").mkdir(parents=True)
            shutil.copy2(
                ROOT / "scripts/test_runtime_scripts.sh",
                project / "scripts/test_runtime_scripts.sh",
            )
            (project / "tests/runtime/test_daed_recovery.sh").write_text(
                "#!/bin/sh\nexit 1\n", encoding="utf-8"
            )
            (project / "tests/runtime/test_z_after_failure.sh").write_text(
                "#!/bin/sh\necho should-not-run >&2\nexit 0\n", encoding="utf-8"
            )
            (project / "scripts/tests/test_patch_daed_database.py").write_text(
                "raise SystemExit('should not run')\n", encoding="utf-8"
            )

            for test_shell in ("bash", "sh"):
                result = subprocess.run(
                    [
                        bash,
                        "-lc",
                        'PYTHON=true PROJECT_ROOT="$PWD" ATHENA_RUNTIME_TEST_SHELL="'
                        + test_shell
                        + '" bash scripts/test_runtime_scripts.sh',
                    ],
                    cwd=project,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                output = result.stdout + result.stderr
                with self.subTest(test_shell=test_shell):
                    self.assertEqual(result.returncode, 1, msg=output)
                    self.assertIn("FAIL: test_daed_recovery.sh", output)
                    self.assertNotIn("PASS: all runtime tests", output)
                    self.assertNotIn("should-not-run", output)

    def test_workflow_records_validation_and_provenance_logs(self):
        workflow = (ROOT / ".github/workflows/build-athena-v19.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("source-validation/source-validation.log", workflow)
        self.assertIn("daed-provenance/prebuild.txt", workflow)
        self.assertIn("daed-provenance/postbuild.txt", workflow)
        self.assertIn("daed-source-provenance/assembly.log", workflow)
        self.assertIn("ATHENA_STEP_OUTCOMES", workflow)
        self.assertIn("bash scripts/collect_output.sh", workflow)

    def test_production_shell_sources_are_syntax_checked_with_dash(self):
        runner = (ROOT / "scripts/test_runtime_scripts.sh").read_text(encoding="utf-8")
        self.assertIn("SYNTAX", runner)
        self.assertIn('dash -n "$shell_file"', runner)


if __name__ == "__main__":
    unittest.main()
