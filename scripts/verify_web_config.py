#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="strict")


def require_exact_count(text: str, token: str, count: int, message: str) -> None:
    require(text.count(token) == count, message)


def location_body(config: str, pattern: str, message: str) -> str:
    match = re.search(pattern + r"\s*\{([^}]*)\}", config, re.DOTALL)
    require(match is not None, message)
    return match.group(1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    root = Path(p.parse_args().root)
    conf_dir = root / "packages/luci-app-athena/root/etc/nginx/conf.d"
    require(
        not (conf_dir / "athena-daed.conf").exists(),
        "bare location must not be loaded in http context",
    )
    locations = read_utf8(conf_dir / "athena-daed.locations")
    defaults = read_utf8(root / "packages/luci-app-athena/root/etc/uci-defaults/95-athena-web")
    panel = read_utf8(root / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js")
    luci_menu_path = root / "packages/luci-app-athena/root/usr/share/luci/menu.d/luci-app-athena.json"
    menu_path = root / "packages/luci-app-athena/root/usr/share/luci/menu.d/zz-athena-dashboard.json"
    dashboard_path = root / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/dashboard.js"
    chart_path = root / "packages/luci-app-athena/htdocs/luci-static/resources/athena/chart.js"
    css_path = root / "packages/luci-app-athena/htdocs/luci-static/resources/athena/dashboard.css"
    json.loads(read_utf8(luci_menu_path))
    menu = json.loads(read_utf8(menu_path))
    dashboard = read_utf8(dashboard_path)
    chart = read_utf8(chart_path)
    dashboard_css = read_utf8(css_path)
    static_ui = location_body(
        locations,
        r"location\s+/athena-daed/",
        "static DAED UI location is missing",
    )
    graphql = location_body(
        locations,
        r"location\s+=\s+/athena-daed/graphql",
        "DAED GraphQL proxy is missing",
    )
    require("root /www;" in static_ui, "DAED UI must be served from /www")
    require(
        "try_files $uri $uri/ /athena-daed/index.html;" in static_ui,
        "DAED UI SPA fallback is missing",
    )
    require("proxy_pass" not in static_ui, "DAED UI must not proxy the whole site")
    require(
        "proxy_pass http://127.0.0.1:2023/graphql;" in graphql,
        "DAED GraphQL upstream must be loopback-only",
    )
    require("root /www" not in graphql and "try_files" not in graphql, "GraphQL route must only proxy the backend")
    require("proxy_http_version 1.1" in graphql, "DAED GraphQL proxy must use HTTP/1.1")
    require("proxy_buffering off" in graphql, "DAED GraphQL buffering must be disabled")
    require("0.0.0.0:2023" not in locations + defaults + panel, "DAED must remain loopback-only")
    require("192.168.50.1:8080" in defaults + panel, "recovery endpoint is missing")
    require("src: '/athena-daed/'" in panel, "DAED panel iframe path is missing")
    require(panel.count("E('iframe'") == 1, "DAED panel must create exactly one iframe")
    require(
        "var ready = !!s.daed_running && !!s.daed_api_reachable" in panel,
        "DAED readiness gate is missing",
    )
    require(
        "if (!ready)" in panel and "_('后端未连接')" in panel,
        "DAED disconnected state must show only the concise backend message",
    )
    require(
        "\n\t\t\tpage.appendChild(E('iframe'" in panel,
        "DAED iframe must only be appended from the ready branch",
    )
    require("DAED 后端尚未就绪" not in panel, "legacy DAED error card remains")
    require("athena-health --verbose" not in panel, "disconnected state must not expose diagnostics")
    require("recovery_url" not in panel, "disconnected state must not expose the recovery URL")
    require(
        not re.search(r"https?://[^'\"\s]*:2023|192\.168\.50\.1:2023", panel),
        "browser-visible DAED port 2023 is forbidden",
    )
    require("set daed.config.listen_addr='127.0.0.1:2023'" in defaults, "DAED loopback default is missing")
    require("set daed.config.enabled='0'" in defaults, "DAED safe default is missing")
    for option in ("uhttpd.main.listen_http", "uhttpd.main.listen_https"):
        require(f"delete {option}" in defaults, f"default uHTTPd listener remains: {option}")
    require_exact_count(defaults, "192.168.50.1:8080", 1, "recovery listener must be unique")
    require("/usr/lib/lua/luci/sgi/uhttpd.lua" in defaults, "recovery LuCI handler is missing")

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
