# Athena Homepage and Embedded DAED UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Athena 现代化主页的 LuCI 模块加载错误，并让与 DAED 二进制同源、同版本、同次构建的完整原生 DAED UI 在服务关闭或后端失败时仍可通过 LuCI/Argon 打开。

**Architecture:** `athena/chart.js` 改为标准 `L.Class` 子类，保留现有图表 API。DAED Web 构建产物从已经校验的固定源码归档中安全提取到 `luci-app-athena/root/www/athena-daed/`，Nginx 静态提供完整 SPA，仅把 `/athena-daed/graphql` 反向代理到 `127.0.0.1:2023/graphql`；LuCI 页面始终显示原生 UI iframe，不再让 DAED 进程状态决定 UI 是否存在。

**Tech Stack:** OpenWrt/LiBwrt、LuCI JavaScript、Nginx、DAED/Vite/GraphQL、POSIX shell、Python 3 `unittest`、Node.js、GitHub Actions

## Global Constraints

- LAN 地址保持 `192.168.50.1/24`。
- DAED 首次启动和刷机后默认关闭。
- DAED 只监听 `127.0.0.1:2023`，不得向 LAN 或 WAN 开放 2023 端口。
- Argon 保持默认深色主题并保留原生主题配置能力；Bootstrap 和 `192.168.50.1:8080` 恢复入口保持可用。
- 不内置 SmartDNS，不改变现有 DNS、路由、Steam、游戏、BT、IPv6、IoT SSID、NSS、ECM 或 Flow Offload 策略。
- 完整 DAED UI 必须来自与 DAED 二进制相同的固定源码归档和同一次前端构建，不得下载或维护第二套 UI。
- 浏览器只能使用同源 `/athena-daed/` 和 `/athena-daed/graphql`，任何浏览器端 `:2023` 地址都必须让验证失败。
- 静态 UI 缺少 `index.html`、主 JavaScript、主 CSS、logo 或 HTML 引用的任一资源时，构建必须失败。
- 缓存命中时必须重新校验源码 pins、归档 SHA-256、同源 GraphQL 端点、静态 UI 文件清单和内容摘要。
- 所有修改遵循测试先行；每个任务先观察针对旧实现的失败，再写最小实现并运行相关回归测试。
- 真机验收先使用 U-Boot 内存启动 initramfs，验收通过前不得刷写 sysupgrade。

---

## File Map

### Create

- `scripts/install_daed_web.py`：从已验证的 DAED 源码归档安全提取 `apps/web/dist`，验证资源完整性并生成确定性静态 UI provenance。
- `tests/test_daed_static_web.py`：覆盖安全提取、资源完整性、同源端点、路径穿越和确定性摘要。

### Modify

- `packages/luci-app-athena/htdocs/luci-static/resources/athena/chart.js`：返回可实例化的 LuCI 类。
- `tests/js/test_dashboard_chart.js`：用最小 LuCI 类加载器执行真实模块契约测试。
- `scripts/verify_daed_source_cache.py`：把未压缩静态 UI 清单与树摘要绑定到 DAED 源码缓存 manifest。
- `tests/test_daed_source_assembly.py`：验证静态 UI manifest、缓存拒绝条件和组装阶段安装调用。
- `scripts/assemble_daed_source.sh`：无论缓存命中或重建，都从最终校验过的归档安装静态 UI。
- `packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.locations`：静态 UI 与 GraphQL 反向代理分离。
- `packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js`：始终渲染完整 DAED iframe。
- `tests/test_luci_app.py`：验证 iframe 无条件存在且浏览器不直连 2023。
- `tests/test_web_config.py`：验证 Nginx 静态 SPA 与 GraphQL 路由分离。
- `scripts/verify_web_config.py`：静态检查同源 UI、loopback GraphQL 和恢复入口。
- `scripts/verify_package_layout.py`：要求静态 UI 安装器和原生 UI 路由架构存在。
- `tests/test_package_layout_validation.py`：覆盖新包结构的通过与失败路径。
- `scripts/inspect_firmware.py`：离线验证固件 rootfs 中完整 DAED UI、资源引用、Nginx 路由和 loopback 监听。
- `tests/test_firmware_inspection.py`：为固件检查器增加完整正反向夹具。
- `.github/workflows/build-athena-v19.yml`：缓存 key 纳入安装器，并在四小时固件编译前确认静态 UI 已暂存。
- `tests/test_workflow.py`：验证工作流前置失败门槛和 cache key。
- `CHANGELOG.md`、`CHANGE_SUMMARY.md`、`VERIFICATION_REPORT.md`：记录行为、验证证据和真机待验项。

---

### Task 1: Restore the LuCI chart module contract

**Files:**
- Modify: `tests/js/test_dashboard_chart.js`
- Modify: `packages/luci-app-athena/htdocs/luci-static/resources/athena/chart.js`
- Test: `tests/test_dashboard_assets.py`

**Interfaces:**
- Consumes: LuCI global `L.Class.extend(members)`.
- Produces: an instantiable chart class whose instances expose `appendSample`, `deltaRate`, `cpuPercent`, `normalizeSeries`, and `polylineSegments`.

- [ ] **Step 1: Replace the permissive Node harness with a minimal LuCI class loader**

Add a base class and `extend()` implementation before evaluating the module:

```javascript
class LuCIClass {}

LuCIClass.extend = function(members) {
    class Derived extends LuCIClass {}
    Object.assign(Derived.prototype, members);
    return Derived;
};

const factory = Function('L', source);
const ChartClass = factory({ Class: LuCIClass });

assert.strictEqual(typeof ChartClass, 'function');
assert.ok(ChartClass.prototype instanceof LuCIClass);

const chart = new ChartClass();
for (const method of [
    'appendSample',
    'deltaRate',
    'cpuPercent',
    'normalizeSeries',
    'polylineSegments'
])
    assert.strictEqual(typeof chart[method], 'function');
```

Move all existing method assertions from the returned plain object to the `chart` instance.

- [ ] **Step 2: Run the focused test and confirm the old factory fails**

Run: `node tests/js/test_dashboard_chart.js`

Expected: FAIL because the old module returns a frozen plain object, not a LuCI subclass constructor.

- [ ] **Step 3: Return a standard LuCI class from `chart.js`**

Keep every existing helper function unchanged and replace only the final return expression with:

```javascript
return L.Class.extend({
    appendSample: appendSample,
    deltaRate: deltaRate,
    cpuPercent: cpuPercent,
    normalizeSeries: normalizeSeries,
    polylineSegments: polylineSegments
});
```

Do not change public method names, sampling limits, rate calculations, SVG segmentation, polling cadence, or dashboard layout.

- [ ] **Step 4: Run focused and asset regression tests**

Run:

```bash
node tests/js/test_dashboard_chart.js
python -m unittest tests.test_dashboard_assets -v
```

Expected: all tests PASS and the Node test prints its existing success line.

- [ ] **Step 5: Commit the homepage fix**

```bash
git add tests/js/test_dashboard_chart.js \
  packages/luci-app-athena/htdocs/luci-static/resources/athena/chart.js
git commit -m "fix: load Athena charts as a LuCI class"
```

---

### Task 2: Safely stage the original DAED static UI from the verified source archive

**Files:**
- Create: `scripts/install_daed_web.py`
- Create: `tests/test_daed_static_web.py`
- Modify: `scripts/assemble_daed_source.sh`

**Interfaces:**
- Consumes: `install_daed_web.py ARCHIVE DESTINATION PROVENANCE`, where `ARCHIVE` is the already verified `daed-*.tar.gz` and the archive contains exactly one root directory with `apps/web/dist/`.
- Produces: `DESTINATION/index.html`, the complete `dist` tree, and `PROVENANCE` JSON with `schema`, `archive`, `root`, `file_count`, `tree_sha256`, and sorted `files` entries containing `path`, `size`, and `sha256`. The package copy of this provenance is installed into the firmware so offline inspection can verify every lazy-loaded asset, not only files directly referenced by `index.html`.

- [ ] **Step 1: Add failing extraction and rejection tests**

Create fixtures in `tests/test_daed_static_web.py` with this valid archive tree:

```text
daed-2026.07.26/
└── apps/web/dist/
    ├── index.html
    ├── logo.webp
    └── assets/
        ├── index-abc.js
        └── index-def.css
```

The valid `index.html` must reference `./assets/index-abc.js`, `./assets/index-def.css`, and `./logo.webp`; the JavaScript must contain `/athena-daed/graphql` and must not contain `:2023/graphql`.

Add tests named `test_installs_complete_static_ui_and_writes_deterministic_provenance`, `test_rejects_missing_index_reference`, `test_rejects_missing_javascript`, `test_rejects_missing_stylesheet`, `test_rejects_missing_logo`, `test_rejects_browser_port_2023_endpoint`, `test_rejects_non_same_origin_graphql_endpoint`, `test_rejects_path_traversal_member`, `test_rejects_symlink_under_dist`, and `test_reinstall_replaces_stale_destination_files`. Each rejection test must invoke the CLI in a subprocess, assert a nonzero return code, and assert the pre-existing destination sentinel remains unchanged.

The success test must run the installer twice and assert identical `tree_sha256` and sorted `files` arrays.

- [ ] **Step 2: Run the new suite and confirm the installer is absent**

Run: `python -m unittest tests.test_daed_static_web -v`

Expected: ERROR importing or executing `scripts/install_daed_web.py`.

- [ ] **Step 3: Implement a fail-closed archive inspector and installer**

Implement five typed functions: `sha256_bytes(data: bytes) -> str`, `normalized_member_path(name: str) -> PurePosixPath`, `inspect_archive(archive: Path) -> dict[str, object]`, `install_static_web(archive: Path, destination: Path, provenance: Path) -> dict[str, object]`, and `main(argv: list[str] | None = None) -> int`.

`inspect_archive()` must:

- reject absolute paths, `..`, empty components, links, devices and duplicate paths;
- find exactly one archive root and exactly one `<root>/apps/web/dist/index.html`;
- collect only regular files under `apps/web/dist/`;
- parse `index.html` `src=` and `href=` references beginning with `./`;
- require at least one referenced `.js`, one referenced `.css`, and one referenced logo image;
- require every local reference to exist in the archive;
- require some JavaScript asset to contain `/athena-daed/graphql`;
- reject `:2023/graphql`, `127.0.0.1:2023`, and `192.168.50.1:2023` in browser assets;
- compute a stable tree digest from sorted records using `path + NUL + sha256 + LF`.

`install_static_web()` must write into a temporary sibling directory, verify every written file hash, remove only the exact requested destination after all validation succeeds, atomically rename the temporary directory, and atomically write provenance JSON. On failure it must leave the previous destination intact.

The CLI must be:

```bash
python scripts/install_daed_web.py \
  --archive "$ARCHIVE" \
  --destination "$TOPDIR/package/custom/luci-app-athena/root/www/athena-daed" \
  --provenance "$PROVENANCE_DIR/static-web.json"
```

- [ ] **Step 4: Run the static UI installer tests**

Run: `python -m unittest tests.test_daed_static_web -v`

Expected: all static UI tests PASS.

- [ ] **Step 5: Invoke the installer after final cache verification on both cache-hit and rebuild paths**

In `scripts/assemble_daed_source.sh`, place one unconditional call after the selected archive and manifest have passed `verify_daed_source_cache.py`, and before `install_daed_source.py`:

```bash
STATIC_WEB_DEST="$TOPDIR/package/custom/luci-app-athena/root/www/athena-daed"
STATIC_WEB_PACKAGE_MANIFEST="$TOPDIR/package/custom/luci-app-athena/root/usr/share/athena/daed-static-web.json"
STATIC_WEB_PROVENANCE="$PROVENANCE/static-web.json"

python3 "$PROJECT_ROOT/scripts/install_daed_web.py" \
  --archive "$ARCHIVE" \
  --destination "$STATIC_WEB_DEST" \
  --provenance "$STATIC_WEB_PACKAGE_MANIFEST"

test -s "$STATIC_WEB_DEST/index.html"
test -s "$STATIC_WEB_PACKAGE_MANIFEST"
cp "$STATIC_WEB_PACKAGE_MANIFEST" "$STATIC_WEB_PROVENANCE"
test -s "$STATIC_WEB_PROVENANCE"
```

Do not copy directly from the temporary build directory because that directory does not exist on a cache hit.

- [ ] **Step 6: Run shell syntax and focused suites**

Run:

```bash
bash -n scripts/assemble_daed_source.sh
python -m unittest tests.test_daed_static_web tests.test_daed_source_assembly -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit static UI staging**

```bash
git add scripts/install_daed_web.py scripts/assemble_daed_source.sh \
  tests/test_daed_static_web.py
git commit -m "feat: stage the pinned DAED web interface"
```

---

### Task 3: Bind the static UI to the DAED source cache manifest

**Files:**
- Modify: `scripts/verify_daed_source_cache.py`
- Modify: `tests/test_daed_source_assembly.py`

**Interfaces:**
- Consumes: the source archive inspected in Task 2 and the existing pin dictionary used by `verify_daed_source_cache.py`.
- Produces: cache manifest schema `2` with `static_web.file_count`, `static_web.tree_sha256`, and `static_web.files`; verification succeeds only if the archive reproduces the stored values.

- [ ] **Step 1: Add cache manifest failure tests**

Extend the existing archive fixture to include complete uncompressed `apps/web/dist/` assets. Add tests named `test_write_manifest_records_static_web_tree`, `test_verify_rejects_static_web_tree_hash_mismatch`, `test_verify_rejects_static_web_file_list_mismatch`, `test_verify_rejects_missing_static_web_asset`, `test_verify_rejects_static_web_browser_port`, and `test_schema_one_manifest_is_rebuilt_instead_of_reused`. Each negative test must alter exactly one archive or manifest field and assert the verifier exits nonzero.

For the positive case assert:

```python
self.assertEqual(manifest["schema"], 2)
self.assertGreater(manifest["static_web"]["file_count"], 3)
self.assertEqual(len(manifest["static_web"]["tree_sha256"]), 64)
self.assertEqual(
    [entry["path"] for entry in manifest["static_web"]["files"]],
    sorted(entry["path"] for entry in manifest["static_web"]["files"]),
)
```

- [ ] **Step 2: Run the focused cache tests and confirm schema-one behavior fails the new contract**

Run: `python -m unittest tests.test_daed_source_assembly -v`

Expected: FAIL because the current manifest has no `static_web` object and uses schema `1`.

- [ ] **Step 3: Extend archive inspection and manifest comparison**

Add this data structure to the written manifest:

```json
{
  "schema": 2,
  "static_web": {
    "file_count": 4,
    "tree_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
    "files": [
      {"path": "assets/index-abc.js", "size": 123, "sha256": "0000000000000000000000000000000000000000000000000000000000000000"},
      {"path": "assets/index-def.css", "size": 45, "sha256": "0000000000000000000000000000000000000000000000000000000000000000"},
      {"path": "index.html", "size": 200, "sha256": "0000000000000000000000000000000000000000000000000000000000000000"},
      {"path": "logo.webp", "size": 80, "sha256": "0000000000000000000000000000000000000000000000000000000000000000"}
    ]
  }
}
```

When verifying, calculate the archive’s current static UI record again and compare the entire object for equality. A schema mismatch, missing key, different ordering, size, hash, endpoint, or asset reference must return nonzero so `assemble_daed_source.sh` takes its existing rebuild branch.

- [ ] **Step 4: Run cache and installer suites together**

Run:

```bash
python -m unittest tests.test_daed_source_assembly tests.test_daed_static_web -v
```

Expected: all tests PASS and old schema-one fixtures are rejected safely.

- [ ] **Step 5: Commit the cache binding**

```bash
git add scripts/verify_daed_source_cache.py tests/test_daed_source_assembly.py
git commit -m "fix: bind DAED UI assets to source cache"
```

---

### Task 4: Serve the complete original UI and proxy only GraphQL

**Files:**
- Modify: `packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.locations`
- Modify: `packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js`
- Modify: `tests/test_web_config.py`
- Modify: `tests/test_luci_app.py`

**Interfaces:**
- Consumes: `/www/athena-daed/` from Task 2 and DAED GraphQL at `127.0.0.1:2023/graphql`.
- Produces: static SPA at `/athena-daed/`, GraphQL proxy at `/athena-daed/graphql`, and an unconditional LuCI iframe pointing only at `/athena-daed/`.

- [ ] **Step 1: Add Nginx split-routing tests**

Require the exact responsibilities below:

```python
self.assertRegex(config, r"location\s+=\s+/athena-daed/graphql\s*\{")
self.assertIn("proxy_pass http://127.0.0.1:2023/graphql;", config)
self.assertIn("proxy_buffering off;", config)
self.assertIn("proxy_set_header Upgrade $http_upgrade;", config)
self.assertRegex(config, r"location\s+/athena-daed/\s*\{")
self.assertIn("root /www;", config)
self.assertIn("try_files $uri $uri/ /athena-daed/index.html;", config)
```

Also extract each location block and assert the static UI block contains no `proxy_pass`, while the GraphQL block contains no `root /www` or `try_files`.

- [ ] **Step 2: Add LuCI panel tests for an unconditional original UI iframe**

Require:

```python
self.assertIn("src: '/athena-daed/'", source)
self.assertNotIn("src: 'http://", source)
self.assertNotIn(":2023", source)
self.assertNotRegex(source, r"if\s*\(\s*ready\s*\).*createElement\('iframe'")
self.assertIn("allow: 'clipboard-read; clipboard-write'", source)
```

Add a test that the backend status banner may change text but the iframe creation remains outside all `daed_running` and `daed_api_reachable` conditionals.

- [ ] **Step 3: Run the Web tests and confirm current whole-site proxy/status replacement fails**

Run:

```bash
python -m unittest tests.test_web_config tests.test_luci_app -v
```

Expected: FAIL because `/athena-daed/` is currently proxied and the iframe is conditional.

- [ ] **Step 4: Split Nginx locations**

Use this configuration shape:

```nginx
location = /athena-daed/graphql {
    proxy_pass http://127.0.0.1:2023/graphql;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_buffering off;
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
}

location /athena-daed/ {
    root /www;
    try_files $uri $uri/ /athena-daed/index.html;
}
```

Keep the project’s existing include conventions for `$connection_upgrade`; do not add a second Nginx server or expose port 2023.

- [ ] **Step 5: Make the LuCI panel always append the DAED iframe**

Keep start/stop/restart actions and a compact read-only status banner. Construct the iframe unconditionally after status rendering:

```javascript
const frame = E('iframe', {
    src: '/athena-daed/',
    title: _('DAED interface'),
    sandbox: 'allow-forms allow-modals allow-popups allow-same-origin allow-scripts allow-downloads',
    allow: 'clipboard-read; clipboard-write',
    referrerpolicy: 'same-origin'
});

container.appendChild(frame);
```

Do not inject CSS or JavaScript into the iframe and do not replace it with custom status/configuration cards when DAED is stopped or unreachable.

- [ ] **Step 6: Run Web tests**

Run:

```bash
python -m unittest tests.test_web_config tests.test_luci_app -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit the original UI routing**

```bash
git add packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.locations \
  packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js \
  tests/test_web_config.py tests/test_luci_app.py
git commit -m "feat: keep the original DAED interface available"
```

---

### Task 5: Strengthen source-tree and package validators

**Files:**
- Modify: `scripts/verify_web_config.py`
- Modify: `scripts/verify_package_layout.py`
- Modify: `tests/test_web_config.py`
- Modify: `tests/test_package_layout_validation.py`

**Interfaces:**
- Consumes: repository source files, not generated Web assets.
- Produces: build-preflight failures for missing installer integration, whole-site proxying, conditional iframe display, browser `:2023`, or missing recovery/loopback defaults.

- [ ] **Step 1: Add validator failure fixtures**

Add isolated temporary-tree tests named `test_rejects_missing_static_web_installer`, `test_rejects_missing_assembly_install_call`, `test_rejects_whole_daed_site_proxy`, `test_rejects_graphql_proxy_not_loopback`, `test_rejects_conditional_daed_iframe`, `test_rejects_browser_visible_port_2023`, `test_rejects_daed_enabled_by_default`, and `test_rejects_missing_recovery_listener`.

Each mutation test must start from a passing minimal fixture and change exactly one invariant.

- [ ] **Step 2: Run validator tests and observe the missing checks**

Run:

```bash
python -m unittest tests.test_web_config tests.test_package_layout_validation -v
```

Expected: one or more new negative fixtures incorrectly pass under the old validators.

- [ ] **Step 3: Implement exact source-tree invariants**

`verify_web_config.py` must verify:

```text
static /athena-daed/ location -> root /www + SPA try_files
exact /athena-daed/graphql location -> 127.0.0.1:2023/graphql
UI location has no proxy_pass
iframe points to /athena-daed/ unconditionally
no browser-visible :2023 URL
DAED UCI listen_addr remains 127.0.0.1:2023
DAED UCI enabled remains 0
uhttpd recovery listener remains 0.0.0.0:8080 and [::]:8080
```

`verify_package_layout.py` must require:

```text
scripts/install_daed_web.py
assemble_daed_source.sh invocation of install_daed_web.py
luci-app-athena/root/etc/nginx/conf.d/athena-daed.locations
luci-app-athena DAED panel iframe source
```

It must not require generated `/www/athena-daed` files in the Git source tree because they are installed from the validated DAED archive during the workflow.

- [ ] **Step 4: Run validators and project preflight**

Run:

```bash
python -m unittest tests.test_web_config tests.test_package_layout_validation -v
python scripts/verify_web_config.py
python scripts/verify_package_layout.py
```

Expected: all tests and both validators PASS.

- [ ] **Step 5: Commit validator hardening**

```bash
git add scripts/verify_web_config.py scripts/verify_package_layout.py \
  tests/test_web_config.py tests/test_package_layout_validation.py
git commit -m "test: enforce persistent embedded DAED UI"
```

---

### Task 6: Verify the complete UI inside compiled firmware

**Files:**
- Modify: `scripts/inspect_firmware.py`
- Modify: `tests/test_firmware_inspection.py`

**Interfaces:**
- Consumes: the extracted initramfs/sysupgrade rootfs `Path`, `/usr/share/athena/daed-static-web.json`, and the existing firmware inspection report.
- Produces: `daed_static_ui` report data and fatal findings for missing/referenced assets, wrong endpoint, whole-site proxying, or exposed DAED listener.

- [ ] **Step 1: Extend the valid rootfs fixture with a real static SPA shape**

Add:

```text
/www/athena-daed/index.html
/www/athena-daed/logo.webp
/www/athena-daed/assets/index-abc.js
/www/athena-daed/assets/index-def.css
/usr/share/athena/daed-static-web.json
```

The HTML must reference all three files relatively; JavaScript must contain `/athena-daed/graphql` and no `:2023` address. Update the Nginx fixture to use the two locations from Task 4.

- [ ] **Step 2: Add firmware rejection tests**

Add tests named `test_rejects_missing_daed_static_index`, `test_rejects_missing_daed_index_reference`, `test_rejects_missing_daed_javascript`, `test_rejects_missing_daed_stylesheet`, `test_rejects_missing_daed_logo`, `test_rejects_daed_browser_port_2023`, `test_rejects_daed_static_location_proxy`, `test_rejects_daed_graphql_proxy_not_loopback`, and `test_reports_daed_static_ui_hashes`. Each rejection test must copy the valid rootfs fixture, mutate exactly one file or route, invoke `inspect_firmware.main()` through the existing harness, and assert the report identifies the corresponding fatal invariant.

- [ ] **Step 3: Run the firmware inspection suite and confirm old inspection misses static UI defects**

Run: `python -m unittest tests.test_firmware_inspection -v`

Expected: new negative tests FAIL because the old inspector does not require static UI files.

- [ ] **Step 4: Implement static UI rootfs inspection**

Add typed helpers `inspect_daed_static_ui(rootfs: Path) -> dict[str, object]` and `parse_local_asset_references(index_html: str) -> list[str]`.

The result must contain:

```python
{
    "index": "/www/athena-daed/index.html",
    "file_count": 4,
    "tree_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
    "javascript": ["/www/athena-daed/assets/index-abc.js"],
    "stylesheets": ["/www/athena-daed/assets/index-def.css"],
    "logos": ["/www/athena-daed/logo.webp"],
    "graphql_endpoint": "/athena-daed/graphql",
}
```

Load `/usr/share/athena/daed-static-web.json`, require every listed file under `/www/athena-daed/`, recompute every size, SHA-256 and the full tree digest, then verify HTML reference completeness and the endpoint rules. Reject unlisted files as well as missing files so the installed tree exactly matches provenance. Any invariant failure must append a fatal firmware-inspection error, not only a warning.

Keep existing checks that DAED binary embeds its Web resources; this task adds the independent static original UI requirement rather than replacing binary provenance checks.

- [ ] **Step 5: Run firmware and artifact tests**

Run:

```bash
python -m unittest tests.test_firmware_inspection tests.test_artifact_layout -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit firmware inspection**

```bash
git add scripts/inspect_firmware.py tests/test_firmware_inspection.py
git commit -m "test: inspect the DAED static UI in firmware"
```

---

### Task 7: Move static UI failure detection before the long firmware build

**Files:**
- Modify: `.github/workflows/build-athena-v19.yml`
- Modify: `tests/test_workflow.py`

**Interfaces:**
- Consumes: `install_daed_web.py`, `assemble_daed_source.sh`, staged package root and static UI provenance.
- Produces: a workflow that invalidates the DAED source cache when installer logic changes and aborts before `make` if the complete UI is absent or invalid.

- [ ] **Step 1: Add workflow contract tests**

Require the workflow source to contain:

```python
self.assertIn("scripts/install_daed_web.py", cache_hash_expression)
self.assertIn("root/www/athena-daed/index.html", workflow)
self.assertIn("daed-source-provenance/static-web.json", workflow)
```

Also assert the staging checks appear after `assemble_daed_source.sh` and before the `Build both images` step.

- [ ] **Step 2: Run workflow tests and confirm missing key/staging guards fail**

Run: `python -m unittest tests.test_workflow -v`

Expected: FAIL because the current cache key and pre-build guard do not include the static UI installer/output.

- [ ] **Step 3: Extend the cache key and assembly step guards**

Add the installer and cache verifier to the source cache hash:

```yaml
${{ hashFiles(
  'SOURCES.lock.json',
  'patches/daed/**',
  'scripts/assemble_daed_source.sh',
  'scripts/install_daed_web.py',
  'scripts/patch_daed_web.py',
  'scripts/verify_daed_source_cache.py'
) }}
```

Immediately after assembly, require:

```bash
test -s openwrt/package/custom/luci-app-athena/root/www/athena-daed/index.html
test -s openwrt/package/custom/luci-app-athena/root/usr/share/athena/daed-static-web.json
test -s daed-source-provenance/static-web.json
python3 scripts/verify_web_config.py
```

Do not add a second Web download/build job. Keep source cache save after successful manifest and static UI checks, before the long OpenWrt compilation.

- [ ] **Step 4: Run workflow and assembly tests**

Run:

```bash
python -m unittest tests.test_workflow tests.test_daed_source_assembly \
  tests.test_daed_static_web -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit workflow fail-fast checks**

```bash
git add .github/workflows/build-athena-v19.yml tests/test_workflow.py
git commit -m "ci: verify DAED UI before firmware compilation"
```

---

### Task 8: Document, run complete verification, and package the source release

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `CHANGE_SUMMARY.md`
- Modify: `VERIFICATION_REPORT.md`
- Verify: all modified source and test files

**Interfaces:**
- Consumes: all outputs from Tasks 1–7.
- Produces: auditable validation evidence and a source ZIP suitable for user upload to GitHub; no remote push.

- [ ] **Step 1: Update release documentation with exact behavior**

Record:

```text
Homepage: athena.chart now returns a LuCI class; no invalid-constructor error.
DAED UI: original static UI is always available at /athena-daed/.
GraphQL: only /athena-daed/graphql is proxied to 127.0.0.1:2023/graphql.
Defaults: DAED remains disabled and loopback-only; recovery remains on LAN port 8080.
Provenance: static UI is extracted from and hashed with the same pinned source archive as the DAED binary.
Known boundary: this change does not fix kernel/eBPF compatibility failures; it keeps the UI reachable while the backend is offline.
```

- [ ] **Step 2: Run syntax and focused JavaScript checks**

Run:

```bash
bash -n scripts/assemble_daed_source.sh
node tests/js/test_dashboard_chart.js
python -m py_compile scripts/install_daed_web.py \
  scripts/verify_daed_source_cache.py scripts/inspect_firmware.py
```

Expected: all commands exit `0`.

- [ ] **Step 3: Run the complete Python test suite**

Run:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: all tests PASS; record the exact test count and duration in `VERIFICATION_REPORT.md`.

- [ ] **Step 4: Run runtime shell tests and project validators**

Run:

```bash
bash scripts/test_runtime_scripts.sh
python scripts/verify_project.py
python scripts/verify_templates.py
python scripts/verify_package_layout.py
python scripts/verify_web_config.py
python scripts/security_check.py
```

Expected: all commands exit `0`. Record each command and result. If a command fails, leave it listed as a failure with its exact error; do not claim completion.

- [ ] **Step 5: Inspect the final diff and forbidden endpoints**

Run:

```bash
git diff --check
git grep -nE 'https?://[^[:space:]]*:2023|192\.168\.50\.1:2023' -- \
  packages scripts .github ':!docs/superpowers/specs/*' ':!docs/superpowers/plans/*'
git status --short
```

Expected: `git diff --check` exits `0`; endpoint search returns no browser-facing occurrence other than intentional loopback service configuration that validators explicitly recognize; status contains only the intended documentation changes before the final commit.

- [ ] **Step 6: Commit documentation and verification evidence**

```bash
git add CHANGELOG.md CHANGE_SUMMARY.md VERIFICATION_REPORT.md
git commit -m "docs: record embedded DAED UI verification"
```

- [ ] **Step 7: Create the deliverable ZIP and SHA-256 without including Git metadata**

From the repository parent directory, create:

```powershell
$Source = 'jdy2-main'
$Zip = 'Athena-AX6600-DAED-v19.0.0-rc1-source.zip'
Compress-Archive -Path "$Source\*" -DestinationPath $Zip -Force
(Get-FileHash -Algorithm SHA256 $Zip).Hash.ToLower() |
  Set-Content -Encoding ascii "$Zip.sha256"
```

Before delivery, inspect the ZIP entries and confirm it contains `.github/workflows/build-athena-v19.yml`, `scripts/install_daed_web.py`, both package directories, docs, tests, `CHANGE_SUMMARY.md`, and `VERIFICATION_REPORT.md`, and does not contain `.git`, generated firmware, private node links, Wi-Fi passwords, tokens, or personal backup files.

- [ ] **Step 8: Report local verification limits explicitly**

The final handoff must distinguish:

```text
Locally verified: syntax, unit tests, runtime mocks, validators, security scan, ZIP integrity.
Requires GitHub Actions: complete LiBwrt/DAED/OpenWrt build and cache-hit build.
Requires real device: initramfs homepage, full static DAED UI while service is off, GraphQL reconnect after service starts, all original DAED sections, LAN/WAN port-2023 isolation, port-8080 recovery.
```

Do not label the firmware safe for sysupgrade until the initramfs checklist passes on JDCloud RE-CS-02 hardware.

---

## Final Acceptance Checklist

- [ ] LuCI overview opens without `factory yields invalid constructor`.
- [ ] `athena.chart` is a LuCI class and all existing chart methods behave unchanged.
- [ ] DAED remains disabled by default and listens only on `127.0.0.1:2023` when started.
- [ ] `/athena-daed/` is a static complete original DAED UI and does not depend on the DAED process for HTML/CSS/JS.
- [ ] `/athena-daed/graphql` is the only DAED route proxied to loopback.
- [ ] LuCI always renders the DAED iframe, including when the backend is stopped or eBPF loading fails.
- [ ] Static UI and DAED binary derive from the same validated source archive.
- [ ] Cache manifests bind the complete static UI file list and digest.
- [ ] Build fails before long compilation when static UI staging is incomplete.
- [ ] Firmware inspection fails for missing assets, browser `:2023`, wrong Nginx routing, non-loopback listener, or enabled-by-default DAED.
- [ ] Argon, Bootstrap recovery, LAN address, IoT SSID, DNS/routing and NSS/ECM policies remain unchanged.
- [ ] All local failures are recorded truthfully and all remaining GitHub Actions/real-device checks are explicitly identified.
