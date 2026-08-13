from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]


class RuntimeRunnerTests(unittest.TestCase):
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
