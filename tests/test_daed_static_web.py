import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).parents[1]
INSTALLER = ROOT / "scripts/install_daed_web.py"
SOURCE_ROOT = "daed-2026.07.26"
FORBIDDEN_WEB_LEAK_TOKENS = (
    b"SENTINEL_DAED_PASSWORD_DO_NOT_RENDER",
    b"toast.error(err.message)",
    b"toast.error((err as Error).message)",
    b"JSON.stringify(error)",
    b"JSON.stringify(err)",
    b"console.error",
    b"console.warn",
    b"request.variables",
    b"request.body",
    b"ClientError",
)


class DaedStaticWebTests(unittest.TestCase):
    def _files(self):
        return {
            "index.html": (
                b'<link rel="icon" href="./logo.webp">'
                b'<script type="module" src="./assets/index-abc.js"></script>'
                b'<link rel="stylesheet" href="./assets/index-def.css">'
            ),
            "logo.webp": b"RIFF-test-logo",
            "assets/index-abc.js": b"const endpoint='/athena-daed/graphql';",
            "assets/index-def.css": b"body{color:#fff}",
        }

    def _write_archive(
        self,
        archive: Path,
        *,
        files=None,
        extra_members=(),
    ):
        files = self._files() if files is None else files
        with tarfile.open(archive, "w:gz") as bundle:
            for relative, payload in files.items():
                name = f"{SOURCE_ROOT}/apps/web/dist/{relative}"
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                info.mtime = 0
                bundle.addfile(info, io.BytesIO(payload))
            for info, payload in extra_members:
                bundle.addfile(info, io.BytesIO(payload) if payload is not None else None)

    def _run(self, archive: Path, destination: Path, provenance: Path):
        return subprocess.run(
            [
                sys.executable,
                str(INSTALLER),
                "--archive",
                str(archive),
                "--destination",
                str(destination),
                "--provenance",
                str(provenance),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def _assert_rejected_without_replacing_destination(
        self,
        archive: Path,
        destination: Path,
        provenance: Path,
        expected_error: str,
    ):
        destination.mkdir(parents=True)
        sentinel = destination / "sentinel.txt"
        sentinel.write_text("keep", encoding="utf-8")
        result = self._run(archive, destination, provenance)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(expected_error, result.stderr)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
        self.assertFalse(provenance.exists())

    def test_installs_complete_static_ui_and_writes_deterministic_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "daed-source.tar.gz"
            destination = root / "www/athena-daed"
            provenance = root / "daed-static-web.json"
            self._write_archive(archive)

            first = self._run(archive, destination, provenance)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            first_record = json.loads(provenance.read_text(encoding="utf-8"))
            self.assertEqual(first_record["schema"], 1)
            self.assertEqual(first_record["archive"], archive.name)
            self.assertEqual(first_record["root"], SOURCE_ROOT)
            self.assertEqual(first_record["file_count"], 4)
            self.assertEqual(len(first_record["tree_sha256"]), 64)
            self.assertEqual(
                [entry["path"] for entry in first_record["files"]],
                sorted(entry["path"] for entry in first_record["files"]),
            )
            for entry in first_record["files"]:
                installed = destination / entry["path"]
                self.assertTrue(installed.is_file(), entry["path"])
                self.assertEqual(installed.stat().st_size, entry["size"])
                self.assertEqual(len(entry["sha256"]), 64)

            second = self._run(archive, destination, provenance)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            second_record = json.loads(provenance.read_text(encoding="utf-8"))
            self.assertEqual(first_record, second_record)

    def test_reinstall_replaces_stale_destination_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "daed-source.tar.gz"
            destination = root / "www/athena-daed"
            provenance = root / "daed-static-web.json"
            self._write_archive(archive)
            destination.mkdir(parents=True)
            (destination / "stale.js").write_text("stale", encoding="utf-8")

            result = self._run(archive, destination, provenance)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((destination / "stale.js").exists())
            self.assertTrue((destination / "index.html").is_file())

    def test_rejects_missing_index_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = self._files()
            files["index.html"] = files["index.html"].replace(
                b"./assets/index-abc.js", b"./assets/missing.js"
            )
            archive = root / "source.tar.gz"
            self._write_archive(archive, files=files)
            self._assert_rejected_without_replacing_destination(
                archive,
                root / "destination",
                root / "provenance.json",
                "referenced asset is missing",
            )

    def test_rejects_missing_javascript(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = self._files()
            files["index.html"] = files["index.html"].replace(
                b'<script type="module" src="./assets/index-abc.js"></script>', b""
            )
            archive = root / "source.tar.gz"
            self._write_archive(archive, files=files)
            self._assert_rejected_without_replacing_destination(
                archive,
                root / "destination",
                root / "provenance.json",
                "index.html does not reference JavaScript",
            )

    def test_rejects_missing_stylesheet(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = self._files()
            files["index.html"] = files["index.html"].replace(
                b'<link rel="stylesheet" href="./assets/index-def.css">', b""
            )
            archive = root / "source.tar.gz"
            self._write_archive(archive, files=files)
            self._assert_rejected_without_replacing_destination(
                archive,
                root / "destination",
                root / "provenance.json",
                "index.html does not reference a stylesheet",
            )

    def test_rejects_missing_logo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = self._files()
            files.pop("logo.webp")
            archive = root / "source.tar.gz"
            self._write_archive(archive, files=files)
            self._assert_rejected_without_replacing_destination(
                archive,
                root / "destination",
                root / "provenance.json",
                "referenced asset is missing",
            )

    def test_rejects_browser_port_2023_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = self._files()
            files["assets/index-abc.js"] = (
                b"const endpoint='http://127.0.0.1:2023/graphql';"
            )
            archive = root / "source.tar.gz"
            self._write_archive(archive, files=files)
            self._assert_rejected_without_replacing_destination(
                archive,
                root / "destination",
                root / "provenance.json",
                "browser-visible DAED port",
            )

    def test_rejects_non_same_origin_graphql_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = self._files()
            files["assets/index-abc.js"] = b"const endpoint='/graphql';"
            archive = root / "source.tar.gz"
            self._write_archive(archive, files=files)
            self._assert_rejected_without_replacing_destination(
                archive,
                root / "destination",
                root / "provenance.json",
                "same-origin GraphQL endpoint",
            )

    def test_rejects_credentials_and_error_leaks_in_browser_assets(self):
        for token in FORBIDDEN_WEB_LEAK_TOKENS:
            with self.subTest(token=token), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                files = self._files()
                files["assets/index-abc.js"] += b"\n// " + token
                archive = root / "source.tar.gz"
                self._write_archive(archive, files=files)
                self._assert_rejected_without_replacing_destination(
                    archive,
                    root / "destination",
                    root / "provenance.json",
                    "unsafe login error content",
                )

    def test_rejects_error_leaks_outside_javascript(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = self._files()
            files["assets/index-def.css"] += b"\n/* SENTINEL_DAED_PASSWORD_DO_NOT_RENDER */"
            archive = root / "source.tar.gz"
            self._write_archive(archive, files=files)
            self._assert_rejected_without_replacing_destination(
                archive,
                root / "destination",
                root / "provenance.json",
                "unsafe login error content",
            )

    def test_rejects_path_traversal_member(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = b"escape"
            info = tarfile.TarInfo(
                f"{SOURCE_ROOT}/apps/web/dist/../../../../escaped.txt"
            )
            info.size = len(payload)
            archive = root / "source.tar.gz"
            self._write_archive(archive, extra_members=[(info, payload)])
            self._assert_rejected_without_replacing_destination(
                archive,
                root / "destination",
                root / "provenance.json",
                "unsafe archive path",
            )
            self.assertFalse((root / "escaped.txt").exists())

    def test_rejects_symlink_under_dist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            info = tarfile.TarInfo(
                f"{SOURCE_ROOT}/apps/web/dist/assets/linked.js"
            )
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            archive = root / "source.tar.gz"
            self._write_archive(archive, extra_members=[(info, None)])
            self._assert_rejected_without_replacing_destination(
                archive,
                root / "destination",
                root / "provenance.json",
                "unsupported archive member",
            )


if __name__ == "__main__":
    unittest.main()
