#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    root = Path(p.parse_args().root)
    conf = (root / "packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.conf").read_text(encoding="utf-8")
    defaults = (root / "packages/luci-app-athena/root/etc/uci-defaults/95-athena-web").read_text(encoding="utf-8")
    panel = (root / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js").read_text(encoding="utf-8")
    menu_path = root / "packages/luci-app-athena/root/usr/share/luci/menu.d/zz-athena-dashboard.json"
    dashboard_path = root / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/dashboard.js"
    chart_path = root / "packages/luci-app-athena/htdocs/luci-static/resources/athena/chart.js"
    css_path = root / "packages/luci-app-athena/htdocs/luci-static/resources/athena/dashboard.css"
    menu = json.loads(menu_path.read_text(encoding="utf-8"))
    dashboard = dashboard_path.read_text(encoding="utf-8")
    chart = chart_path.read_text(encoding="utf-8")
    dashboard_css = css_path.read_text(encoding="utf-8")
    required = ["127.0.0.1:2023", "proxy_http_version 1.1", "proxy_buffering off"]
    require(all(x in conf for x in required), "DAED reverse proxy is incomplete")
    require("0.0.0.0:2023" not in conf + defaults + panel, "DAED must remain loopback-only")
    require("192.168.50.1:8080" in defaults + panel, "recovery endpoint is missing")
    require("/athena-daed/" in panel, "DAED panel proxy path is missing")

    for route in ("admin/status/overview", "admin/services/athena/status"):
        require(route in menu, f"missing dashboard menu route: {route}")
        action = menu[route].get("action", {})
        require(action.get("type") == "view", f"{route} must use a LuCI view")
        require(action.get("path") == "athena/dashboard", f"{route} must open athena/dashboard")

    combined_dashboard = "\n".join((dashboard, chart, dashboard_css))
    forbidden = (
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
    for token in forbidden:
        require(token not in combined_dashboard, f"dashboard contains forbidden token: {token}")

    print("PASS: web configuration")

if __name__ == "__main__":
    main()
