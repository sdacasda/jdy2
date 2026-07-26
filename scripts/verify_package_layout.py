#!/usr/bin/env python3
from pathlib import Path
import argparse
import re


SCAN_SIGNATURE = re.compile(
    r"call\s+(?:Build/DefaultTargets|BuildPackage|KernelPackage)"
)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); root=Path(ap.parse_args().root)
    required=[
      "packages/athena-runtime/Makefile","packages/luci-app-athena/Makefile",
      "packages/athena-runtime/files/usr/bin/athena-setup",
      "packages/athena-runtime/files/usr/bin/athena-iot",
      "packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.conf"]
    missing=[p for p in required if not (root/p).is_file()]
    if missing: raise SystemExit("missing: "+", ".join(missing))

    runtime=(root/"packages/athena-runtime/Makefile").read_text(encoding="utf-8")
    luci=(root/"packages/luci-app-athena/Makefile").read_text(encoding="utf-8")
    if not SCAN_SIGNATURE.search(luci):
        raise SystemExit(
            "luci-app-athena is not discoverable by OpenWrt package scan"
        )

    dependency_lines=re.findall(r"^\s*DEPENDS\s*:?=\s*(.*)$", runtime, re.MULTILINE)
    dependency_tokens=set(" ".join(dependency_lines).split())
    forbidden={"+tar", "+gzip"} & dependency_tokens
    if forbidden:
        raise SystemExit(
            "athena-runtime must use base BusyBox tar/gzip applets; "
            "optional GNU archive packages can hide the package in Kconfig"
        )

    print("PASS: package layout")
if __name__=="__main__": main()
