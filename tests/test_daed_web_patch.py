from pathlib import Path
import tempfile
import unittest

from scripts.patch_daed_package import HOOK, patch_makefile
from scripts.patch_daed_web import NEW, OLD, SOURCE, patch_source


class DaedWebSourcePatchTests(unittest.TestCase):
    def make_source(self, root: Path, text: str) -> Path:
        path = root / SOURCE
        path.parent.mkdir(parents=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_exact_endpoint_is_replaced_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.make_source(root, f"before\n{OLD}\nafter\n")
            patch_source(root)
            patched = path.read_text(encoding="utf-8")
            self.assertEqual(patched.count(OLD), 0)
            self.assertEqual(patched.count(NEW), 1)

    def test_second_run_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.make_source(root, f"{OLD}\n")
            patch_source(root)
            first = path.read_bytes()
            patch_source(root)
            self.assertEqual(path.read_bytes(), first)

    def test_missing_known_endpoint_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_source(root, "export const OTHER = 'unknown'\n")
            with self.assertRaises(RuntimeError):
                patch_source(root)

    def test_duplicate_known_endpoint_fails_closed(self):
        for text in (f"{OLD}\n{OLD}\n", f"{NEW}\n{NEW}\n"):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_source(root, text)
                with self.assertRaises(RuntimeError):
                    patch_source(root)

    def test_unexpected_source_path_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                patch_source(Path(directory))


class DaedPackagePatchTests(unittest.TestCase):
    def test_hook_is_inserted_once_inside_build_prepare(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Makefile"
            path.write_text(
                "define Build/Prepare\n"
                "\t$(call Build/Prepare/Default)\n"
                "endef\n",
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


if __name__ == "__main__":
    unittest.main()
