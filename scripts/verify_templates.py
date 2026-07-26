#!/usr/bin/env python3
"""Static safety checks for DAED templates and maintained domain lists."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--templates", type=pathlib.Path, required=True)
    parser.add_argument("--rules", type=pathlib.Path, required=True)
    args = parser.parse_args()
    errors: list[str] = []
    required_templates = ("global.dae.tpl", "dns.dae.tpl", "routing.dae.tpl")
    required_rules = (
        "steam-proxy-domains.txt",
        "steam-direct-domains.txt",
        "xbox-proxy-domains.txt",
        "xbox-direct-domains.txt",
    )
    for name in required_templates:
        if not (args.templates / name).is_file():
            errors.append(f"missing template: {name}")
    for name in required_rules:
        path = args.rules / name
        if not path.is_file():
            errors.append(f"missing rule list: {name}")
            continue
        for number, value in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            value = value.strip()
            if not value or value.startswith("#"):
                continue
            if value != value.lower() or "://" in value or "/" in value or not re.fullmatch(r"[a-z0-9.-]+", value):
                errors.append(f"{name}:{number}: invalid normalized domain")

    routing_path = args.templates / "routing.dae.tpl"
    dns_path = args.templates / "dns.dae.tpl"
    if routing_path.is_file():
        routing = routing_path.read_text(encoding="utf-8")
        required = ("geoip:private", "must_direct", "dscp(0x4)", "dport(25565)", "fallback: {{PROXY_GROUP}}")
        for token in required:
            if token not in routing:
                errors.append(f"routing template missing: {token}")
        if re.search(r"^\s*l4proto\(udp\)\s*->\s*direct", routing, re.MULTILINE):
            errors.append("global UDP direct rule is prohibited")
        if "ff00::/0" in routing:
            errors.append("global IPv6 direct rule is prohibited")
        if routing.find("geoip:private") > routing.rfind("fallback: {{PROXY_GROUP}}"):
            errors.append("private rule appears after fallback")
    if dns_path.is_file():
        dns = dns_path.read_text(encoding="utf-8")
        try:
            fallback = dns.index("fallback: global_doh")
        except ValueError:
            errors.append("DNS global DoH fallback missing")
        else:
            for selector in ("sub()", "subnode()", "node()"):
                if selector not in dns or dns.index(selector) > fallback:
                    errors.append(f"{selector} must precede DNS fallback")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: DAED templates and rule lists are structurally safe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
