from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import patch_daed_web
from scripts.patch_daed_package import HOOK, patch_makefile


ROOT = Path(__file__).parents[1]
FIXTURE_ROOT = ROOT / "scripts" / "tests" / "fixtures" / "daed_web"
FIXTURE_MANIFEST = FIXTURE_ROOT / "manifest.json"
SENTINEL_PASSWORD = "SENTINEL_DAED_PASSWORD_DO_NOT_RENDER"
FORBIDDEN_LEAK_TOKENS = (
    "toast.error(err.message)",
    "toast.error((err as Error).message)",
    "JSON.stringify(error)",
    "JSON.stringify(err)",
    "console.error",
    "console.warn",
    "request.variables",
    "request.body",
    "ClientError",
)


class DaedWebSourcePatchTests(unittest.TestCase):
    def copy_fixture(self, root: Path) -> tuple[Path, Path]:
        manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["assembly_pin"],
            {
                "commit": "b16dbbd3f94558c30d9a875c7e8daf91d4718747",
                "repository": "https://github.com/kenzok8/openwrt-daede.git",
            },
        )
        self.assertEqual(
            manifest["resolved_daed"],
            {
                "commit": "671e65d2fdcd62fe6a3ec18ecda209c5addea898",
                "repository": "https://github.com/daeuniverse/daed.git",
            },
        )
        for relative, expected_digest in manifest["fixture_sha256"].items():
            fixture = FIXTURE_ROOT / relative
            self.assertTrue(fixture.is_file(), f"pinned fixture is missing: {relative}")
            self.assertEqual(sha256(fixture.read_bytes()).hexdigest(), expected_digest)
            if relative in manifest["upstream_sha256"]:
                self.assertEqual(manifest["upstream_sha256"][relative], expected_digest)
        shutil.copytree(FIXTURE_ROOT / "apps", root / "apps")
        return root / patch_daed_web.SOURCE, root / patch_daed_web.SETUP_SOURCE

    def helper_source(self, source: str) -> str:
        start = source.find("function safeErrorMessage(error: unknown): string {")
        self.assertNotEqual(start, -1, "safeErrorMessage is missing")
        depth = 0
        for index in range(start, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    return source[start : index + 1]
        self.fail("safeErrorMessage has unbalanced braces")

    def run_safe_error_helper(self, source: str) -> list[str]:
        node = shutil.which("node")
        if node is None:
            if os.environ.get("GITHUB_ACTIONS") == "true":
                self.fail("GitHub Actions must provide Node.js for safeErrorMessage behavior tests")
            self.skipTest("Node.js is unavailable; CI runs this behavior test with Node.js")
        helper = self.helper_source(source)
        javascript = (
            helper.replace("error: unknown", "error")
            .replace("): string", ")")
            .replace(" as { response?: unknown }", "")
            .replace(" as { errors?: unknown }", "")
            .replace(" as { message?: unknown }", "")
            .replace("const messages: string[]", "const messages")
        )
        representative_error = json.loads(
            (FIXTURE_ROOT / "graphql-request-error.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            representative_error["request"]["variables"]["password"], SENTINEL_PASSWORD
        )
        cases = [
            representative_error,
            None,
            False,
            0,
            "failure",
            [],
            {},
            {"response": None},
            {"response": {"errors": None}},
            {"response": {"errors": {}}},
            {"response": {"errors": [None, 1, "bad", {}, {"message": 1}]}},
        ]
        script = (
            f"{javascript}\n"
            "const cases = JSON.parse(process.argv[1]);\n"
            "const results = cases.map((value) => safeErrorMessage(value));\n"
            "const throwingResponse = {};\n"
            "Object.defineProperty(throwingResponse, 'response', { get() { throw new Error('response getter') } });\n"
            "const throwingErrors = { response: {} };\n"
            "Object.defineProperty(throwingErrors.response, 'errors', { get() { throw new Error('errors getter') } });\n"
            "const throwingEntry = {};\n"
            "Object.defineProperty(throwingEntry, 'message', { get() { throw new Error('message getter') } });\n"
            "const revoked = Proxy.revocable({}, {}); revoked.revoke();\n"
            "results.push(\n"
            "  safeErrorMessage(undefined), safeErrorMessage(() => {}), safeErrorMessage(Symbol('x')), safeErrorMessage(1n),\n"
            "  safeErrorMessage(throwingResponse), safeErrorMessage(throwingErrors),\n"
            "  safeErrorMessage({ response: { errors: [throwingEntry] } }), safeErrorMessage(revoked.proxy),\n"
            ");\n"
            "process.stdout.write(JSON.stringify(results));\n"
        )
        result = subprocess.run(
            [node, "-e", script, json.dumps(cases)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_pinned_source_patch_redacts_errors_and_preserves_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            endpoint_path, setup_path = self.copy_fixture(Path(directory))
            patch_daed_web.patch_source(Path(directory))

            endpoint = endpoint_path.read_text(encoding="utf-8")
            setup = setup_path.read_text(encoding="utf-8")
            self.assertNotIn(patch_daed_web.OLD, endpoint)
            self.assertEqual(endpoint.count(patch_daed_web.NEW), 1)
            self.assertNotIn("toast.error((err as Error).message)", setup)
            self.assertNotIn("toast.error(err.message)", setup)
            self.assertNotIn("JSON.stringify(error)", setup)
            self.assertEqual(setup.count("toast.error(safeErrorMessage(err))"), 3)

    def test_safe_error_message_extracts_only_graphql_messages_and_falls_back_for_all_malformed_values(self):
        with tempfile.TemporaryDirectory() as directory:
            _, setup_path = self.copy_fixture(Path(directory))
            patch_daed_web.patch_source(Path(directory))
            results = self.run_safe_error_helper(setup_path.read_text(encoding="utf-8"))

            self.assertEqual(results[0], "Invalid username or password")
            self.assertNotIn(SENTINEL_PASSWORD, json.dumps(results))
            self.assertEqual(results[1:], ["DAED request failed"] * (len(results) - 1))

    def test_second_run_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            endpoint_path, setup_path = self.copy_fixture(root)
            patch_daed_web.patch_source(root)
            first = (endpoint_path.read_bytes(), setup_path.read_bytes())
            patch_daed_web.patch_source(root)
            self.assertEqual((endpoint_path.read_bytes(), setup_path.read_bytes()), first)

    def test_extra_leak_or_catch_is_rejected_without_writing_either_file(self):
        mutations = {
            "direct_message": "\n      toast.error(err.message)",
            "serialized_error": "\n      toast.error(JSON.stringify(error))",
            "fourth_catch": "\n  try {} catch (error) { toast.error(safeErrorMessage(error)) }",
        }
        for name, added in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                endpoint_path, setup_path = self.copy_fixture(root)
                setup_path.write_text(
                    setup_path.read_text(encoding="utf-8") + added + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
                original = (endpoint_path.read_bytes(), setup_path.read_bytes())
                with self.assertRaises(RuntimeError):
                    patch_daed_web.patch_source(root)
                self.assertEqual((endpoint_path.read_bytes(), setup_path.read_bytes()), original)

    def test_pinned_or_patched_source_leaks_are_rejected_without_writing_either_file(self):
        for state in ("clean", "patched"):
            for token in FORBIDDEN_LEAK_TOKENS:
                with self.subTest(state=state, token=token), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    endpoint_path, setup_path = self.copy_fixture(root)
                    if state == "patched":
                        patch_daed_web.patch_source(root)
                    setup_path.write_text(
                        setup_path.read_text(encoding="utf-8") + f"\n// {token}\n",
                        encoding="utf-8",
                        newline="\n",
                    )
                    original = (endpoint_path.read_bytes(), setup_path.read_bytes())
                    digest_name = (
                        "CLEAN_SETUP_SHA256" if state == "clean" else "PATCHED_SETUP_SHA256"
                    )
                    with patch.object(
                        patch_daed_web,
                        digest_name,
                        sha256(setup_path.read_bytes()).hexdigest(),
                    ):
                        with self.assertRaises(RuntimeError):
                            patch_daed_web.patch_source(root)
                    self.assertEqual((endpoint_path.read_bytes(), setup_path.read_bytes()), original)

    def test_tampered_already_patched_source_is_rejected_without_writing_either_file(self):
        mutations = {
            "warning_message": "\n      toast.warning((err as Error).message)",
            "serialized_error": "\n      console.error(JSON.stringify(error))",
            "fourth_catch": "\n  try {} catch (error) { toast.warning((error as Error).message) }",
        }
        for name, added in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                endpoint_path, setup_path = self.copy_fixture(root)
                patch_daed_web.patch_source(root)
                setup_path.write_text(
                    setup_path.read_text(encoding="utf-8") + added + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
                original = (endpoint_path.read_bytes(), setup_path.read_bytes())
                with self.assertRaises(RuntimeError):
                    patch_daed_web.patch_source(root)
                self.assertEqual((endpoint_path.read_bytes(), setup_path.read_bytes()), original)

    def test_write_failure_rolls_back_both_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            endpoint_path, setup_path = self.copy_fixture(root)
            original = (endpoint_path.read_bytes(), setup_path.read_bytes())
            original_replace = patch_daed_web.os.replace
            failed = False

            def fail_setup_replace(source: str, destination: str) -> None:
                nonlocal failed
                if Path(destination) == setup_path and not failed:
                    failed = True
                    raise OSError("simulated setup replacement failure")
                original_replace(source, destination)

            with patch.object(patch_daed_web.os, "replace", side_effect=fail_setup_replace):
                with self.assertRaises(OSError):
                    patch_daed_web.patch_source(root)
            self.assertTrue(failed)
            self.assertEqual((endpoint_path.read_bytes(), setup_path.read_bytes()), original)


class DaedPackagePatchTests(unittest.TestCase):
    def test_hook_is_inserted_once_inside_build_prepare(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Makefile"
            path.write_text(
                "define Build/Prepare\n\t$(call Build/Prepare/Default)\nendef\n",
                encoding="utf-8",
            )
            patch_makefile(path)
            patched = path.read_text(encoding="utf-8")
            block = patched.split("define Build/Prepare\n", 1)[1].split("\nendef", 1)[0]
            self.assertEqual(patched.count(HOOK), 1)
            self.assertIn(HOOK, block)
            patch_makefile(path)
            self.assertEqual(path.read_text(encoding="utf-8").count(HOOK), 1)

    def test_unexpected_makefile_layout_fails_closed(self):
        fixtures = (
            "define Package/daed\nendef\n",
            "define Build/Prepare\nendef\ndefine Build/Prepare\nendef\n",
            f"define Build/Prepare\n{HOOK}\n{HOOK}\nendef\n",
        )
        for fixture in fixtures:
            with self.subTest(fixture=fixture), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "Makefile"
                path.write_text(fixture, encoding="utf-8")
                with self.assertRaises(RuntimeError):
                    patch_makefile(path)
