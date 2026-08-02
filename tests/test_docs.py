from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]


class DocsTests(unittest.TestCase):
    def test_consistency(self):
        files = [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]
        text = "\n".join(path.read_text(encoding="utf-8") for path in files)

        self.assertIn("192.168.50.1", text)
        self.assertIn("192.168.50.1:8080", text)
        self.assertIn("initramfs", text.lower())
        self.assertIn("sysupgrade -n", text)
        self.assertIn("athena-iot setup", text)
        self.assertIn("DAED 默认关闭", text)
        self.assertNotIn("http://192.168.50.1:2023", text)

    def test_no_common_mojibake_in_user_docs(self):
        files = [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]
        text = "\n".join(path.read_text(encoding="utf-8") for path in files)

        for marker in ("榛樿", "鐜颁唬", "鏋舵瀯", "鍥藉唴", "鍏煎"):
            self.assertNotIn(marker, text, marker)


if __name__ == "__main__":
    unittest.main()
