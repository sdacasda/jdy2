#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import zlib
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
GZIP_MAGIC = b"\x1f\x8b\x08"
MAX_EMBEDDED_WEB_BYTES = 32 * 1024 * 1024
STATIC_WEB_ROOT = "/www/athena-daed"
STATIC_WEB_PROVENANCE = "/usr/share/athena/daed-static-web.json"
IMAGE_SUFFIXES = {".avif", ".gif", ".ico", ".jpeg", ".jpg", ".png", ".svg", ".webp"}


def embedded_gzip_payloads(binary: bytes):
    """Yield valid, bounded gzip members embedded in a Go ELF binary."""
    offset = 0
    while True:
        offset = binary.find(GZIP_MAGIC, offset)
        if offset < 0:
            return
        inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            payload = inflater.decompress(
                memoryview(binary)[offset:], MAX_EMBEDDED_WEB_BYTES + 1
            )
        except zlib.error:
            offset += 1
            continue
        if inflater.eof and len(payload) <= MAX_EMBEDDED_WEB_BYTES:
            yield payload
        offset += 1


def read_utf8(rootfs: Path, relative: str) -> str:
    return (rootfs / relative.lstrip("/")).read_text(
        encoding="utf-8", errors="strict"
    )


def parse_local_asset_references(index_html: str) -> list[str]:
    references = []
    for match in re.finditer(r"(?:src|href)\s*=\s*(['\"])(\./[^'\"]+)\1", index_html, re.IGNORECASE):
        reference = match.group(2)[2:].split("?", 1)[0].split("#", 1)[0]
        if reference and reference not in references:
            references.append(reference)
    return sorted(references)


def _tree_digest(entries: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    for entry in entries:
        digest.update(str(entry["path"]).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(entry["sha256"]).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def inspect_daed_static_ui(rootfs: Path) -> dict[str, object]:
    static_root = rootfs / STATIC_WEB_ROOT.lstrip("/")
    provenance_path = rootfs / STATIC_WEB_PROVENANCE.lstrip("/")
    errors: list[str] = []
    manifest: dict[str, object] = {}
    if not provenance_path.is_file():
        errors.append("missing-provenance")
    else:
        try:
            loaded = json.loads(provenance_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                manifest = loaded
            else:
                errors.append("invalid-provenance")
        except (OSError, UnicodeError, json.JSONDecodeError):
            errors.append("invalid-provenance")

    listed = manifest.get("files", [])
    if not isinstance(listed, list):
        listed = []
        errors.append("invalid-provenance-files")
    expected: dict[str, dict[str, object]] = {}
    for entry in listed:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            errors.append("invalid-provenance-entry")
            continue
        expected[str(entry["path"])] = entry

    actual_paths = sorted(
        path.relative_to(static_root).as_posix()
        for path in static_root.rglob("*")
        if path.is_file()
    ) if static_root.is_dir() else []
    for relative in sorted(set(expected) - set(actual_paths)):
        errors.append(f"missing:{relative}")
    for relative in sorted(set(actual_paths) - set(expected)):
        errors.append(f"unlisted:{relative}")

    actual_entries: list[dict[str, object]] = []
    for relative in actual_paths:
        payload = (static_root / relative).read_bytes()
        entry = {
            "path": relative,
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        actual_entries.append(entry)
        wanted = expected.get(relative)
        if wanted is not None:
            if wanted.get("size") != entry["size"]:
                errors.append(f"size:{relative}")
            if wanted.get("sha256") != entry["sha256"]:
                errors.append(f"hash:{relative}")

    tree_sha256 = _tree_digest(actual_entries)
    if manifest and manifest.get("file_count") != len(actual_entries):
        errors.append("file-count-mismatch")
    if manifest and manifest.get("tree_sha256") != tree_sha256:
        errors.append("tree-hash-mismatch")

    index_path = static_root / "index.html"
    references: list[str] = []
    browser_payload = b""
    if not index_path.is_file():
        if "index.html" not in expected:
            errors.append("missing:index.html")
    else:
        try:
            references = parse_local_asset_references(index_path.read_text(encoding="utf-8"))
        except UnicodeError:
            errors.append("invalid:index.html")
        for reference in references:
            if not (static_root / reference).is_file():
                errors.append(f"missing-reference:{reference}")

    javascript = [path for path in references if Path(path).suffix.lower() in {".js", ".mjs"}]
    stylesheets = [path for path in references if Path(path).suffix.lower() == ".css"]
    logos = [path for path in references if Path(path).suffix.lower() in IMAGE_SUFFIXES]
    if not javascript:
        errors.append("missing-javascript-reference")
    if not stylesheets:
        errors.append("missing-stylesheet-reference")
    if not logos:
        errors.append("missing-logo-reference")

    for relative in actual_paths:
        if Path(relative).suffix.lower() in {".html", ".js", ".mjs"}:
            browser_payload += (static_root / relative).read_bytes() + b"\n"
    if any(token in browser_payload for token in (b":2023/graphql", b"127.0.0.1:2023", b"192.168.50.1:2023")):
        errors.append("browser-port-2023")
    graphql_endpoint = "/athena-daed/graphql" if b"/athena-daed/graphql" in browser_payload else "missing"
    if graphql_endpoint == "missing":
        errors.append("missing-same-origin-graphql")

    return {
        "checked": True,
        "index": f"{STATIC_WEB_ROOT}/index.html",
        "file_count": len(actual_entries),
        "tree_sha256": tree_sha256,
        "javascript": [f"{STATIC_WEB_ROOT}/{path}" for path in javascript],
        "stylesheets": [f"{STATIC_WEB_ROOT}/{path}" for path in stylesheets],
        "logos": [f"{STATIC_WEB_ROOT}/{path}" for path in logos],
        "graphql_endpoint": graphql_endpoint,
        "errors": sorted(set(errors)),
    }


def _location_body(config: str, pattern: str) -> str | None:
    match = re.search(pattern + r"\s*\{([^}]*)\}", config, re.DOTALL)
    return match.group(1) if match else None


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
        static_ui = _location_body(locations, r"location\s+/athena-daed/")
        graphql = _location_body(locations, r"location\s+=\s+/athena-daed/graphql")
        if static_ui is None:
            missing.append("daed-ui-location")
        else:
            if "root /www;" not in static_ui or "try_files $uri $uri/ /athena-daed/index.html;" not in static_ui:
                missing.append("daed-static-ui-routing")
            if "proxy_pass" in static_ui:
                forbidden.append("daed-ui-whole-site-proxy")
        if graphql is None:
            missing.append("daed-graphql-location")
        elif "proxy_pass http://127.0.0.1:2023/graphql;" not in graphql:
            missing.append("daed-graphql-loopback-proxy")

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
        if not (has_same_origin and has_browser_port):
            for payload in embedded_gzip_payloads(daed_bytes):
                has_same_origin = has_same_origin or b"/athena-daed/graphql" in payload
                has_browser_port = has_browser_port or b":2023/graphql" in payload
                if has_same_origin and has_browser_port:
                    break
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
    daed_static_ui = {
        "checked": False,
        "index": f"{STATIC_WEB_ROOT}/index.html",
        "file_count": 0,
        "tree_sha256": "",
        "javascript": [],
        "stylesheets": [],
        "logos": [],
        "graphql_endpoint": "not-checked",
        "errors": [],
    }
    if rootfs_candidates:
        rootfs = rootfs_candidates[0]
        dashboard_missing = [
            path
            for path in DASHBOARD_ROOTFS_FILES
            if not (rootfs / path.lstrip("/")).is_file()
        ]
        web_integration = inspect_web(rootfs)
        daed_static_ui = inspect_daed_static_ui(rootfs)

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
        "daed_static_ui": daed_static_ui,
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
        or bool(daed_static_ui["errors"])
    )
    if failed:
        raise SystemExit(1)
    print("PASS: firmware inspection")


if __name__ == "__main__":
    main()
