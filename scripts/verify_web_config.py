#!/usr/bin/env python3
import argparse
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    root = Path(p.parse_args().root)
    conf = (root / "packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.conf").read_text(encoding="utf-8")
    defaults = (root / "packages/luci-app-athena/root/etc/uci-defaults/95-athena-web").read_text(encoding="utf-8")
    panel = (root / "packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js").read_text(encoding="utf-8")
    required = ["127.0.0.1:2023", "proxy_http_version 1.1", "proxy_buffering off"]
    assert all(x in conf for x in required)
    assert "0.0.0.0:2023" not in conf + defaults + panel
    assert "192.168.50.1:8080" in defaults + panel
    assert "/athena-daed/" in panel
    print("PASS: web configuration")

if __name__ == "__main__":
    main()
