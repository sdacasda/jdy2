# Athena AX6600 DAED v19 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing JDCloud RE-CS-02 LiBwrt build project from v18 to a safe, reproducible v19 release with Argon, loopback-only DAED management, guided DAED template generation, stable routing defaults, runtime optimization, health checks, backups, rollback, and hardened CI artifacts.

**Architecture:** Keep the existing GitHub Actions firmware build pipeline and split v19 into two local OpenWrt packages: `athena-runtime` owns all system-side commands, state, templates, and init behavior; `luci-app-athena` is a thin LuCI frontend that calls rpcd/ubus-backed commands and embeds the native DAED UI through a same-origin Nginx reverse proxy. Build-time scripts only import pinned third-party packages, inject safe first-boot defaults, validate the final configuration, and assemble release artifacts.

**Tech Stack:** POSIX/BusyBox shell, OpenWrt `procd` and UCI, rpcd/ubus, LuCI JavaScript views, Nginx, uhttpd recovery listener, Python 3 CI validators, GitHub Actions YAML, LiBwrt/OpenWrt package Makefiles, DAED/DAE configuration templates.

## Global Constraints

- Device is `JDCloud RE-CS-02`; target is `qualcommax/ipq60xx`; kernel line remains LiBwrt 6.12.x.
- Default LAN is exactly `192.168.50.1/24`; WAN remains DHCP client for an upstream modem/router.
- DAED is disabled on first boot and is never configured by writing `/etc/daed/wing.db` directly.
- DAED management listens on `127.0.0.1:2023`; port 2023 is not exposed to LAN or WAN.
- Normal UI uses Nginx and Argon; recovery UI uses uhttpd on LAN-only port `8080` with Bootstrap available.
- SmartDNS, OpenClash, PassWall, and HomeProxy are excluded.
- Chinese IPv4/IPv6 is direct; non-Chinese IPv4/IPv6 is proxied by default.
- Domestic DNS uses direct UDP; global DNS uses DoH through the proxy; node/subscription resolution uses direct bootstrap DNS.
- A global `all UDP -> direct` rule and a global `all IPv6 -> direct` rule are prohibited.
- Steam downloads/CDNs, selected gaming UDP, Minecraft defaults, and BT traffic marked with DSCP `0x4` are direct.
- NSS firmware, NSS data path, ath11k, QCN9074, and Wi-Fi offload remain; ECM IPv4/IPv6 frontends and OpenWrt software/hardware flow offload are stopped/disabled.
- CPU governor defaults to `performance`; DAED priority defaults to nice `-5`; IRQ/RPS/XPS are not rewritten by default.
- Every state-changing command must be idempotent, log credential-safe output, and support verified backup/rollback.
- Public source and generated artifacts must not contain real node links, UUIDs, passwords, tokens, keys, personal MAC addresses, Wi-Fi credentials, or the user's node hostname.
- Persistent kernel image hard limit is `6291456` bytes; less than `131072` bytes remaining is a warning; exceeding the limit fails CI.
- First public build is `v19.0.0-rc1`; v18 to v19 persistent upgrade requires `sysupgrade -n` after initramfs validation.

---

## Planned File Map

### Existing files to replace or substantially modify

- `.github/workflows/build-athena-final-candidate.yml` → replaced by `.github/workflows/build-athena-v19.yml`; owns reproducible build, validation, compilation, package/image inspection, and artifact upload.
- `config/athena-final-candidate.config` → replaced by `config/athena-v19.config`; owns package selection and target configuration.
- `scripts/prepare_packages.sh`; imports pinned external packages and local v19 packages into the LiBwrt tree.
- `scripts/inject_runtime.sh`; limited to first-boot network, web recovery, DAED-off defaults, and diagnostic page injection.
- `scripts/verify_config.sh`; validates effective OpenWrt configuration and package conflicts.
- `scripts/project_check.py`; replaced by broader project validators.
- `scripts/collect_output.sh`; creates the v19 release artifact layout and canonical firmware names.
- `scripts/verify_after_flash.sh`; expanded into the post-flash acceptance tool shipped with artifacts.
- `README.md`, `CHANGELOG.md`, `PROJECT.json`, `AUDIT.md`, `docs/BUILD.md`, `docs/FLASH.md`; updated for v19.

### New source and test files

- `SOURCES.lock.json`; exact full commit IDs for LiBwrt, DAED feed, BTF, Athena LED, Argon, Argon config, and Go feed.
- `packages/athena-runtime/Makefile`; OpenWrt package manifest.
- `packages/athena-runtime/files/etc/config/athena`; supported UCI defaults.
- `packages/athena-runtime/files/etc/init.d/athena-runtime`; applies ECM, flow-offload, governor, and DAED process policy.
- `packages/athena-runtime/files/usr/lib/athena/common.sh`; logging, locking, UCI, redaction, atomic-write, and platform helpers.
- `packages/athena-runtime/files/usr/lib/athena/backup.sh`; backup and manifest implementation.
- `packages/athena-runtime/files/usr/lib/athena/templates.sh`; safe template rendering and rule-list composition.
- `packages/athena-runtime/files/usr/lib/athena/checks.sh`; reusable health/preflight probes.
- `packages/athena-runtime/files/usr/bin/athena-setup`; setup state machine.
- `packages/athena-runtime/files/usr/bin/athena-health`; human and JSON health output.
- `packages/athena-runtime/files/usr/bin/athena-backup`; backup CLI.
- `packages/athena-runtime/files/usr/bin/athena-rollback`; rollback CLI.
- `packages/athena-runtime/files/usr/bin/athena-runtime`; runtime status/apply CLI.
- `packages/athena-runtime/files/usr/bin/athena-iot`; optional 2.4 GHz IoT compatibility SSID manager.
- `packages/athena-runtime/files/usr/bin/athena-info`; build/source metadata CLI.
- `packages/athena-runtime/files/usr/bin/athena-feature-check`; expanded feature inventory.
- `packages/athena-runtime/files/usr/share/athena/templates/{global,dns,routing}.dae.tpl`; DAED import templates.
- `packages/athena-runtime/files/usr/share/athena/rules/{steam-proxy,steam-direct,xbox-proxy,xbox-direct}-domains.txt`; versioned routing inputs.
- `packages/athena-runtime/files/usr/share/rpcd/acl.d/luci-app-athena.json`; least-privilege LuCI permissions.
- `packages/athena-runtime/files/usr/libexec/rpcd/athena`; rpcd executable backend.
- `packages/luci-app-athena/Makefile`; LuCI package manifest.
- `packages/luci-app-athena/root/usr/share/luci/menu.d/luci-app-athena.json`; LuCI menu entries.
- `packages/luci-app-athena/htdocs/luci-static/resources/view/athena/{status,daed-panel,templates,backups}.js`; LuCI pages.
- `packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.conf`; same-origin DAED proxy.
- `packages/luci-app-athena/root/etc/uci-defaults/95-athena-web`; Nginx/uhttpd/Argon defaults.
- `scripts/verify_project.py`; repository structure, lock, permissions, and metadata validation.
- `scripts/verify_templates.py`; deterministic template and routing-policy tests.
- `scripts/verify_package_layout.py`; package file placement and executable-mode checks.
- `scripts/verify_web_config.py`; Nginx, recovery listener, menu, and loopback-listener validation.
- `scripts/security_check.py`; credential and forbidden-setting scan.
- `scripts/test_runtime_scripts.sh`; host-side BusyBox-compatible runtime unit tests with command stubs.
- `tests/fixtures/rootfs/`; isolated fake root for runtime tests.
- `tests/runtime/test_iot.sh`; fake-UCI tests for radio discovery, compatibility defaults, idempotence, and safe removal.
- `docs/{SETUP,DAED_CONFIG,GAMING,RECOVERY,ARCHITECTURE}.md`; user documentation.
- `THIRD_PARTY_NOTICES.md`, `CHANGE_SUMMARY.md`; release/source disclosures.

---

### Task 1: Establish v19 Metadata, Source Locks, and Repository Validation

**Files:**
- Create: `SOURCES.lock.json`
- Create: `scripts/verify_project.py`
- Create: `scripts/security_check.py`
- Modify: `PROJECT.json`
- Modify: `.gitignore`
- Test: `tests/test_project_validation.py`

**Interfaces:**
- Produces: `SOURCES.lock.json` with keys `libwrt`, `daede`, `vmlinux_btf`, `athena_led`, `golang`, `argon`, and `argon_config`; each value has `repository` and 40-character lowercase hexadecimal `commit`.
- Produces: `scripts/verify_project.py --root PATH` returning exit 0 only for a complete v19 project.
- Produces: `scripts/security_check.py --root PATH` returning exit 0 only when no secret pattern or forbidden configuration is present.

- [ ] **Step 1: Write repository-validation tests**

Create `tests/test_project_validation.py` with tests that copy a minimal fixture to a temporary directory, invoke each validator with `subprocess.run()`, and assert:

```python
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(script: str, root: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / script), "--root", str(root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def test_lock_rejects_moving_ref(tmp_path: pathlib.Path) -> None:
    lock = {
        name: {"repository": "https://example.com/repo.git", "commit": "main"}
        for name in ("libwrt", "daede", "vmlinux_btf", "athena_led", "golang", "argon", "argon_config")
    }
    (tmp_path / "SOURCES.lock.json").write_text(json.dumps(lock), encoding="utf-8")
    result = run("scripts/verify_project.py", tmp_path)
    assert result.returncode != 0
    assert "40-character commit" in result.stdout


def test_security_scan_rejects_vless_link(tmp_path: pathlib.Path) -> None:
    (tmp_path / "bad.txt").write_text("vless://secret@example.com:443", encoding="utf-8")
    result = run("scripts/security_check.py", tmp_path)
    assert result.returncode != 0
    assert "node link" in result.stdout
```

- [ ] **Step 2: Run tests and confirm they fail before validators exist**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_project_validation.py' -v
```

Expected: FAIL because `scripts/verify_project.py` and `scripts/security_check.py` do not exist.

- [ ] **Step 3: Resolve exact upstream commits and write `SOURCES.lock.json`**

Use `git ls-remote` against the currently approved repository/tag or branch, record the resulting full SHA once, and commit the SHA. The command sequence must be reproducible:

```bash
resolve_ref() {
    repo="$1"
    ref="$2"
    git ls-remote "$repo" "$ref" | awk 'NR == 1 { print $1 }'
}

resolve_ref https://github.com/LiBwrt/openwrt-6.x.git cf9444c1b20458687898489b36e1aebf56d9baf2
resolve_ref https://github.com/kenzok8/openwrt-daede.git refs/tags/v2026.07.09
resolve_ref https://github.com/kenzok8/vmlinux-btf.git refs/heads/main
resolve_ref https://github.com/NONGFAH/luci-app-athena-led.git refs/heads/main
resolve_ref https://github.com/sbwml/packages_lang_golang.git refs/heads/26.x
resolve_ref https://github.com/jerrykuku/luci-theme-argon.git refs/heads/master
resolve_ref https://github.com/jerrykuku/luci-app-argon-config.git refs/heads/master
```

Fail the task if any command returns blank or a non-40-character SHA. Do not retain `main`, `master`, `26.x`, or a tag name in the committed `commit` fields.

- [ ] **Step 4: Implement validators and v19 metadata**

Implement `verify_project.py` to validate required files, project version `v19.0.0-rc1`, target/device, full source SHAs, executable modes, no legacy workflow/config filenames, and no unresolved template variables outside `.tpl` files.

Implement `security_check.py` to scan text files while excluding `.git`, archives, and generated firmware. Reject complete proxy URLs, UUID-like credentials except documented nil/example values, PEM private keys, subscription/token assignments, private key fields, non-example MAC addresses, `listen_addr='0.0.0.0:2023'`, and personal hostnames. Emit path and line number without echoing the secret.

Update `PROJECT.json` to identify v19, its two packages, safe setup model, LAN address, build outputs, and source-lock file.

- [ ] **Step 5: Run validation tests**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_project_validation.py' -v
python3 scripts/verify_project.py --root .
python3 scripts/security_check.py --root .
```

Expected: all tests PASS; both validators exit 0.

- [ ] **Step 6: Commit metadata and validators**

```bash
git add SOURCES.lock.json PROJECT.json .gitignore scripts/verify_project.py scripts/security_check.py tests/test_project_validation.py
git commit -m "build: lock v19 sources and validate project"
```

---

### Task 2: Create the `athena-runtime` Package and Shared Shell Library

**Files:**
- Create: `packages/athena-runtime/Makefile`
- Create: `packages/athena-runtime/files/etc/config/athena`
- Create: `packages/athena-runtime/files/usr/lib/athena/common.sh`
- Create: `tests/runtime/test_common.sh`
- Create: `scripts/test_runtime_scripts.sh`

**Interfaces:**
- Produces shell functions: `athena_log LEVEL MESSAGE`, `athena_die MESSAGE`, `athena_lock NAME`, `athena_unlock`, `athena_atomic_write TARGET`, `athena_redact`, `athena_uci_get PACKAGE.SECTION.OPTION DEFAULT`, `athena_is_ipv4`, `athena_is_mac`, and `athena_root PATH`.
- All runtime commands consume `ATHENA_ROOT` for host tests; default is `/` on the router.

- [ ] **Step 1: Write failing shared-library tests**

Create `tests/runtime/test_common.sh` that sources `common.sh` with a temporary `ATHENA_ROOT` and verifies:

```sh
#!/bin/sh
set -eu

fail() { echo "FAIL: $*" >&2; exit 1; }
ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT
ATHENA_ROOT="$ROOT"
. "${PROJECT_ROOT}/packages/athena-runtime/files/usr/lib/athena/common.sh"

[ "$(athena_root /etc/config/athena)" = "$ROOT/etc/config/athena" ] || fail athena_root
athena_is_ipv4 223.5.5.5 || fail valid_ipv4
! athena_is_ipv4 999.5.5.5 || fail invalid_ipv4
athena_is_mac AA:BB:CC:DD:EE:FF || fail valid_mac
! athena_is_mac AA:BB:CC:DD:EE || fail invalid_mac
printf '%s\n' 'vless://user@example.com token=abcdef' | athena_redact | grep -q 'REDACTED' || fail redact
```

- [ ] **Step 2: Run the test and confirm failure**

Run:

```bash
PROJECT_ROOT="$PWD" sh tests/runtime/test_common.sh
```

Expected: FAIL because `common.sh` does not exist.

- [ ] **Step 3: Implement package metadata, UCI defaults, and shared functions**

The Makefile installs only focused files and depends on `bash` only if an implementation proves BusyBox `ash` insufficient; the preferred dependency set is `+jsonfilter +jshn +rpcd +ucode +curl +ca-bundle +tar +gzip +coreutils-stat` with no SmartDNS dependency.

Default `/etc/config/athena` must include:

```uci
config athena 'main'
    option enabled '0'
    option version '19'
    option profile 'stable'
    option lan_ip '192.168.50.1'
    option backup_retention '3'
    option ecm_policy 'stop_frontend'
    option flow_offload '0'
    option cpu_governor 'performance'
    option daed_priority '-5'
    option daed_affinity 'auto'
    option china_dns_primary '223.5.5.5'
    option china_dns_secondary '119.29.29.29'
    option global_doh 'https://dns.google:443/dns-query'
    option bt_mode 'dscp'
    option bt_dscp '0x4'
    option quic_policy 'proxy'
    option disable_ech '0'
```

Use atomic temporary-file-and-rename writes and a lock directory under `/var/lock/athena-<name>.lock`.

- [ ] **Step 4: Add one test runner for all runtime shell tests**

Implement `scripts/test_runtime_scripts.sh` to discover `tests/runtime/test_*.sh`, export `PROJECT_ROOT`, run each with `sh`, aggregate failures, and exit non-zero if any test fails.

- [ ] **Step 5: Run shell tests and syntax checks**

```bash
bash -n scripts/test_runtime_scripts.sh
find packages/athena-runtime/files -type f -name '*.sh' -o -path '*/usr/bin/*' | xargs -r -n1 sh -n
bash scripts/test_runtime_scripts.sh
```

Expected: PASS.

- [ ] **Step 6: Commit runtime foundation**

```bash
git add packages/athena-runtime scripts/test_runtime_scripts.sh tests/runtime/test_common.sh
git commit -m "feat: add athena runtime package foundation"
```

---

### Task 3: Implement Verified Backup and Rollback

**Files:**
- Create: `packages/athena-runtime/files/usr/lib/athena/backup.sh`
- Create: `packages/athena-runtime/files/usr/bin/athena-backup`
- Create: `packages/athena-runtime/files/usr/bin/athena-rollback`
- Test: `tests/runtime/test_backup.sh`
- Test: `tests/runtime/test_rollback.sh`

**Interfaces:**
- Produces: `athena_backup_create [LABEL]` printing the created backup directory.
- Produces: `athena_backup_verify DIRECTORY` returning 0 only when all manifest checksums match.
- Produces CLI: `athena-backup`, `athena-backup --list`, `athena-rollback [BACKUP_ID]`, and `athena-rollback --component daed BACKUP_ID`.
- Backup root is `${ATHENA_ROOT}/root/athena-backups`; default retention comes from UCI and is 3.

- [ ] **Step 1: Write failing backup tests**

The backup test creates fake `/etc/config`, `/etc/daed/wing.db`, Nginx/uhttpd files, and runtime state under `ATHENA_ROOT`; invokes `athena-backup`; then asserts presence of:

```text
manifest.txt
checksums.sha256
etc-config.tar.gz
daed-database.tar.gz
web-config.tar.gz
runtime-config.tar.gz
system-report.txt
```

It modifies `wing.db`, invokes rollback for component `daed`, and asserts the original bytes return.

- [ ] **Step 2: Run tests and confirm failure**

```bash
bash scripts/test_runtime_scripts.sh
```

Expected: backup/rollback tests FAIL because commands do not exist.

- [ ] **Step 3: Implement backup creation and verification**

Backup must:

1. Acquire `athena_lock backup`.
2. Create a staging directory with mode `0700`.
3. Archive only paths that exist.
4. Generate a manifest recording timestamp, v19 version, device model when available, services, UCI state, and archive members.
5. Generate `checksums.sha256` from all payload files.
6. Verify checksums before renaming staging into its final timestamp directory.
7. Remove oldest verified backups only after success, preserving the newest three by default.
8. Never include `/var/log/daed/daed.log` or other potentially sensitive full logs; `system-report.txt` contains counts and service state only.

- [ ] **Step 4: Implement component-aware rollback**

Rollback must verify the selected backup first, stop DAED for DAED restoration, extract through a staging directory, replace files atomically, restore UCI configuration, restart only affected services, and run a basic LAN/default-route/DNS check. Reject unknown backup IDs and path traversal.

- [ ] **Step 5: Run tests**

```bash
bash scripts/test_runtime_scripts.sh
```

Expected: backup and rollback tests PASS, including checksum-corruption rejection and retention behavior.

- [ ] **Step 6: Commit backup and rollback**

```bash
git add packages/athena-runtime/files/usr/lib/athena/backup.sh packages/athena-runtime/files/usr/bin/athena-backup packages/athena-runtime/files/usr/bin/athena-rollback tests/runtime/test_backup.sh tests/runtime/test_rollback.sh
git commit -m "feat: add verified backup and rollback"
```

---

### Task 4: Implement DAED Templates, Domain Lists, and Deterministic Rendering

**Files:**
- Create: `packages/athena-runtime/files/usr/share/athena/templates/global.dae.tpl`
- Create: `packages/athena-runtime/files/usr/share/athena/templates/dns.dae.tpl`
- Create: `packages/athena-runtime/files/usr/share/athena/templates/routing.dae.tpl`
- Create: `packages/athena-runtime/files/usr/share/athena/rules/steam-proxy-domains.txt`
- Create: `packages/athena-runtime/files/usr/share/athena/rules/steam-direct-domains.txt`
- Create: `packages/athena-runtime/files/usr/share/athena/rules/xbox-proxy-domains.txt`
- Create: `packages/athena-runtime/files/usr/share/athena/rules/xbox-direct-domains.txt`
- Create: `packages/athena-runtime/files/usr/lib/athena/templates.sh`
- Create: `scripts/verify_templates.py`
- Test: `tests/test_templates.py`

**Interfaces:**
- Produces: `athena_render_templates OUTPUT_DIR PROXY_GROUP NODE_HOSTNAME NODE_IPS GAME_MACS`.
- Inputs are validated and escaped before substitution; `PROXY_GROUP` permits letters, numbers, `_`, `-`, and spaces; node hostnames must be DNS names; IPs and MACs are comma-separated validated values.
- Generated outputs are exactly `global.dae`, `dns.dae`, `routing.dae`, and `IMPORT.md`.

- [ ] **Step 1: Write failing template-policy tests**

`tests/test_templates.py` must render with fixture values and assert:

- no `{{...}}` remains;
- `node()`, `subnode()`, and `sub()` precede DNS fallback;
- bootstrap DNS is `must_direct` before default proxy fallback;
- private/multicast rules precede all public routing;
- Steam direct and proxy lists are distinct;
- DSCP `0x4` is direct;
- Minecraft ports are direct;
- no regex matches `l4proto\(udp\).*->\s*direct` without a MAC, port, or DSCP predicate;
- no all-IPv6 direct rule exists;
- default fallback is the selected proxy group;
- QUIC `proxy` produces no global block rule; QUIC `block` emits only UDP/443 block before fallback.

- [ ] **Step 2: Run tests and confirm failure**

```bash
python3 -m unittest discover -s tests -p 'test_templates.py' -v
```

Expected: FAIL because templates and renderer are absent.

- [ ] **Step 3: Write templates and maintained domain lists**

Use DAED syntax already approved in the design. Domain-list files contain one normalized suffix per line, comments beginning with `#`, no schemes, paths, or credentials. Generate rule blocks from lists rather than embedding long lists in shell.

The DNS template must default to direct UDP domestic upstreams and a global DoH upstream. It must not reject HTTPS records unless `disable_ech=1`.

- [ ] **Step 4: Implement safe renderer**

Do not use `eval`. Read templates linearly and replace only a fixed allowlist of placeholders. Reject newline characters in all scalar inputs. Write output to a temporary directory, run static verification, then atomically replace `/etc/athena/generated`.

`IMPORT.md` must give exact DAED UI import order and state that the user must select a proxy group and start DAED manually.

- [ ] **Step 5: Run template tests and security scan**

```bash
python3 -m unittest discover -s tests -p 'test_templates.py' -v
python3 scripts/verify_templates.py --templates packages/athena-runtime/files/usr/share/athena/templates --rules packages/athena-runtime/files/usr/share/athena/rules
python3 scripts/security_check.py --root .
```

Expected: PASS.

- [ ] **Step 6: Commit templates and renderer**

```bash
git add packages/athena-runtime/files/usr/share/athena packages/athena-runtime/files/usr/lib/athena/templates.sh scripts/verify_templates.py tests/test_templates.py
git commit -m "feat: generate safe daed configuration templates"
```

---

### Task 5: Implement Runtime Policy Service and CLI

**Files:**
- Create: `packages/athena-runtime/files/etc/init.d/athena-runtime`
- Create: `packages/athena-runtime/files/usr/bin/athena-runtime`
- Test: `tests/runtime/test_runtime_policy.sh`

**Interfaces:**
- Init service supports `start`, `stop`, `restart`, and `status` through OpenWrt rc.common/procd conventions.
- CLI supports `athena-runtime apply`, `athena-runtime status`, and `athena-runtime restore-defaults`.
- Runtime policy reads `/etc/config/athena`; no hidden hard-coded policy exists outside UCI defaults.

- [ ] **Step 1: Write failing policy tests with fake sysfs and command stubs**

The test root contains writable fake files for:

```text
/sys/kernel/debug/ecm/front_end_ipv4_stop
/sys/kernel/debug/ecm/front_end_ipv6_stop
/sys/devices/system/cpu/cpufreq/policy0/scaling_governor
```

Stub `uci`, `pidof`, `renice`, and `taskset`. Assert `apply` writes `1` to both ECM stop flags, sets both flow-offload options to `0`, writes `performance`, applies nice `-5`, and does not invoke `taskset` when affinity is `auto`.

- [ ] **Step 2: Run test and confirm failure**

```bash
bash scripts/test_runtime_scripts.sh
```

Expected: runtime-policy test FAIL.

- [ ] **Step 3: Implement idempotent runtime policy**

The service waits up to 30 seconds for ECM debugfs nodes, writes stop flags only when writable, sets and commits firewall offload settings only when changed, applies available cpufreq policies, adjusts DAED priority when running, and applies explicit affinity only when UCI is not `auto`.

It must never unload ECM/NSS modules, write `defunct_all`, rewrite IRQ affinity, or enable RPS/XPS.

`status` prints machine-parsable `key=value` lines for ECM flags/counts, flow-offload settings, governor values, DAED PID/nice/affinity, and NSS module presence.

- [ ] **Step 4: Run runtime tests**

```bash
bash scripts/test_runtime_scripts.sh
```

Expected: PASS; repeated `apply` yields identical state and no duplicate UCI sections.

- [ ] **Step 5: Commit runtime service**

```bash
git add packages/athena-runtime/files/etc/init.d/athena-runtime packages/athena-runtime/files/usr/bin/athena-runtime tests/runtime/test_runtime_policy.sh
git commit -m "feat: apply stable ecm and cpu runtime policy"
```

---

### Task 6: Implement Reusable Health Checks and User-Facing Diagnostics

**Files:**
- Create: `packages/athena-runtime/files/usr/lib/athena/checks.sh`
- Create: `packages/athena-runtime/files/usr/bin/athena-health`
- Create: `packages/athena-runtime/files/usr/bin/athena-info`
- Create: `packages/athena-runtime/files/usr/bin/athena-feature-check`
- Test: `tests/runtime/test_health.sh`

**Interfaces:**
- Produces check function output records with fields `id`, `severity`, `status`, `summary`, and `detail`.
- `athena-health` supports default concise output, `--verbose`, and `--json`.
- Exit code is 0 for PASS/WARN-only, 2 when one or more critical checks FAIL, and 64 for invalid arguments.

- [ ] **Step 1: Write failing health-output tests**

Stub `ubus`, `uci`, `nslookup`, `ip`, `curl`, and log files. Test that:

- a healthy fixture emits valid JSON and exit 0;
- no default route is a critical FAIL and exit 2;
- DAED stopped before initialization is WARN, not FAIL;
- post-initialization DAED stopped is FAIL;
- bootstrap resolver errors are counted without outputting the affected domain;
- ECM stop flags at `0` are WARN before initialization and FAIL after stable profile activation;
- `--verbose` shows actionable commands but no secrets.

- [ ] **Step 2: Run tests and confirm failure**

```bash
bash scripts/test_runtime_scripts.sh
```

Expected: health tests FAIL.

- [ ] **Step 3: Implement checks**

Checks cover device/target, memory/free space, LAN address, WAN lease/default routes, dnsmasq, domestic DNS, global DNS, node bootstrap resolution when configured, DAED process/API, Nginx proxy, recovery uhttpd, IPv4/IPv6, ECM flags/counts, flow offload, governor, log error counts, generated template presence, backup availability, and setup state.

Use bounded timeouts for all network probes. Never make internet success a prerequisite for accessing local recovery.

- [ ] **Step 4: Implement metadata and feature inventory commands**

`athena-info` reads `/etc/athena-release`, UCI, and installed package versions. `athena-feature-check` extends the v18 command and reports BTF, DAED, Argon, Nginx, recovery listener, WOL, Athena LED, NSS modules, ath11k/QCN9074 firmware, and v19 command availability.

- [ ] **Step 5: Run tests**

```bash
bash scripts/test_runtime_scripts.sh
```

Expected: PASS.

- [ ] **Step 6: Commit diagnostics**

```bash
git add packages/athena-runtime/files/usr/lib/athena/checks.sh packages/athena-runtime/files/usr/bin/athena-health packages/athena-runtime/files/usr/bin/athena-info packages/athena-runtime/files/usr/bin/athena-feature-check tests/runtime/test_health.sh
git commit -m "feat: add athena health and feature diagnostics"
```

---

### Task 6A: Implement the Optional IoT 2.4 GHz Compatibility Network

**Files:**
- Create: `packages/athena-runtime/files/usr/bin/athena-iot`
- Create: `packages/athena-runtime/files/usr/lib/athena/iot.sh`
- Modify: `packages/athena-runtime/files/etc/config/athena`
- Modify: `packages/athena-runtime/files/usr/lib/athena/checks.sh`
- Test: `tests/runtime/test_iot.sh`

**Interfaces:**
- `athena-iot setup` interactively creates or updates one Athena-managed 2.4 GHz SSID after a verified backup.
- `athena-iot status` reports configuration and runtime state without revealing the SSID or passphrase.
- `athena-iot diagnose` emits redacted compatibility, association, DHCP, and service diagnostics.
- `athena-iot disable` disables only the managed IoT interface.
- `athena-iot remove` removes only the managed IoT interface after confirmation and backup.

- [ ] **Step 1: Write failing fake-UCI tests**

Tests create multiple fake `wifi-device` sections in different orders and verify runtime band discovery selects the 2.4 GHz PHY without relying on `radio0`. Assert setup rejects channels outside `1`, `6`, and `11`, weak passphrases, empty SSIDs, and missing 2.4 GHz radios.

Tests must also assert the generated interface uses WPA2-PSK/AES, 20 MHz, country `CN`, PMF off, 802.11r/k/v off, WMM on, broadcast SSID, client isolation off, and Wi-Fi 6/HE disabled by default. Repeated setup must update one managed section rather than duplicate it. Disable/remove must not change unrelated wireless sections.

- [ ] **Step 2: Run the runtime tests and confirm failure**

```bash
bash scripts/test_runtime_scripts.sh
```

Expected: the IoT tests FAIL because `athena-iot` and `iot.sh` do not exist.

- [ ] **Step 3: Implement radio discovery and validated UCI generation**

Discover the 2.4 GHz radio from UCI `band`, `hwmode`, or runtime `iw phy` capabilities, in that order, and fail safely when ambiguous. Store the managed section name in `/etc/config/athena`. Never store the passphrase in Athena logs or diagnostic output.

Create a verified Athena backup before every state change. Use UCI batch operations, validate the resulting section, commit `wireless`, and reload Wi-Fi only after validation. If reload fails, offer rollback using the created backup.

- [ ] **Step 4: Implement compatibility diagnostics**

Report redacted effective settings, selected radio, current channel and width, hostapd/netifd service state, associated-station count, DHCP lease count, and recent categorized failures. Do not print station MAC addresses, client hostnames, SSIDs, or keys.

- [ ] **Step 5: Integrate health and LuCI status**

Add an optional `iot_wifi` health group. It is `PASS` when disabled by design, `WARN` when enabled but no station has associated, and `FAIL` only for invalid configuration, missing radio, or failed interface/service state. Expose status and command guidance through the existing rpcd backend and LuCI status page; do not expose passphrases through rpcd.

- [ ] **Step 6: Run tests**

```bash
bash scripts/test_runtime_scripts.sh
python3 scripts/security_check.py --root .
```

Expected: PASS.

- [ ] **Step 7: Commit IoT compatibility support**

```bash
git add packages/athena-runtime/files/usr/bin/athena-iot packages/athena-runtime/files/usr/lib/athena/iot.sh packages/athena-runtime/files/etc/config/athena packages/athena-runtime/files/usr/lib/athena/checks.sh tests/runtime/test_iot.sh
git commit -m "feat: add optional iot wifi compatibility network"
```

---

### Task 7: Implement the `athena-setup` State Machine

**Files:**
- Create: `packages/athena-runtime/files/usr/bin/athena-setup`
- Test: `tests/runtime/test_setup.sh`

**Interfaces:**
- CLI supports `athena-setup`, `athena-setup --check`, and `athena-setup --resume`.
- State file format is newline-delimited `KEY=VALUE` with allowed keys `STATE`, `BACKUP_ID`, `PROFILE`, `GENERATED_SHA256`, `UPDATED_AT`; state transitions are `new -> checked -> backed_up -> generated -> awaiting_import -> validated -> complete`.
- Consumes `athena_backup_create`, `athena_render_templates`, and reusable health checks.

- [ ] **Step 1: Write failing setup-state tests**

Test scenarios:

1. `--check` leaves fixture files and UCI logs byte-identical.
2. Normal run creates exactly one verified backup before any change.
3. Interrupt after generation and `--resume` continues at `awaiting_import` without another backup.
4. Invalid proxy group, DNS IP, node hostname, node IP, or MAC is rejected before output files change.
5. Health critical failure after import prompts rollback; non-interactive fixture defaults to rollback unless `ATHENA_ASSUME_NO=1`.
6. Logs redact proxy URLs, UUIDs, and token strings.

- [ ] **Step 2: Run tests and confirm failure**

```bash
bash scripts/test_runtime_scripts.sh
```

Expected: setup tests FAIL.

- [ ] **Step 3: Implement preflight and state handling**

Preflight checks the exact design requirements. `--check` calls only read-only helpers. State writes are atomic. Acquire `athena_lock setup`; reject concurrent setup/rollback.

- [ ] **Step 4: Implement profile prompts and generation**

Default to `stable`. Ask only for proxy group, domestic resolvers, global DoH, node hostname/IPs, game-device MACs, gaming toggle, BT mode, and QUIC policy. Provide documented defaults. Do not request node URL or credentials.

After template generation, print and write exact import steps, then pause for the user to confirm DAED import/start. Do not touch `wing.db`.

- [ ] **Step 5: Implement validation and rollback branch**

After confirmation, enable/apply `athena-runtime`, run `athena-health --verbose`, mark `complete` only on no critical failures, and offer verified rollback on critical failure.

- [ ] **Step 6: Run setup tests**

```bash
bash scripts/test_runtime_scripts.sh
```

Expected: PASS for clean, resume, invalid-input, and failure/rollback cases.

- [ ] **Step 7: Commit setup workflow**

```bash
git add packages/athena-runtime/files/usr/bin/athena-setup tests/runtime/test_setup.sh
git commit -m "feat: add resumable safe athena setup"
```

---

### Task 8: Add rpcd Backend and Thin LuCI Application

**Files:**
- Create: `packages/athena-runtime/files/usr/libexec/rpcd/athena`
- Create: `packages/athena-runtime/files/usr/share/rpcd/acl.d/luci-app-athena.json`
- Create: `packages/luci-app-athena/Makefile`
- Create: `packages/luci-app-athena/root/usr/share/luci/menu.d/luci-app-athena.json`
- Create: `packages/luci-app-athena/htdocs/luci-static/resources/view/athena/status.js`
- Create: `packages/luci-app-athena/htdocs/luci-static/resources/view/athena/templates.js`
- Create: `packages/luci-app-athena/htdocs/luci-static/resources/view/athena/backups.js`
- Test: `tests/test_luci_app.py`

**Interfaces:**
- rpcd object `athena` methods: `status`, `health`, `templates`, `backups`, `runtime_apply`, and `rollback`.
- Read methods return JSON objects; mutating methods require explicit LuCI confirmation and ACL permission.
- LuCI JavaScript calls rpcd only; it does not shell out or duplicate policy logic.

- [ ] **Step 1: Write failing LuCI/rpcd structure tests**

Tests parse menu and ACL JSON, inspect JS imports/calls, and assert:

- menu under `admin/services/athena` with children Status, DAED Panel, Templates, Backups;
- ACL read/write separation;
- no JS `fs.exec()` or hard-coded `192.168.50.1:2023`;
- rollback method requires a backup ID and explicit confirmation;
- status page renders setup state, DAED state, ECM state, DNS error counts, and recovery URL.

- [ ] **Step 2: Run tests and confirm failure**

```bash
python3 -m unittest discover -s tests -p 'test_luci_app.py' -v
```

Expected: FAIL.

- [ ] **Step 3: Implement rpcd backend**

Use rpcd executable protocol and `jshn`. Validate method inputs and call existing commands with JSON output. Cap returned logs/data sizes. Never return `/etc/daed/wing.db`, node URLs, or raw DAED logs.

- [ ] **Step 4: Implement LuCI pages**

Use standard LuCI modules (`view`, `rpc`, `ui`, `dom`) and Argon-compatible semantic markup. Status auto-refreshes at a conservative interval. Templates page displays generated files read-only with copy buttons. Backups page lists IDs/checksum status and requires confirmation for rollback.

- [ ] **Step 5: Run LuCI tests**

```bash
python3 -m unittest discover -s tests -p 'test_luci_app.py' -v
python3 scripts/security_check.py --root .
```

Expected: PASS.

- [ ] **Step 6: Commit LuCI application**

```bash
git add packages/athena-runtime/files/usr/libexec/rpcd/athena packages/athena-runtime/files/usr/share/rpcd packages/luci-app-athena tests/test_luci_app.py
git commit -m "feat: add athena luci management app"
```

---

### Task 9: Implement Nginx DAED Proxy, Embedded Panel, Argon Defaults, and Recovery uhttpd

**Files:**
- Create: `packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.conf`
- Create: `packages/luci-app-athena/root/etc/uci-defaults/95-athena-web`
- Create: `packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js`
- Create: `scripts/verify_web_config.py`
- Test: `tests/test_web_config.py`

**Interfaces:**
- Normal path `/athena-daed/` proxies to `http://127.0.0.1:2023/`.
- Recovery LuCI listens on port `8080`, LAN addresses only.
- DAED panel view embeds `/athena-daed/` and displays local status/retry/recovery controls if unavailable.

- [ ] **Step 1: Write failing web architecture tests**

Tests assert:

- upstream target is loopback only;
- `proxy_http_version 1.1`, Upgrade/Connection headers, buffering disabled for streaming paths, and bounded connect/read/send timeouts exist;
- no `0.0.0.0:2023` or direct client URL exists;
- recovery listener is `8080`, firewall zone/input scope is LAN-only, and Bootstrap remains installed;
- Argon is selected as default without deleting theme-choice configuration;
- iframe sandbox/referrer policy permits the same-origin native DAED interface without broad cross-origin privileges.

- [ ] **Step 2: Run tests and confirm failure**

```bash
python3 -m unittest discover -s tests -p 'test_web_config.py' -v
```

Expected: FAIL.

- [ ] **Step 3: Implement Nginx proxy and first-boot defaults**

The uci-defaults script must be idempotent, bind DAED to `127.0.0.1:2023`, select Argon dark/auto-compatible defaults, preserve Bootstrap, configure recovery uhttpd, and reload services only after `nginx -t` succeeds. On Nginx validation failure, leave uhttpd recovery available and log the error.

- [ ] **Step 4: Implement DAED panel view**

Use an iframe pointed at `/athena-daed/` inside LuCI's content area. Probe rpcd status first. When DAED is stopped or proxy fails, render a status callout, reload control, runtime diagnostics link, and recovery URL instead of a blank panel.

- [ ] **Step 5: Run web tests**

```bash
python3 -m unittest discover -s tests -p 'test_web_config.py' -v
python3 scripts/verify_web_config.py --root .
```

Expected: PASS.

- [ ] **Step 6: Commit web architecture**

```bash
git add packages/luci-app-athena/root/etc packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js scripts/verify_web_config.py tests/test_web_config.py
git commit -m "feat: embed loopback daed panel with recovery ui"
```

---

### Task 10: Refactor Package Import and Safe First-Boot Injection

**Files:**
- Modify: `scripts/prepare_packages.sh`
- Modify: `scripts/inject_runtime.sh`
- Create: `scripts/verify_package_layout.py`
- Test: `tests/test_build_scripts.py`

**Interfaces:**
- `prepare_packages.sh OPENWRT_ROOT` imports all locked third-party sources and copies `packages/athena-runtime` plus `packages/luci-app-athena` into `package/custom/`.
- `inject_runtime.sh OPENWRT_ROOT` injects only safe network/web defaults, release metadata, and `/www/diag.html`; runtime commands come from packages.

- [ ] **Step 1: Write failing build-script tests**

Build a fake OpenWrt tree and assert:

- each third-party clone uses the exact SHA from `SOURCES.lock.json` and verifies `rev-parse HEAD`;
- local packages are copied to `package/custom`;
- no Git checkout uses a moving ref;
- injected LAN address is `192.168.50.1` everywhere;
- DAED and Athena LED are disabled by default;
- flow offload defaults are zero;
- injection does not generate `athena-setup`, health, backup, or rollback scripts;
- diagnostics reference normal port 80 and recovery port 8080.

- [ ] **Step 2: Run tests and confirm failure**

```bash
python3 -m unittest discover -s tests -p 'test_build_scripts.py' -v
```

Expected: FAIL against v18 scripts.

- [ ] **Step 3: Refactor `prepare_packages.sh`**

Read lock JSON using Python or `jq`; clone/fetch each exact commit; verify expected package paths; apply the existing DAED BTF patch only after checking its target signatures; copy local packages; fail with a precise package name when an upstream layout is incompatible.

- [ ] **Step 4: Narrow `inject_runtime.sh`**

Generate release metadata, safe first-boot UCI defaults, RAM recovery bridge behavior, DAED-off state, and diagnostic HTML. Remove runtime-command generation and retain no private environment values.

- [ ] **Step 5: Run tests and validators**

```bash
python3 -m unittest discover -s tests -p 'test_build_scripts.py' -v
python3 scripts/verify_package_layout.py --root .
find scripts -type f -name '*.sh' -print0 | xargs -0 -n1 bash -n
```

Expected: PASS.

- [ ] **Step 6: Commit build-script refactor**

```bash
git add scripts/prepare_packages.sh scripts/inject_runtime.sh scripts/verify_package_layout.py tests/test_build_scripts.py
git commit -m "refactor: import v19 packages and safe boot defaults"
```

---

### Task 11: Replace v18 Build Configuration and Strengthen Effective-Config Validation

**Files:**
- Create: `config/athena-v19.config`
- Modify: `scripts/verify_config.sh`
- Delete: `config/athena-final-candidate.config`
- Test: `tests/test_config_validation.py`

**Interfaces:**
- `verify_config.sh CONFIG DAED_MAKEFILE` returns exit 0 only for the approved v19 package/features set.

- [ ] **Step 1: Write failing config tests**

Fixture configs cover missing Argon, missing local package, enabled SmartDNS, enabled alternate proxy suite, conflicting QCN9074 firmware, disabled initramfs, wrong target, and valid v19 configuration. Assert exact failure labels.

- [ ] **Step 2: Run tests and confirm failure**

```bash
python3 -m unittest discover -s tests -p 'test_config_validation.py' -v
```

Expected: FAIL because v19 config is absent.

- [ ] **Step 3: Build v19 seed configuration**

Start from the existing v18 config and add `athena-runtime`, `luci-app-athena`, `luci-theme-argon`, `luci-app-argon-config`, Nginx/LuCI Nginx support, recovery uhttpd, and required rpcd/JSON utilities. Keep DAED, detached BTF, Athena LED, WOL, NSS, and the single approved QCN9074 firmware. Explicitly disable SmartDNS and alternate proxy suites.

- [ ] **Step 4: Expand validation**

Validate target/profile, kernel/initramfs/squashfs, local packages, DAED/BTF, Argon/Nginx/uhttpd, NSS/QCN9074, WOL/display, excluded suites, and DAED package's BTF dependency behavior.

- [ ] **Step 5: Run tests**

```bash
python3 -m unittest discover -s tests -p 'test_config_validation.py' -v
bash scripts/verify_config.sh config/athena-v19.config /dev/null
```

For the direct seed-file invocation, allow a `--seed` mode or provide a test fixture DAED Makefile; do not weaken effective `.config` validation used in CI.

- [ ] **Step 6: Commit v19 configuration**

```bash
git add config/athena-v19.config scripts/verify_config.sh tests/test_config_validation.py
git rm config/athena-final-candidate.config
git commit -m "build: select athena v19 firmware packages"
```

---

### Task 12: Replace GitHub Actions Workflow and Add Post-Build Inspection

**Files:**
- Create: `.github/workflows/build-athena-v19.yml`
- Create: `scripts/inspect_firmware.py`
- Delete: `.github/workflows/build-athena-final-candidate.yml`
- Test: `tests/test_workflow.py`

**Interfaces:**
- Workflow inputs: `compile_jobs` (`1` or `2`), `build_profile` (`stable` or `performance`), and `release_stage` (`test` or `candidate`).
- `scripts/inspect_firmware.py --openwrt PATH --output PATH --kernel-limit 6291456` emits JSON/text inspection reports and fails on missing images, oversized kernel, or required/forbidden package mismatch.

- [ ] **Step 1: Write failing workflow tests**

Parse YAML as text/JSON-safe structure and assert source data comes from `SOURCES.lock.json`, cache key says v19, validators run before clone/build, both images are required, kernel warning threshold is 131072 bytes, local package files are checked inside rootfs/package manifests, workflow never publishes a Release automatically, and artifact name includes v19/run number.

- [ ] **Step 2: Run tests and confirm failure**

```bash
python3 -m unittest discover -s tests -p 'test_workflow.py' -v
```

Expected: FAIL against v18 workflow.

- [ ] **Step 3: Implement v19 workflow**

Retain Ubuntu 22.04, disk cleanup, dependencies, swap, exact source checkout, feed setup, serial retry, error context, and artifact upload. Add project/security/template/package/web tests before compilation; use exact lock values; apply `config/athena-v19.config`; inspect outputs; always upload diagnostics; fail the job after artifact upload if compile or inspection failed.

- [ ] **Step 4: Implement firmware inspection**

Locate initramfs and sysupgrade, canonicalize names, inspect package manifest and extracted rootfs where available, verify required files/commands, calculate kernel margin, and create `diagnostics/kernel-size.txt` plus `diagnostics/firmware-inspection.json`.

- [ ] **Step 5: Run tests and local workflow validation**

```bash
python3 -m unittest discover -s tests -p 'test_workflow.py' -v
python3 scripts/verify_project.py --root .
```

Expected: PASS.

- [ ] **Step 6: Commit workflow**

```bash
git add .github/workflows/build-athena-v19.yml scripts/inspect_firmware.py tests/test_workflow.py
git rm .github/workflows/build-athena-final-candidate.yml
git commit -m "ci: build and inspect athena v19 firmware"
```

---

### Task 13: Rebuild Artifact Collection and Post-Flash Verification

**Files:**
- Modify: `scripts/collect_output.sh`
- Modify: `scripts/verify_after_flash.sh`
- Create: `scripts/verify_checksums.sh`
- Test: `tests/test_artifact_layout.py`

**Interfaces:**
- `collect_output.sh OPENWRT_ROOT OUTPUT_ROOT` produces the exact artifact layout from the design.
- `verify_after_flash.sh` is router-safe and produces PASS/WARN/FAIL with no state changes.
- `verify_checksums.sh ARTIFACT_ROOT` verifies all distributed checksums.

- [ ] **Step 1: Write failing artifact-layout tests**

Create fake firmware and metadata inputs, run collector, and assert canonical names and folders:

```text
firmware/
metadata/
diagnostics/
tools/
docs/
SHA256SUMS.txt
```

Assert checksum verification fails after one byte changes.

- [ ] **Step 2: Run tests and confirm failure**

```bash
python3 -m unittest discover -s tests -p 'test_artifact_layout.py' -v
```

Expected: FAIL against v18 collector.

- [ ] **Step 3: Implement canonical artifact assembly**

Copy both images, profiles, package manifest, effective config, diffconfig, lock/project metadata, package commits, diagnostics, user docs, and tools. Generate nested firmware checksums and top-level checksums after all copying. Do not include build caches or private logs.

- [ ] **Step 4: Expand post-flash verifier**

Check LAN/WAN, LuCI/Argon, recovery port, DAED default-off state on fresh boot, DAED loopback listener after setup, v19 commands, BTF, NSS/Wi-Fi, ECM/flow policy, DNS/IPv6, backups, and health output. Never modify the router.

- [ ] **Step 5: Run artifact tests**

```bash
python3 -m unittest discover -s tests -p 'test_artifact_layout.py' -v
```

Expected: PASS.

- [ ] **Step 6: Commit artifact tooling**

```bash
git add scripts/collect_output.sh scripts/verify_after_flash.sh scripts/verify_checksums.sh tests/test_artifact_layout.py
git commit -m "build: package v19 firmware and verification tools"
```

---

### Task 14: Write v19 User, Recovery, Architecture, and Release Documentation

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `AUDIT.md`
- Modify: `docs/BUILD.md`
- Modify: `docs/FLASH.md`
- Create: `docs/SETUP.md`
- Create: `docs/DAED_CONFIG.md`
- Create: `docs/GAMING.md`
- Create: `docs/IOT_WIFI.md`
- Create: `docs/RECOVERY.md`
- Create: `docs/ARCHITECTURE.md`
- Create: `THIRD_PARTY_NOTICES.md`
- Create: `CHANGE_SUMMARY.md`
- Test: `tests/test_docs.py`

**Interfaces:**
- Documentation commands and URLs must match implemented commands and ports exactly.

- [ ] **Step 1: Write failing documentation-consistency tests**

Tests assert all docs use `192.168.50.1`, recovery `:8080`, v19 filenames, `sysupgrade -n` for v18 migration, `athena-setup` after node import, no direct port-2023 LAN instructions, no claim that SmartDNS is present, and explicit initramfs-first warning.

- [ ] **Step 2: Run tests and confirm failure**

```bash
python3 -m unittest discover -s tests -p 'test_docs.py' -v
```

Expected: FAIL against v18 docs.

- [ ] **Step 3: Rewrite top-level documentation**

README provides project purpose, safety warning, build steps, artifact explanation, initramfs test, persistent flash, first setup, normal/recovery URLs, command index, privacy model, and support boundary. CHANGELOG records `v19.0.0-rc1`. AUDIT describes source lock and CI checks.

- [ ] **Step 4: Write focused guides**

Document exact build, flash, setup/import, DNS and routing design, game/Steam/Xbox/BT behavior, optional IoT Wi-Fi setup and diagnostics, recovery/rollback, and architecture. Clearly separate direct domestic UDP DNS from proxied global DoH and explain why DAED is not automatically private without correct DNS policy.

- [ ] **Step 5: Record third-party notices and upload summary**

List repositories/commits/licenses from `SOURCES.lock.json`; do not bundle third-party source. `CHANGE_SUMMARY.md` lists added/removed/changed files, upload steps, Actions steps, artifact validation, and GitHub Release naming.

- [ ] **Step 6: Run documentation and security checks**

```bash
python3 -m unittest discover -s tests -p 'test_docs.py' -v
python3 scripts/security_check.py --root .
```

Expected: PASS.

- [ ] **Step 7: Commit documentation**

```bash
git add README.md CHANGELOG.md AUDIT.md docs THIRD_PARTY_NOTICES.md CHANGE_SUMMARY.md
git commit -m "docs: publish athena v19 build and recovery guides"
```

---

### Task 15: Run Full Verification and Produce the Source ZIP

**Files:**
- Modify as required by verification failures: only files already listed in Tasks 1–14
- Create outside repository: `jdy2-v19.0.0-rc1.zip`
- Create outside repository: `jdy2-v19.0.0-rc1.zip.sha256`

**Interfaces:**
- The source ZIP contains the repository files only; it excludes `.git`, firmware binaries, caches, test temporary directories, private configuration, and prior review ZIPs.

- [ ] **Step 1: Run all host-side tests**

```bash
set -euo pipefail
find scripts -type f -name '*.sh' -print0 | xargs -0 -n1 bash -n
python3 -m unittest discover -s tests -p 'test_*.py' -v
bash scripts/test_runtime_scripts.sh
python3 scripts/verify_project.py --root .
python3 scripts/verify_templates.py --templates packages/athena-runtime/files/usr/share/athena/templates --rules packages/athena-runtime/files/usr/share/athena/rules
python3 scripts/verify_package_layout.py --root .
python3 scripts/verify_web_config.py --root .
python3 scripts/security_check.py --root .
```

Expected: every command exits 0.

- [ ] **Step 2: Verify spec coverage**

Map each design section 1–22 to one or more implemented files/tests. Confirm all success criteria have either a host-side test or an explicitly documented real-device acceptance step. Correct any missing coverage before packaging.

- [ ] **Step 3: Inspect the final Git diff**

```bash
git status --short
git diff --check
git log --oneline --decorate -15
```

Expected: no uncommitted changes, no whitespace errors, and focused commits matching Tasks 1–14.

- [ ] **Step 4: Create reproducible source ZIP**

From the repository parent directory:

```bash
find jdy2 -type f -print0 | LC_ALL=C sort -z | \
  zip -X -@ jdy2-v19.0.0-rc1.zip
sha256sum jdy2-v19.0.0-rc1.zip > jdy2-v19.0.0-rc1.zip.sha256
```

When the local directory name is not `jdy2`, copy it to a clean staging directory named `jdy2` first. Ensure the ZIP root is `jdy2/`, not a flat file list.

- [ ] **Step 5: Verify the packaged ZIP**

```bash
rm -rf /tmp/jdy2-v19-verify
mkdir -p /tmp/jdy2-v19-verify
unzip -q jdy2-v19.0.0-rc1.zip -d /tmp/jdy2-v19-verify
cd /tmp/jdy2-v19-verify/jdy2
python3 scripts/verify_project.py --root .
python3 scripts/security_check.py --root .
```

Expected: both validators PASS from the extracted archive.

- [ ] **Step 6: Create final source release commit/tag only after user review**

```bash
git tag -a v19.0.0-rc1 -m "Athena AX6600 DAED v19.0.0-rc1"
```

Do not push the tag or source; the user uploads/pushes the repository.

---

## Real-Device Acceptance Checklist After GitHub Actions Build

The following cannot be proven by host-side tests and must be executed on the JDCloud RE-CS-02 before a stable `v19.0.0` release:

- [ ] Boot the v19 initramfs image from U-Boot `/uimage.html`.
- [ ] Confirm LAN, DHCP, WAN DHCP, DNS, SSH, `http://192.168.50.1/`, and `http://192.168.50.1:8080/`.
- [ ] Confirm Argon default and Bootstrap recovery fallback.
- [ ] Confirm DAED is stopped on clean first boot and port 2023 is not LAN-reachable.
- [ ] Confirm NSS, ath11k, QCN9074, all radios, Ethernet, WOL, BTF, and display package availability.
- [ ] Run `athena-iot setup`, connect at least one previously affected 2.4 GHz IoT device, and confirm association, DHCP, DNS, LAN discovery, Internet access, and reconnect after router/device reboot.
- [ ] Confirm `athena-iot disable` and `athena-iot remove` do not alter unrelated SSIDs, then recreate the IoT network for continued testing.
- [ ] Import generated DAED templates, start DAED, and confirm `/athena-daed/` renders the complete native UI.
- [ ] Run `athena-health --verbose`; require no critical FAIL.
- [ ] Confirm domestic DNS is direct UDP, global DNS is proxied DoH, and bootstrap errors do not increase.
- [ ] Confirm Chinese IPv4/IPv6 is direct and non-Chinese IPv4/IPv6 is proxied by default.
- [ ] Confirm Steam store/login proxy, download direct, Minecraft/game UDP direct for selected device, Xbox behavior, and BT DSCP direct.
- [ ] Confirm ECM frontend flags remain 1, flow offload remains 0, and NSS/Wi-Fi acceleration remains loaded after reboot.
- [ ] Create a backup, change a safe setting, roll back, and confirm service/network recovery.
- [ ] Leave initramfs under ordinary and high-load use long enough to detect Wi-Fi “no internet” recurrence.
- [ ] Only then flash the matching sysupgrade image with `sysupgrade -n`.
- [ ] Repeat boot-persistence, web/recovery, DAED, health, DNS, IPv6, backup, and rollback checks on persistent storage.

## Plan Self-Review

- Spec coverage: Tasks 1–15 cover metadata/release model, safe boot, web/theme, runtime packages, setup, backups, templates, DNS/routing, gaming/BT, ECM/NSS/CPU, health, rollback, build pipeline, CI, artifact layout, flashing, documentation, and final packaging.
- Placeholder scan: no implementation requirement is deferred with a placeholder marker, an unfinished-note marker, or an unspecified test request.
- Interface consistency: runtime commands share `ATHENA_ROOT`, setup consumes the named backup/template/check interfaces, rpcd calls the public CLI interfaces, and CI validators use the paths defined in the file map.
- Scope: although v19 spans firmware build, runtime, and LuCI, each task produces an independently reviewable deliverable and the final device acceptance remains explicitly separate from host-side claims.
