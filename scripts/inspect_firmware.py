#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


REQUIRED = {
    "daed",
    "luci-app-daede",
    "athena-runtime",
    "luci-app-athena",
    "luci-theme-argon",
    "luci-app-argon-config",
    "uhttpd",
    "uhttpd-mod-lua",
}
REQUIRED_ALTERNATIVES = {"nginx-runtime": {"nginx", "nginx-ssl"}}
FORBIDDEN = {
    "smartdns",
    "luci-app-smartdns",
    "luci-app-openclash",
    "luci-app-passwall",
    "luci-app-homeproxy",
}
DASHBOARD_ROOTFS_FILES = (
    "/usr/lib/athena/dashboard.sh",
    "/www/luci-static/resources/athena/chart.js",
    "/www/luci-static/resources/athena/dashboard.css",
    "/www/luci-static/resources/view/athena/dashboard.js",
    "/usr/share/luci/menu.d/zz-athena-dashboard.json",
)
WEB_ROOTFS_FILES = (
    "/etc/nginx/conf.d/athena-daed.locations",
    "/etc/uci-defaults/95-athena-web",
    "/www/athena-recovery.html",
    "/www/luci-static/resources/view/athena/daed-panel.js",
    "/usr/share/luci/menu.d/luci-app-athena.json",
    "/usr/bin/daed",
)
WEB_FORBIDDEN_FILES = ("/etc/nginx/conf.d/athena-daed.conf",)


def read_utf8(rootfs: Path, relative: str) -> str:
    return (rootfs / relative.lstrip("/")).read_text(
        encoding="utf-8", errors="strict"
    )


def inspect_web(rootfs: Path) -> dict:
    missing = [
        path
        for path in WEB_ROOTFS_FILES
        if not (rootfs / path.lstrip("/")).is_file()
    ]
    forbidden = [
        path
        for path in WEB_FORBIDDEN_FILES
        if (rootfs / path.lstrip("/")).exists()
    ]

    defaults_path = "/etc/uci-defaults/95-athena-web"
    if defaults_path not in missing:
        defaults = read_utf8(rootfs, defaults_path)
        default_lines = {line.strip() for line in defaults.splitlines()}
        if "delete uhttpd.main.listen_http" not in default_lines:
            forbidden.append("uhttpd-primary-listener")
        if "delete uhttpd.main.listen_https" not in default_lines:
            forbidden.append("uhttpd-primary-https-listener")
        if "set daed.config.listen_addr='127.0.0.1:2023'" not in defaults:
            missing.append("daed-loopback-default")
        if "set daed.config.enabled='0'" not in defaults:
            missing.append("daed-safe-default")

    locations_path = "/etc/nginx/conf.d/athena-daed.locations"
    if locations_path not in missing:
        locations = read_utf8(rootfs, locations_path)
        if "location /athena-daed/" not in locations:
            missing.append("daed-ui-location")
        if "location = /athena-daed/graphql" not in locations:
            missing.append("daed-graphql-location")

    panel_path = "/www/luci-static/resources/view/athena/daed-panel.js"
    if panel_path not in missing:
        panel = read_utf8(rootfs, panel_path)
        if "/athena-daed/" not in panel:
            missing.append("daed-panel-same-origin-path")
        if ":2023" in panel:
            forbidden.append("daed-panel-browser-port")

    daed_endpoint = "missing"
    daed_path = rootfs / "usr/bin/daed"
    if daed_path.is_file():
        daed_bytes = daed_path.read_bytes()
        has_same_origin = b"/athena-daed/graphql" in daed_bytes
        has_browser_port = b":2023/graphql" in daed_bytes
        if has_browser_port:
            daed_endpoint = "browser-port"
            forbidden.append("daed-binary-browser-port")
        elif has_same_origin:
            daed_endpoint = "same-origin"
        else:
            daed_endpoint = "unknown"
            missing.append("daed-binary-same-origin-endpoint")

    return {
        "checked": True,
        "missing": sorted(set(missing)),
        "forbidden": sorted(set(forbidden)),
        "daed_endpoint": daed_endpoint,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--openwrt", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--kernel-limit", type=int, default=6291456)
    args = parser.parse_args()
    root = Path(args.openwrt)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    target = root / "bin/targets/qualcommax/ipq60xx"
    initramfs = list(target.glob("*jdcloud_re-cs-02*initramfs*uImage.itb"))
    sysupgrade = list(target.glob("*jdcloud_re-cs-02*squashfs-sysupgrade.bin"))
    packages = set()
    for manifest in target.glob("*manifest"):
        packages.update(
            line.split()[0]
            for line in manifest.read_text(errors="ignore").splitlines()
            if line.strip()
        )

    persistent = list((root / "build_dir").rglob("jdcloud_re-cs-02-uImage.itb"))
    size = max((path.stat().st_size for path in persistent), default=0)
    rootfs_candidates = sorted(
        (root / "build_dir").glob("target-*/root-qualcommax")
    )
    dashboard_checked = bool(rootfs_candidates)
    dashboard_missing = []
    web_integration = {
        "checked": False,
        "missing": [],
        "forbidden": [],
        "daed_endpoint": "not-checked",
    }
    if rootfs_candidates:
        rootfs = rootfs_candidates[0]
        dashboard_missing = [
            path
            for path in DASHBOARD_ROOTFS_FILES
            if not (rootfs / path.lstrip("/")).is_file()
        ]
        web_integration = inspect_web(rootfs)

    missing_packages = sorted(REQUIRED - packages) if packages else []
    if packages:
        missing_packages.extend(
            name
            for name, alternatives in REQUIRED_ALTERNATIVES.items()
            if packages.isdisjoint(alternatives)
        )

    report = {
        "initramfs": [str(path) for path in initramfs],
        "sysupgrade": [str(path) for path in sysupgrade],
        "kernel_bytes": size,
        "kernel_limit": args.kernel_limit,
        "kernel_margin": args.kernel_limit - size,
        "missing_packages": sorted(missing_packages),
        "forbidden_packages": sorted(FORBIDDEN & packages),
        "dashboard_files": {
            "checked": dashboard_checked,
            "missing": dashboard_missing,
        },
        "web_integration": web_integration,
    }
    (output / "firmware-inspection.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8", newline="\n"
    )
    (output / "kernel-size.txt").write_text(
        f"kernel_bytes={size}\nlimit={args.kernel_limit}\nmargin={args.kernel_limit-size}\n",
        encoding="utf-8",
        newline="\n",
    )
    failed = (
        len(initramfs) != 1
        or len(sysupgrade) != 1
        or size > args.kernel_limit
        or bool(report["missing_packages"])
        or bool(report["forbidden_packages"])
        or bool(dashboard_missing)
        or bool(web_integration["missing"])
        or bool(web_integration["forbidden"])
    )
    if failed:
        raise SystemExit(1)
    print("PASS: firmware inspection")


if __name__ == "__main__":
    main()
