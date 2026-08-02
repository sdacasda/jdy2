#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import re


SCAN_SIGNATURE = re.compile(
    r"call\s+(?:Build/DefaultTargets|BuildPackage|KernelPackage)"
)

DASHBOARD_FILES = (
    "packages/athena-runtime/files/usr/lib/athena/dashboard.sh",
    "packages/luci-app-athena/htdocs/luci-static/resources/athena/chart.js",
    "packages/luci-app-athena/htdocs/luci-static/resources/athena/dashboard.css",
    "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/dashboard.js",
    "packages/luci-app-athena/root/usr/share/luci/menu.d/zz-athena-dashboard.json",
)

DASHBOARD_FORBIDDEN = (
    "http://",
    "https://",
    "fs.exec",
    "uci.set",
    "uci.commit",
    "localStorage",
    "sessionStorage",
    "runtime_apply",
    "rollback",
)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); root=Path(ap.parse_args().root)
    required=[
      "packages/athena-runtime/Makefile","packages/luci-app-athena/Makefile",
      "packages/athena-runtime/files/usr/bin/athena-setup",
      "packages/athena-runtime/files/usr/bin/athena-iot",
      "packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.locations",
      *DASHBOARD_FILES]
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

    menu_path = root / DASHBOARD_FILES[-1]
    try:
        menu = json.loads(menu_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid dashboard menu JSON: {exc}") from exc

    for route in ("admin/status/overview", "admin/services/athena/status"):
        action = menu.get(route, {}).get("action", {})
        if action.get("type") != "view" or action.get("path") != "athena/dashboard":
            raise SystemExit(f"dashboard menu must override {route}")

    dashboard_text = "\n".join(
        (root / relative).read_text(encoding="utf-8")
        for relative in DASHBOARD_FILES[1:4]
    )
    for token in DASHBOARD_FORBIDDEN:
        if token in dashboard_text:
            raise SystemExit(f"dashboard contains forbidden token: {token}")

    print("PASS: package layout")
if __name__=="__main__": main()
