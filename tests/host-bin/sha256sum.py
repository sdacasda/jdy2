import hashlib
import pathlib
import sys


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "-c":
        manifest = pathlib.Path(sys.argv[2])
        ok = True
        for line in manifest.read_text(encoding="utf-8").splitlines():
            expected, name = line.split(maxsplit=1)
            name = name.lstrip("*")
            path = pathlib.Path(name)
            current = digest(path)
            print(f"{name}: {'OK' if current == expected else 'FAILED'}")
            ok = ok and current == expected
        return 0 if ok else 1
    for value in sys.argv[1:]:
        path = pathlib.Path(value)
        print(f"{digest(path)}  {value}")
    return 0


raise SystemExit(main())
