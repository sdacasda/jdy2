# Athena v19 initramfs Web and DAED Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the clean Athena v19 initramfs boot expose a reliable Nginx/LuCI management UI, an independent uHTTPd recovery endpoint, and a loopback-only DAED UI through a same-origin reverse proxy.

**Architecture:** Nginx is the sole owner of LAN ports 80/443 and serves LuCI plus `/athena-daed/`; uHTTPd owns only `192.168.50.1:8080` for recovery. DAED remains disabled by default and listens only on `127.0.0.1:2023`; its locked frontend source is patched before compilation so GraphQL uses `/athena-daed/graphql` instead of browser-visible port 2023.

**Tech Stack:** OpenWrt UCI/procd, Nginx `luci-nginx`/uWSGI, uHTTPd Lua LuCI handler, LuCI JavaScript/RPCD, POSIX shell, Python 3 `unittest`, GitHub Actions, DAED React/TypeScript frontend embedded in Go.

## Global Constraints

- LAN remains exactly `192.168.50.1/24`.
- DAED remains disabled by default and must listen exactly on `127.0.0.1:2023` when enabled.
- Nginx exclusively owns LAN ports 80 and 443; uHTTPd exclusively owns `192.168.50.1:8080`.
- DAED browser traffic must use same-origin `/athena-daed/` and `/athena-daed/graphql`; port 2023 must not be exposed to LAN or WAN.
- Argon remains the default configurable dark-capable theme; Bootstrap remains installed for recovery.
- SmartDNS, OpenClash, PassWall, and HomeProxy remain excluded.
- NSS and Wi-Fi offload remain present; ECM frontends and OpenWrt flow offload remain stopped.
- DAED failure, including eBPF verifier failure, must not prevent LuCI or the recovery endpoint from working.
- Both initramfs and sysupgrade images remain mandatory; initramfs must be tested before any persistent flash.
- All third-party sources remain locked by immutable commit or package hash.
- Never edit `wing.db`, embed private nodes, expose credentials, or push to GitHub.

## File Structure and Responsibilities

### Files created

- `packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.locations`: server-context proxy locations for DAED HTML/assets and GraphQL.
- `scripts/patch_daed_web.py`: exact, fail-closed patch of the locked DAED frontend endpoint source.
- `scripts/patch_daed_package.py`: injects the source patch invocation into the imported DAED OpenWrt package `Build/Prepare` block.
- `tests/test_daed_web_patch.py`: unit fixtures for the DAED source and package Makefile patchers.
- `packages/luci-app-athena/root/www/athena-recovery.html`: dependency-light recovery landing page served by uHTTPd on port 8080.
- `docs/WEB_RECOVERY.md`: operator guide for the two Web entry points and DAED failure states.

### Files modified

- `packages/luci-app-athena/Makefile`: add the uHTTPd Lua runtime dependency required by the recovery endpoint.
- `packages/luci-app-athena/root/etc/uci-defaults/95-athena-web`: establish one owner per port and preserve safe DAED defaults.
- `packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js`: render enabled/running/API tri-state before creating the iframe.
- `packages/athena-runtime/files/usr/libexec/rpcd/athena`: expose DAED tri-state and categorized startup failure.
- `packages/athena-runtime/files/usr/lib/athena/checks.sh`: add Web listener, Nginx, recovery uHTTPd, and DAED API health checks.
- `config/athena-v19.config`: explicitly include `uhttpd-mod-lua` and retain the existing Nginx/LuCI stack.
- `scripts/prepare_packages.sh`: stage and apply both DAED package patches.
- `scripts/verify_web_config.py`: structurally validate file context, endpoint ownership, UTF-8 JSON, UCI defaults, and frontend path use.
- `scripts/inspect_firmware.py`: inspect rootfs files, manifest dependencies, and embedded DAED endpoint strings.
- `scripts/verify_after_flash.sh`: perform runtime Web/port/API checks on initramfs hardware.
- `.github/workflows/build-athena-v19.yml`: run the new tests and preserve Web inspection diagnostics.
- `tests/test_web_config.py`, `tests/test_luci_app.py`, `tests/test_build_scripts.py`, `tests/test_firmware_inspection.py`, `tests/runtime/test_health.sh`: regression coverage.
- `README.md`, `CHANGELOG.md`, `docs/SETUP.md`, `docs/RECOVERY.md`, `docs/BUILD.md`: deployment, recovery, and validation instructions.

---

### Task 1: Capture the Web ownership defects (red phase of Task 2)

**Files:**
- Modify: `tests/test_web_config.py`
- Modify: `tests/test_luci_app.py`
- Modify: `scripts/verify_web_config.py`

**Interfaces:**
- Consumes: project root passed as `--root PATH`.
- Produces: `verify_web_config.py` exit code 0 only when the Nginx include context, port ownership, UCI defaults, menu JSON, and LuCI panel path are valid.

- [ ] **Step 1: Add failing layout and port-ownership tests**

Add these assertions to `tests/test_web_config.py`:

```python
    def test_daed_proxy_uses_server_context_include(self):
        conf_dir = ROOT / "packages/luci-app-athena/root/etc/nginx/conf.d"
        self.assertFalse((conf_dir / "athena-daed.conf").exists())
        locations = (conf_dir / "athena-daed.locations").read_text(encoding="utf-8")
        self.assertIn("location /athena-daed/", locations)
        self.assertIn("location = /athena-daed/graphql", locations)

    def test_firstboot_assigns_each_web_port_once(self):
        defaults = (ROOT / "packages/luci-app-athena/root/etc/uci-defaults/95-athena-web").read_text(encoding="utf-8")
        for option in ("uhttpd.main.listen_http", "uhttpd.main.listen_https"):
            self.assertIn(f"delete {option}", defaults)
        self.assertEqual(defaults.count("192.168.50.1:8080"), 1)
        self.assertIn("/usr/lib/lua/luci/sgi/uhttpd.lua", defaults)
```

Extend `tests/test_luci_app.py` so it parses both LuCI menu JSON files and asserts that `daed-panel.js` contains `/athena-daed/` but not `:2023`.

- [ ] **Step 2: Run the focused tests and verify the current project fails**

Run:

```text
python -m unittest tests.test_web_config tests.test_luci_app -v
```

Expected: FAIL because `athena-daed.conf` exists, `athena-daed.locations` is absent, and the default uHTTPd listeners are not deleted.

- [ ] **Step 3: Replace keyword-only validation with structural checks**

Refactor `scripts/verify_web_config.py` to define:

```python
def read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="strict")

def require_exact_count(text: str, token: str, count: int, message: str) -> None:
    require(text.count(token) == count, message)
```

The validator must:

```python
conf_dir = root / "packages/luci-app-athena/root/etc/nginx/conf.d"
require(not (conf_dir / "athena-daed.conf").exists(), "bare location must not be loaded in http context")
locations = read_utf8(conf_dir / "athena-daed.locations")
require("location /athena-daed/" in locations, "DAED UI proxy is missing")
require("location = /athena-daed/graphql" in locations, "DAED GraphQL proxy is missing")
require("proxy_pass http://127.0.0.1:2023/" in locations, "DAED UI upstream is wrong")
require("proxy_pass http://127.0.0.1:2023/graphql" in locations, "DAED GraphQL upstream is wrong")
require("proxy_http_version 1.1" in locations, "DAED proxy must use HTTP/1.1")
require("proxy_buffering off" in locations, "DAED proxy buffering must be disabled")
```

Parse both menu JSON files with `json.loads()`. Check that firstboot deletes the four default uHTTPd listener lists, creates exactly one recovery HTTP listener, adds the LuCI Lua prefix, sets DAED loopback-only, and disables DAED.

- [ ] **Step 4: Run the validator tests**

Run the same focused command. Expected: the validator-specific tests pass, while layout tests remain red until Task 2 installs the new configuration.

- [ ] **Step 5: Continue directly to Task 2 without committing a red tree**

Tasks 1 and 2 are one reviewer gate: Task 1 proves the old layout fails, and Task 2 returns the entire focused suite to green before the combined commit.

---

### Task 2: Give Nginx and uHTTPd exclusive, working entry points (green phase)

**Files:**
- Delete: `packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.conf`
- Create: `packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.locations`
- Create: `packages/luci-app-athena/root/www/athena-recovery.html`
- Modify: `packages/luci-app-athena/root/etc/uci-defaults/95-athena-web`
- Modify: `packages/luci-app-athena/Makefile`
- Modify: `config/athena-v19.config`

**Interfaces:**
- Consumes: OpenWrt Nginx convention that `*.locations` is included inside the LuCI `server {}` block.
- Produces: Nginx on 80/443, recovery uHTTPd on `192.168.50.1:8080`, DAED upstream on loopback only.

- [ ] **Step 1: Install server-context DAED locations**

Replace the old file with `athena-daed.locations` containing:

```nginx
location = /athena-daed/graphql {
    proxy_pass http://127.0.0.1:2023/graphql;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_buffering off;
    proxy_connect_timeout 3s;
    proxy_read_timeout 3600s;
    proxy_send_timeout 30s;
}

location /athena-daed/ {
    proxy_pass http://127.0.0.1:2023/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_buffering off;
    proxy_connect_timeout 3s;
    proxy_read_timeout 3600s;
    proxy_send_timeout 30s;
}
```

- [ ] **Step 2: Make firstboot UCI idempotently remove the default uHTTPd listeners**

In `95-athena-web`, use one UCI batch with these exact operations before recreating recovery:

```uci
delete uhttpd.main.listen_http
delete uhttpd.main.listen_https
delete uhttpd.recovery
set uhttpd.recovery='uhttpd'
add_list uhttpd.recovery.listen_http='192.168.50.1:8080'
set uhttpd.recovery.home='/www'
add_list uhttpd.recovery.index_page='athena-recovery.html'
add_list uhttpd.recovery.lua_prefix='/cgi-bin/luci=/usr/lib/lua/luci/sgi/uhttpd.lua'
set uhttpd.recovery.ubus_prefix='/ubus'
set uhttpd.recovery.rfc1918_filter='1'
```

Also retain:

```uci
set daed.config.listen_addr='127.0.0.1:2023'
set daed.config.enabled='0'
set luci.main.mediaurlbase='/luci-static/argon'
```

Validate Nginx before reloading it. Enable uHTTPd only after the recovery instance has been committed.

- [ ] **Step 3: Add a dependency-light recovery landing page**

Create `/www/athena-recovery.html` with UTF-8 HTML that states the LAN address, links to `/cgi-bin/luci/`, and shows these recovery commands without loading Argon JavaScript:

```text
/etc/init.d/daed stop
/etc/init.d/nginx restart
athena-health --verbose
athena-rollback --component web
```

Do not include credentials, remote assets, inline network requests, or JavaScript.

- [ ] **Step 4: Include the LuCI handler for uHTTPd**

Add `+uhttpd-mod-lua` to `LUCI_DEPENDS` and add:

```text
CONFIG_PACKAGE_uhttpd-mod-lua=y
```

to `config/athena-v19.config`. Keep `luci-theme-bootstrap`, `luci-theme-argon`, `luci-nginx`, and `nginx-ssl` selected.

- [ ] **Step 5: Run focused tests and package checks**

Run:

```text
python -m unittest tests.test_web_config tests.test_luci_app tests.test_config_validation -v
python scripts/verify_web_config.py --root .
```

Expected: PASS.

- [ ] **Step 6: Commit the Web ownership fix**

```text
git add scripts/verify_web_config.py tests/test_web_config.py tests/test_luci_app.py packages/luci-app-athena config/athena-v19.config
git commit -m "fix: separate primary and recovery web listeners"
```

---

### Task 3: Patch the locked DAED frontend to use the same-origin GraphQL path

**Files:**
- Create: `scripts/patch_daed_web.py`
- Create: `scripts/patch_daed_package.py`
- Create: `tests/test_daed_web_patch.py`
- Modify: `scripts/prepare_packages.sh`
- Modify: `tests/test_build_scripts.py`

**Interfaces:**
- Consumes: extracted DAED source root containing `apps/web/src/constants/default.ts`; imported OpenWrt DAED Makefile containing one `define Build/Prepare` block.
- Produces: exact source line `export const DEFAULT_ENDPOINT_URL = `${location.origin}/athena-daed/graphql`` and a package `Build/Prepare` hook that runs the patch after source extraction.

- [ ] **Step 1: Write exact fixture tests for source patching**

`tests/test_daed_web_patch.py` must import `scripts.patch_daed_web.patch_source` and assert:

```python
OLD = "export const DEFAULT_ENDPOINT_URL = `${location.protocol}//${location.hostname}:2023/graphql`"
NEW = "export const DEFAULT_ENDPOINT_URL = `${location.origin}/athena-daed/graphql`"
```

Test cases:

- exactly one old line becomes exactly one new line;
- a second run is idempotent;
- zero old and zero new lines raises `RuntimeError`;
- more than one old or new line raises `RuntimeError`;
- an unexpected source path raises `RuntimeError`.

Add a Makefile fixture test asserting the injected line is exactly:

```make
	python3 $(CURDIR)/files/patch_daed_web.py $(DAED_BUILD_DIR)
```

and appears once inside `define Build/Prepare` before `endef`.

- [ ] **Step 2: Run the new tests and verify imports fail**

Run:

```text
python -m unittest tests.test_daed_web_patch -v
```

Expected: FAIL because both patch modules are absent.

- [ ] **Step 3: Implement the fail-closed source patch**

`scripts/patch_daed_web.py` must expose:

```python
SOURCE = Path("apps/web/src/constants/default.ts")
OLD = "export const DEFAULT_ENDPOINT_URL = `${location.protocol}//${location.hostname}:2023/graphql`"
NEW = "export const DEFAULT_ENDPOINT_URL = `${location.origin}/athena-daed/graphql`"

def patch_source(root: Path) -> None:
    path = root / SOURCE
    text = path.read_text(encoding="utf-8")
    old_count = text.count(OLD)
    new_count = text.count(NEW)
    if (old_count, new_count) == (1, 0):
        path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8", newline="\n")
        return
    if (old_count, new_count) == (0, 1):
        return
    raise RuntimeError(f"unexpected DAED endpoint source: old={old_count} new={new_count}")
```

The CLI must return 2 for a missing argument or file and 1 for a layout mismatch.

- [ ] **Step 4: Implement the package Makefile hook patch**

`scripts/patch_daed_package.py` must locate exactly one `define Build/Prepare ... endef` block, insert the hook before `endef`, and be idempotent only when the hook already occurs exactly once. It must fail when the block count or hook count is unexpected.

- [ ] **Step 5: Stage the patcher into the imported package**

After copying `daed` in `scripts/prepare_packages.sh`, replace the current single BTF patch command with:

```bash
install -m 0644 "$PROJECT_ROOT/scripts/patch_daed_web.py" \
    "$CUSTOM/daed/files/patch_daed_web.py"
python3 "$PROJECT_ROOT/scripts/patch_daed_btf.py" "$CUSTOM/daed/Makefile"
python3 "$PROJECT_ROOT/scripts/patch_daed_package.py" "$CUSTOM/daed/Makefile"
```

Each package Makefile patch must execute exactly once.

- [ ] **Step 6: Run all patch and build-script tests**

Run:

```text
python -m unittest tests.test_daed_web_patch tests.test_build_scripts -v
```

Expected: PASS, including failure on an upstream layout mismatch.

- [ ] **Step 7: Commit the immutable frontend patch**

```text
git add scripts/patch_daed_web.py scripts/patch_daed_package.py scripts/prepare_packages.sh tests/test_daed_web_patch.py tests/test_build_scripts.py
git commit -m "fix: route daed frontend through same-origin graphql"
```

---

### Task 4: Report DAED enabled, running, and API status separately

**Files:**
- Modify: `packages/athena-runtime/files/usr/libexec/rpcd/athena`
- Modify: `packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js`
- Modify: `packages/athena-runtime/files/usr/share/rpcd/acl.d/luci-app-athena.json`
- Modify: `tests/test_luci_app.py`
- Create: `tests/runtime/test_rpcd_status.sh`

**Interfaces:**
- Consumes: `/etc/init.d/daed enabled`, `pidof daed`, loopback HTTP probe of `127.0.0.1:2023/graphql`, and sanitized DAED log classification.
- Produces RPC method `status` with booleans `daed_enabled`, `daed_running`, `daed_api_reachable`, string `daed_error_class`, and string `recovery_url`; write methods `daed_start` and `daed_stop` return the same status object after the action.

- [ ] **Step 1: Write the RPC and panel contract tests**

The shell fixture must set command overrides through environment variables:

```text
ATHENA_DAED_ENABLED=1
ATHENA_DAED_RUNNING=0
ATHENA_DAED_API_REACHABLE=0
ATHENA_DAED_ERROR_CLASS=ebpf
```

and assert JSON contains:

```json
{"daed_enabled":true,"daed_running":false,"daed_api_reachable":false,"daed_error_class":"ebpf"}
```

Make the RPCD script source the JSON helper through:

```sh
. "${ATHENA_JSHN:-/usr/share/libubox/jshn.sh}"
```

and provide a minimal test helper implementing the `json_*` calls in the fixture directory, so the host test never depends on an OpenWrt `/usr/share` tree.

The Python LuCI test must assert `daed-panel.js` references all three boolean fields, declares `daed_start` and `daed_stop`, uses only `/athena-daed/`, and contains no `:2023` or direct external URL. ACL tests must require `daed_start` and `daed_stop` in write methods and exclude them from read methods.

- [ ] **Step 2: Run tests to observe missing tri-state fields**

Run:

```text
bash tests/runtime/test_rpcd_status.sh
python -m unittest tests.test_luci_app -v
```

Expected: FAIL because current RPC only returns `daed_running`.

- [ ] **Step 3: Implement sanitized RPC status helpers**

Add shell helpers in the RPCD script that prefer the test environment variables and otherwise execute the real checks. Classify the latest DAED error only as one of:

```text
none
ebpf
configuration
memory
unavailable
```

Match `load eBPF objects|verifier|invalid argument` as `ebpf`, configuration parse/load messages as `configuration`, and allocation/OOM messages as `memory`. Do not return the original log line.

- [ ] **Step 4: Render the tri-state LuCI panel**

Before rendering the iframe, show three status chips:

```text
开机启用
进程运行
API 可达
```

Only render the iframe when `daed_running && daed_api_reachable`. Otherwise render a warning card with the categorized error, recovery URL, `athena-health --verbose`, a `启动 DAED` or `重新启动` button, and a `重新检测` button. When running, expose a confirmation-gated `停止 DAED` action. Keep the iframe sandbox and same-origin source.

Implement RPC actions with `/etc/init.d/daed start` and `/etc/init.d/daed stop`; after a start, wait at most five seconds for the process/API state and return the status object. A failed start must return `daed_running=false` with the categorized error rather than an unconditional `{ok:true}`.

- [ ] **Step 5: Run RPC, LuCI, and ACL tests**

Run:

```text
bash tests/runtime/test_rpcd_status.sh
python -m unittest tests.test_luci_app tests.test_web_config -v
```

Expected: PASS.

- [ ] **Step 6: Commit DAED status semantics**

```text
git add packages/athena-runtime/files/usr/libexec/rpcd/athena packages/athena-runtime/files/usr/share/rpcd/acl.d/luci-app-athena.json packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js tests/test_luci_app.py tests/runtime/test_rpcd_status.sh
git commit -m "fix: distinguish daed enable run and api state"
```

---

### Task 5: Add Web and DAED API health checks without breaking safe defaults

**Files:**
- Modify: `packages/athena-runtime/files/usr/lib/athena/checks.sh`
- Modify: `tests/runtime/test_health.sh`
- Modify: `scripts/test_runtime_scripts.sh`

**Interfaces:**
- Consumes: process/listener/API probe helpers and `ATHENA_ROOT` fixtures.
- Produces health record IDs `nginx`, `web_ports`, `recovery_web`, `daed_enabled`, `daed_process`, and `daed_api`.

- [ ] **Step 1: Extend the health fixture with explicit states**

Set these in `tests/runtime/test_health.sh`:

```text
ATHENA_NGINX_OK=1
ATHENA_WEB_PORTS_OK=1
ATHENA_RECOVERY_WEB_OK=1
ATHENA_DAED_ENABLED=0
ATHENA_DAED_RUNNING=0
ATHENA_DAED_API_REACHABLE=0
```

Assert safe-default output marks DAED enabled/process/API as `WARN`, not critical `FAIL`, while all Web checks are `PASS`. Add a second invocation with setup state complete and DAED enabled but API unreachable; assert exit code 2 and `daed_api` is critical `FAIL`.

- [ ] **Step 2: Run the runtime test and verify missing records**

Run:

```text
bash tests/runtime/test_health.sh
```

Expected: FAIL because the new IDs do not exist.

- [ ] **Step 3: Implement Web and tri-state health checks**

Use environment overrides for fixtures; on the router:

- Nginx: `nginx -t` plus running process;
- Web ports: inspect `/proc/net/tcp`, `/proc/net/tcp6`, and process ownership when `ss` is available;
- recovery: local HTTP request to `192.168.50.1:8080/athena-recovery.html`;
- DAED API: loopback HTTP POST/GET probe with a short timeout, treating any valid HTTP response as reachable.

Do not make DAED safe-default shutdown a critical failure before setup completes.

- [ ] **Step 4: Run every runtime test**

Run:

```text
bash scripts/test_runtime_scripts.sh
```

Expected: all runtime tests PASS.

- [ ] **Step 5: Commit health checks**

```text
git add packages/athena-runtime/files/usr/lib/athena/checks.sh tests/runtime/test_health.sh scripts/test_runtime_scripts.sh
git commit -m "feat: diagnose web ownership and daed api state"
```

---

### Task 6: Add verified Web-only backup rollback

**Files:**
- Modify: `packages/athena-runtime/files/usr/lib/athena/backup.sh`
- Modify: `packages/athena-runtime/files/usr/bin/athena-rollback`
- Modify: `tests/runtime/test_rollback.sh`

**Interfaces:**
- Consumes: verified backup archive `web-config.tar.gz`.
- Produces: `athena-rollback --component web BACKUP_ID`, restoring only Nginx, uHTTPd, and DAED listen/default-service configuration.

- [ ] **Step 1: Add a failing Web-only rollback fixture**

Create fixture files for:

```text
/etc/nginx/conf.d/athena-daed.locations
/etc/config/nginx
/etc/config/uhttpd
/etc/config/daed
/etc/daed/wing.db
```

Create a backup, modify every file, run:

```text
athena-rollback --component web BACKUP_ID
```

Assert the four Web configuration paths are restored while `/etc/daed/wing.db` remains modified. Keep the existing traversal and DAED-only rollback tests.

- [ ] **Step 2: Run the rollback test and observe the rejected component**

Run:

```text
bash tests/runtime/test_rollback.sh
```

Expected: FAIL with `unknown rollback component`.

- [ ] **Step 3: Include DAED service UCI in the Web archive**

Change the Web backup archive inputs to:

```sh
athena_backup_archive "$stage/web-config.tar.gz" \
    etc/nginx etc/config/uhttpd etc/config/nginx etc/config/daed
```

Do not include `/etc/daed/wing.db` in this component.

- [ ] **Step 4: Implement the Web rollback branch**

Accept `all|daed|web`. For `web`, restore only `web-config.tar.gz`. On the real router:

1. stop DAED;
2. restart uHTTPd so port 8080 is available;
3. run `nginx -t`;
4. restart Nginx only if validation succeeds;
5. exit nonzero with a clear message if Nginx validation fails, while leaving recovery uHTTPd running.

Update the usage string to:

```text
athena-rollback [--component all|daed|web] [BACKUP_ID]
```

- [ ] **Step 5: Run backup and rollback tests**

Run:

```text
bash tests/runtime/test_backup.sh
bash tests/runtime/test_rollback.sh
```

Expected: PASS.

- [ ] **Step 6: Commit Web rollback support**

```text
git add packages/athena-runtime/files/usr/lib/athena/backup.sh packages/athena-runtime/files/usr/bin/athena-rollback tests/runtime/test_rollback.sh
git commit -m "feat: add verified web configuration rollback"
```

---

### Task 7: Fail firmware inspection when Web integration is incomplete

**Files:**
- Modify: `scripts/inspect_firmware.py`
- Modify: `tests/test_firmware_inspection.py`

**Interfaces:**
- Consumes: target manifest and `build_dir/target-*/root-qualcommax`.
- Produces `web_integration` in `firmware-inspection.json` with `checked`, `missing`, `forbidden`, and `daed_endpoint` fields.

- [ ] **Step 1: Add complete rootfs fixtures and negative tests**

Extend the fixture manifest with `uhttpd-mod-lua`. Add these rootfs files:

```text
/etc/nginx/conf.d/athena-daed.locations
/etc/uci-defaults/95-athena-web
/www/athena-recovery.html
/www/luci-static/resources/view/athena/daed-panel.js
/usr/share/luci/menu.d/luci-app-athena.json
/usr/bin/daed
```

The fake DAED binary must contain `/athena-daed/graphql` and not `:2023/graphql`.

Add separate tests proving inspection fails when:

- `athena-daed.locations` is missing;
- old `athena-daed.conf` exists;
- `uhttpd-mod-lua` is missing from the manifest;
- `/usr/bin/daed` contains `:2023/graphql`;
- firstboot does not delete `uhttpd.main.listen_http`;
- DAED loopback default is missing.

- [ ] **Step 2: Run the focused firmware tests and observe failures**

Run:

```text
python -m unittest tests.test_firmware_inspection -v
```

Expected: FAIL because current inspection does not report Web integration.

- [ ] **Step 3: Implement structured rootfs inspection**

Add constants for required and forbidden Web files. Read relevant text as strict UTF-8. Read `/usr/bin/daed` as bytes and require:

```python
b"/athena-daed/graphql" in daed_bytes
b":2023/graphql" not in daed_bytes
```

Record every failure in `web_integration` and include it in the final exit condition. Do not skip Web inspection when the rootfs candidate exists.

- [ ] **Step 4: Run firmware inspection and artifact layout tests**

Run:

```text
python -m unittest tests.test_firmware_inspection tests.test_artifact_layout -v
```

Expected: PASS.

- [ ] **Step 5: Commit firmware inspection hardening**

```text
git add scripts/inspect_firmware.py tests/test_firmware_inspection.py
git commit -m "test: enforce web integration in firmware rootfs"
```

---

### Task 8: Add initramfs runtime verification and CI diagnostics

**Files:**
- Modify: `scripts/verify_after_flash.sh`
- Modify: `.github/workflows/build-athena-v19.yml`
- Modify: `scripts/collect_output.sh`
- Modify: `tests/test_workflow.py`
- Modify: `tests/test_artifact_layout.py`

**Interfaces:**
- Consumes: compiled rootfs inspection report and real initramfs runtime.
- Produces: artifact tool `verify-after-flash.sh`, Web verification output, and build failure when rootfs integration is wrong.

- [ ] **Step 1: Add workflow and artifact regression assertions**

Tests must require the workflow to run:

```text
python3 scripts/verify_web_config.py --root .
python3 scripts/inspect_firmware.py ...
```

and require the artifact to include:

```text
tools/verify-after-flash.sh
docs/WEB_RECOVERY.md
diagnostics/firmware-inspection.json
```

- [ ] **Step 2: Extend the hardware verification script**

Add checks for:

```text
nginx -t
Nginx process running
uHTTPd recovery listener configured only on 192.168.50.1:8080
DAED configured as 127.0.0.1:2023 and disabled by default
HTTP response from http://192.168.50.1:8080/athena-recovery.html
HTTPS/LuCI local response through Nginx
no LAN listener on 0.0.0.0:2023 or [::]:2023
```

When DAED is intentionally off, report same-origin DAED proxy unavailability as `WARN`. When DAED is running, require both loopback GraphQL and `/athena-daed/graphql` to be reachable.

- [ ] **Step 3: Preserve detailed inspection diagnostics**

Ensure `collect_output.sh` copies `firmware-inspection.json`, `kernel-size.txt`, and `WEB_RECOVERY.md`. The workflow must keep `Inspect firmware` as a required final outcome and upload diagnostics even on failure.

- [ ] **Step 4: Run workflow and artifact tests**

Run:

```text
python -m unittest tests.test_workflow tests.test_artifact_layout -v
bash -n scripts/verify_after_flash.sh scripts/collect_output.sh
```

Expected: PASS.

- [ ] **Step 5: Commit runtime verification and CI diagnostics**

```text
git add scripts/verify_after_flash.sh scripts/collect_output.sh .github/workflows/build-athena-v19.yml tests/test_workflow.py tests/test_artifact_layout.py
git commit -m "ci: verify initramfs web and daed entry points"
```

---

### Task 9: Document recovery, run the complete verification suite, and package source

**Files:**
- Create: `docs/WEB_RECOVERY.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/SETUP.md`
- Modify: `docs/RECOVERY.md`
- Modify: `docs/BUILD.md`
- Create: `CHANGE_SUMMARY.md`
- Create: `VERIFICATION_REPORT.md`

**Interfaces:**
- Consumes: all implementation tasks and their test output.
- Produces: user-facing recovery instructions, exact validation record, and a GitHub-uploadable source ZIP plus SHA256.

- [ ] **Step 1: Write operator instructions with exact URLs and state meanings**

Document:

```text
Primary LuCI: https://192.168.50.1/
Recovery: http://192.168.50.1:8080/
DAED panel: LuCI → 服务 → Athena 优化 → DAED 面板
Direct port 2023: intentionally unavailable from LAN
```

Explain `enabled`, `running`, and `API reachable`; include commands for `nginx -t`, `athena-health --verbose`, stopping DAED, restarting Nginx/uHTTPd, and rolling back Web configuration. State that initramfs reboot discards changes and must be validated before sysupgrade.

- [ ] **Step 2: Run source-level validation**

Run:

```text
python -m unittest discover -s tests -p "test_*.py" -v
node tests/js/test_dashboard_chart.js
bash scripts/test_runtime_scripts.sh
python scripts/verify_project.py --root .
python scripts/verify_templates.py --templates packages/athena-runtime/files/usr/share/athena/templates --rules packages/athena-runtime/files/usr/share/athena/rules
python scripts/verify_package_layout.py --root .
python scripts/verify_web_config.py --root .
python scripts/security_check.py --root .
git diff --check
```

Expected: every command PASS. Record actual counts and any environment-limited checks in `VERIFICATION_REPORT.md`; do not claim a full OpenWrt build was run locally if it was not.

- [ ] **Step 3: Run syntax checks for every changed executable**

Run:

```text
python -m py_compile scripts/patch_daed_web.py scripts/patch_daed_package.py scripts/verify_web_config.py scripts/inspect_firmware.py
bash -n scripts/prepare_packages.sh scripts/verify_after_flash.sh scripts/collect_output.sh packages/luci-app-athena/root/etc/uci-defaults/95-athena-web packages/athena-runtime/files/usr/libexec/rpcd/athena packages/athena-runtime/files/usr/lib/athena/checks.sh
```

Expected: exit code 0.

- [ ] **Step 4: Review the final diff against the approved spec**

Explicitly verify:

- no `athena-daed.conf` remains;
- no browser code contains `:2023`;
- no uHTTPd port 80/443 listener is created by Athena;
- DAED defaults to disabled and loopback-only;
- Argon/dashboard/IoT features remain present;
- SmartDNS remains absent;
- no node, UUID, key, token, password, public address, or private MAC entered the repo.

- [ ] **Step 5: Commit documentation and verification report**

```text
git add README.md CHANGELOG.md CHANGE_SUMMARY.md VERIFICATION_REPORT.md docs
git commit -m "docs: explain initramfs web and daed recovery"
```

- [ ] **Step 6: Create the source deliverable without build artifacts or secrets**

From the repository parent, create:

```text
jdy2-v19.0.0-rc1-webfix-source.zip
jdy2-v19.0.0-rc1-webfix-source.zip.sha256
```

Exclude `.git`, `.analysis`, `__pycache__`, build logs, downloaded firmware, extracted rootfs, user backups, and DAED databases. Extract the ZIP into a clean temporary directory, rerun the source validators there, and record the ZIP SHA256 in `VERIFICATION_REPORT.md`.

- [ ] **Step 7: Copy final deliverables only after verification**

Copy the source ZIP, SHA256 file, `CHANGE_SUMMARY.md`, and `VERIFICATION_REPORT.md` to `E:\Users\mayib\Desktop\jd2`. Do not push GitHub and do not include compiled firmware unless it came from a successful GitHub Actions run using this exact source commit.

---

## Final Review Gates

- Source tests and static validators all pass.
- Current Nginx/uHTTPd port collision has a regression test.
- Current `*.conf` versus `*.locations` context error has a regression test.
- Current DAED `:2023/graphql` frontend endpoint has a fail-closed source patch and rootfs binary check.
- DAED off/crashed/eBPF-failed states leave LuCI and recovery available.
- The initramfs hardware checklist is included and explicitly blocks persistent flashing until completed.
- Any unrun full build or hardware test is listed as unverified, not reported as passed.
