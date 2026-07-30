# Athena AX6600 Modern Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将登录后的 LuCI `状态 → 概况` 替换为 Athena AX6600 现代化实时仪表盘，同时保持页面只读、低开销、无闪存历史写入，并在 DAED、无线、IPv6、ECM 或温度数据缺失时安全降级。

**Architecture:** 在现有 `athena` rpcd 对象上新增只读 `dashboard` 方法，由运行时 Shell 收集 `/proc`、`/sys`、`ubus`、UCI 和经过分类的 DAED 错误，返回固定 JSON 快照。LuCI 页面每 3 秒轮询一次，在浏览器中计算 CPU/网络增量、维护最多 200 点历史，并使用本地 SVG/CSS 渲染卡片、状态徽标、告警与曲线。通过排序靠后的菜单文件覆盖 `admin/status/overview`，不修改 Argon、`luci-mod-status`、网络、无线或 DAED 配置。

**Tech Stack:** OpenWrt BusyBox `ash`、rpcd/ubus、LuCI JavaScript、LuCI `poll`、原生 SVG/CSS、Python `unittest`、Node.js 纯函数测试、GitHub Actions。

## Global Constraints

- 保持 LAN `192.168.50.1`、恢复入口 `192.168.50.1:8080`、DAED 默认关闭及 `127.0.0.1:2023` 同源反向代理不变。
- 不引入 ECharts、Chart.js、外部 CDN、新后台守护进程、遥测或云端上传。
- 仪表盘 RPC 和页面不得写 UCI、`/etc`、日志、数据库或闪存历史。
- 不返回 Wi-Fi 密码、节点链接、订阅地址、UUID、Token、私钥或完整 DAED 日志。
- 所有可选指标缺失时返回 `null`、空数组或明确状态，不得让整个 RPC 或页面失败。
- 页面刷新后历史清空；单页面最多保留 200 点，采样周期固定为 3 秒。
- 不恢复 ECM frontend 或 Flow Offload；仪表盘仅显示状态。
- 不改 Argon 上游源码；深色、浅色、主色和背景继续由 Argon 配置控制。
- 保留现有不可变 DAED 编译前/编译后来源校验、initramfs/sysupgrade 检查和恢复流程。

---

## File Map and Responsibilities

### Runtime data collection

- **Modify:** `packages/athena-runtime/files/usr/libexec/rpcd/athena`
  - 注册并分派只读 `dashboard` RPC。
- **Create:** `packages/athena-runtime/files/usr/lib/athena/dashboard.sh`
  - 只读采集、字段标准化、JSON 输出和 DAED 错误分类。
- **Modify:** `packages/athena-runtime/files/usr/share/rpcd/acl.d/luci-app-athena.json`
  - 将 `dashboard` 加入现有只读 ACL，不加入写权限。
- **Create:** `tests/runtime/test_dashboard.sh`
  - 在临时根目录和模拟命令下验证固定 JSON 结构、缺失数据与错误分类。

### Browser data and charts

- **Create:** `packages/luci-app-athena/htdocs/luci-static/resources/athena/chart.js`
  - 纯函数：固定长度历史、计数器速率、CPU 百分比、SVG 折线路径。
- **Create:** `tests/js/test_dashboard_chart.js`
  - 使用 Node.js 直接执行纯函数模块。
- **Create:** `packages/luci-app-athena/htdocs/luci-static/resources/athena/dashboard.css`
  - Argon 兼容卡片、徽标、告警、图表和响应式布局。
- **Create:** `packages/luci-app-athena/htdocs/luci-static/resources/view/athena/dashboard.js`
  - RPC 轮询、页面状态、告警映射和 SVG 渲染。
- **Create:** `tests/test_dashboard_assets.py`
  - 静态验证本地资源、3 秒轮询、200 点上限、无外部资源、无写操作及降级文案。

### LuCI routing, validation, packaging, and documentation

- **Create:** `packages/luci-app-athena/root/usr/share/luci/menu.d/zz-athena-dashboard.json`
  - 将 `admin/status/overview` 和 Athena 状态菜单指向 `athena/dashboard`。
- **Modify:** `tests/test_luci_app.py`
  - 验证菜单覆盖和只读 ACL。
- **Modify:** `scripts/verify_web_config.py`
  - 验证仪表盘路由、资源与恢复入口，并继续验证 DAED 反向代理。
- **Modify:** `scripts/verify_package_layout.py`
  - 将仪表盘文件加入源码包硬性清单。
- **Modify:** `tests/test_package_layout_validation.py`
  - 更新最小包布局夹具并增加缺失仪表盘文件的失败测试。
- **Modify:** `.github/workflows/build-athena-v19.yml`
  - 在昂贵编译前运行 Node 图表测试。
- **Modify:** `tests/test_workflow.py`
  - 验证工作流包含仪表盘测试且保留 DAED 来源校验。
- **Modify:** `README.md`
- **Modify:** `CHANGE_SUMMARY.md`
- **Modify:** `VALIDATION_REPORT.md`
- **Create:** `docs/DASHBOARD.md`
  - 使用、指标、告警、故障降级、恢复和真机验收说明。

---

## Task 1: Lock the read-only dashboard RPC contract

**Files:**

- Create: `tests/runtime/test_dashboard.sh`
- Create: `packages/athena-runtime/files/usr/lib/athena/dashboard.sh`
- Modify: `packages/athena-runtime/files/usr/libexec/rpcd/athena`
- Modify: `packages/athena-runtime/files/usr/share/rpcd/acl.d/luci-app-athena.json`

### Step 1: Write the failing runtime contract test

- [ ] 新建 `tests/runtime/test_dashboard.sh`，构造以下临时数据：

```text
/proc/stat
/proc/meminfo
/proc/loadavg
/proc/uptime
/sys/class/net/eth1/statistics/rx_bytes
/sys/class/net/eth1/statistics/tx_bytes
/sys/class/thermal/thermal_zone0/type
/sys/class/thermal/thermal_zone0/temp
/sys/kernel/debug/ecm/front_end_ipv4_stop
/sys/kernel/debug/ecm/front_end_ipv6_stop
/var/log/daed/daed.log
```

- [ ] 在测试临时 `PATH` 中提供只读模拟命令：`ubus`、`uci`、`pidof`、`logread`、`lsmod`。
- [ ] 调用方式固定为：

```sh
ATHENA_ROOT="$ROOT"
ATHENA_LIBDIR="$PROJECT_ROOT/packages/athena-runtime/files/usr/lib/athena"
. "$ATHENA_LIBDIR/common.sh"
. "$ATHENA_LIBDIR/dashboard.sh"
athena_dashboard_json
```

- [ ] 用 `jsonfilter` 可用时校验 JSON；宿主测试用字段匹配校验以下固定顶层键：

```json
{
  "schema_version": 1,
  "sampled_at": 0,
  "system": {},
  "cpu": {},
  "memory": {},
  "wan": {},
  "thermal": [],
  "wireless": {},
  "daed": {},
  "acceleration": {}
}
```

- [ ] 固定子字段如下，任何字段不允许因采集失败而从结构中消失：

```text
system.uptime_seconds
system.load_1
system.load_5
system.load_15
system.time_synced
system.password_set
cpu.total_ticks
cpu.idle_ticks
memory.total_kib
memory.available_kib
wan.up
wan.device
wan.rx_bytes
wan.tx_bytes
wan.ipv4
wan.ipv6
wan.dns_ok
wireless.radios_total
wireless.radios_up
wireless.clients_total
wireless.iot_clients
daed.installed
daed.running
daed.error_code
daed.error_at
acceleration.nss_loaded
acceleration.ecm_ipv4_stopped
acceleration.ecm_ipv6_stopped
acceleration.flow_offload
acceleration.flow_offload_hw
```

- [ ] 增加三个场景：
  1. 完整数据返回确定值；
  2. thermal、ECM、IPv6、IoT 和 DAED 缺失时仍返回有效 JSON；
  3. 日志包含 `LocalTcpSockops` 与 `bpf_get_current_task#35` 时只返回 `error_code="ebpf_local_tcp_sockops"`，不返回原始日志正文。

### Step 2: Run the test to verify it fails

- [ ] Run:

```sh
bash scripts/test_runtime_scripts.sh
```

- [ ] Expected: `test_dashboard.sh` 因 `dashboard.sh` 不存在或固定结构缺失而失败；现有运行时测试仍通过。

### Step 3: Implement the minimal read-only collector

- [ ] 在 `dashboard.sh` 中只提供无副作用函数：

```sh
athena_dashboard_json()
athena_dashboard_cpu()
athena_dashboard_memory()
athena_dashboard_wan()
athena_dashboard_thermal()
athena_dashboard_wireless()
athena_dashboard_daed()
athena_dashboard_acceleration()
```

- [ ] 所有文件路径必须通过 `athena_root` 解析，方便真机和临时测试共用。
- [ ] 所有命令读取失败时使用 `null`、`false` 或空数组，不使用 `set -e` 让单项失败终止整个采集。
- [ ] CPU RPC 返回原始 `total_ticks` 与 `idle_ticks`，百分比留给浏览器按两次采样计算。
- [ ] WAN RPC 返回累计 `rx_bytes` 与 `tx_bytes`，速率留给浏览器计算。
- [ ] thermal 仅返回：

```json
{"id":"cpu","label":"CPU","millicelsius":57900}
```

  其中 `id`、`label` 由已知 thermal zone 类型映射产生，不返回设备路径。
- [ ] DAED 日志最多检查最近 200 行，只分类为：

```text
ebpf_local_tcp_sockops
ebpf_verifier
startup_failure
none
```

  `error_at` 仅在能够安全解析时间时返回 Unix 时间，否则返回 `null`。
- [ ] `time_synced` 同时要求系统年份不早于 2020 且 NTP 状态为已同步；1970 年不得报告为正常。
- [ ] `password_set` 只返回布尔值，不返回 shadow 内容。

### Step 4: Register the method and ACL

- [ ] 将 RPC `list` 输出扩展为：

```sh
"dashboard":{}
```

- [ ] 在 `call` 分支中加入：

```sh
dashboard) athena_dashboard_json ;;
```

- [ ] 在 RPC 顶部加载：

```sh
ATHENA_LIBDIR="${ATHENA_LIBDIR:-/usr/lib/athena}"
. "$ATHENA_LIBDIR/common.sh"
. "$ATHENA_LIBDIR/dashboard.sh"
```

- [ ] 将 ACL 只读列表改为：

```json
"ubus": {
  "athena": ["status", "dashboard", "health", "templates", "backups"]
}
```

- [ ] 不得把 `dashboard` 放入 `write`。

### Step 5: Run focused tests

- [ ] Run:

```sh
bash scripts/test_runtime_scripts.sh
```

- [ ] Expected: 所有运行时 Shell 测试通过，输出包含 `PASS: dashboard`。

### Step 6: Commit

- [ ] Commit:

```sh
git add packages/athena-runtime/files/usr/lib/athena/dashboard.sh \
  packages/athena-runtime/files/usr/libexec/rpcd/athena \
  packages/athena-runtime/files/usr/share/rpcd/acl.d/luci-app-athena.json \
  tests/runtime/test_dashboard.sh
git commit -m "feat: add read-only Athena dashboard RPC"
```

---

## Task 2: Build and test the browser-side sampling math

**Files:**

- Create: `packages/luci-app-athena/htdocs/luci-static/resources/athena/chart.js`
- Create: `tests/js/test_dashboard_chart.js`
- Modify: `.github/workflows/build-athena-v19.yml`
- Modify: `tests/test_workflow.py`

### Step 1: Write failing pure-function tests

- [ ] `tests/js/test_dashboard_chart.js` 使用以下方式加载 LuCI 模块，不需要浏览器 DOM：

```js
const fs = require('fs');
const source = fs.readFileSync(
  'packages/luci-app-athena/htdocs/luci-static/resources/athena/chart.js',
  'utf8'
);
const chart = Function(source)();
```

- [ ] 覆盖以下行为：
  - `appendSample([], point, 200)` 添加首点；
  - 添加 205 点后只保留最新 200 点；
  - 首次 WAN 采样返回 `null` 速率；
  - `deltaRate(1000, 4000, 3)` 返回 `1000` bytes/s；
  - 新计数器小于旧计数器时返回 `0`；
  - CPU 首次采样返回 `null`；
  - CPU 总计数或空闲计数回退时返回 `0`；
  - 正常 CPU 增量限制在 `0..100`；
  - 全相同值的 SVG 曲线仍生成有限坐标；
  - `null` 值造成断段，不生成 `NaN` 或 `Infinity`。

### Step 2: Run the test to verify it fails

- [ ] Run:

```sh
node tests/js/test_dashboard_chart.js
```

- [ ] Expected: 因 `chart.js` 不存在而失败。

### Step 3: Implement the pure module

- [ ] 暴露以下固定 API：

```js
return Object.freeze({
  appendSample: appendSample,
  deltaRate: deltaRate,
  cpuPercent: cpuPercent,
  normalizeSeries: normalizeSeries,
  polylineSegments: polylineSegments
});
```

- [ ] `appendSample` 必须返回新数组或原地裁剪到 `limit`，不得无限增长。
- [ ] `deltaRate` 必须处理首次采样、零间隔、计数器回退和非数字输入。
- [ ] `cpuPercent` 仅使用总 ticks 与 idle ticks 的相邻增量计算。
- [ ] `polylineSegments` 返回可直接用于 SVG `path d` 的本地坐标字符串；不得访问 DOM、网络、存储或定时器。

### Step 4: Add the Node test to source validation

- [ ] 在工作流 `Validate source project` 中，紧跟 Python 测试后加入：

```sh
node tests/js/test_dashboard_chart.js
```

- [ ] 在 `tests/test_workflow.py` 增加断言：

```python
self.assertIn("node tests/js/test_dashboard_chart.js", t)
```

- [ ] 保留并继续断言 `verify_daed_provenance.py`、prebuild/postbuild、双镜像和固件检查步骤。

### Step 5: Run focused tests

- [ ] Run:

```sh
node tests/js/test_dashboard_chart.js
python3 -m unittest tests.test_workflow -v
```

- [ ] Expected: Node 测试全部通过；工作流测试通过。

### Step 6: Commit

- [ ] Commit:

```sh
git add packages/luci-app-athena/htdocs/luci-static/resources/athena/chart.js \
  tests/js/test_dashboard_chart.js \
  .github/workflows/build-athena-v19.yml \
  tests/test_workflow.py
git commit -m "test: cover Athena dashboard sampling math"
```

---

## Task 3: Implement the modern LuCI dashboard and graceful degradation

**Files:**

- Create: `tests/test_dashboard_assets.py`
- Create: `packages/luci-app-athena/htdocs/luci-static/resources/athena/dashboard.css`
- Create: `packages/luci-app-athena/htdocs/luci-static/resources/view/athena/dashboard.js`

### Step 1: Write failing page contract tests

- [ ] `tests/test_dashboard_assets.py` 必须验证：
  - 页面声明 `rpc.declare({ object: 'athena', method: 'dashboard' })`；
  - 使用 `poll.add` 且周期为 `3`；
  - 历史上限为 `200`；
  - 引用本地 `athena/chart` 和 `athena/dashboard.css`；
  - 页面包含 WAN、CPU、内存、温度、Wi-Fi、IoT、DAED、NSS、ECM、Flow Offload；
  - 页面包含 eBPF 不兼容、时间未同步、数据中断和最近成功更新时间文案；
  - 连续两次 RPC 失败后才显示“数据已中断”；
  - 页面不包含 `http://`、`https://`、`fs.exec`、`uci.set`、`uci.commit`、`localStorage` 或写 RPC；
  - CSS 包含桌面四列、平板两列和手机单列断点；
  - CSS 使用主题变量和 `minmax(0, 1fr)`，不固定桌面像素宽度；
  - SVG 具有文本替代或可读数值，不仅依靠颜色。

### Step 2: Run the test to verify it fails

- [ ] Run:

```sh
python3 -m unittest tests.test_dashboard_assets -v
```

- [ ] Expected: 因 `dashboard.js` 和 `dashboard.css` 不存在而失败。

### Step 3: Implement view state and polling

- [ ] 页面依赖固定为：

```js
'require view';
'require rpc';
'require poll';
'require dom';
'require athena.chart as chart';
```

- [ ] 固定常量：

```js
var POLL_SECONDS = 3;
var MAX_POINTS = 200;
```

- [ ] `load()` 首次调用 `dashboard`，`render()` 建立固定 DOM 引用，然后通过 `poll.add()` 更新，不在每次采样重建整个页面。
- [ ] 页面状态至少包含：

```js
{
  samples: [],
  previous: null,
  consecutiveFailures: 0,
  lastSuccessAt: null
}
```

- [ ] 每次成功采样：
  - CPU 通过相邻 ticks 计算；
  - WAN 通过相邻 bytes 和真实时间差计算；
  - 计数器回退时速率为 0；
  - 样本压入并裁剪到 200；
  - 重置失败计数并记录最后成功时间；
  - 更新卡片、状态徽标、告警和三组 SVG。
- [ ] 第一次采样的 CPU/网络速率显示 `—`，不显示 0 或异常尖峰。
- [ ] 单个字段为 `null` 时只将相应值显示为“暂不可用”，其他区域继续刷新。
- [ ] 连续第一次 RPC 失败只保留最后值并增加失败计数；连续第二次失败才显示“数据已中断”。

### Step 4: Implement warning classification

- [ ] 告警优先级固定为：

```text
critical: DAED eBPF 不兼容、WAN 断开
warning: 管理员密码未设置、时间未同步、DNS 异常、射频离线、温度过高
info: DAED 未运行但处于安全默认状态
```

- [ ] `daed.error_code === "ebpf_local_tcp_sockops"` 时显示：

```text
DAED 内核组件不兼容：local_tcp_sockops 无法在当前内核加载。
请打开“服务 → Athena 优化 → DAED 面板”查看日志。
```

- [ ] 时间未同步必须作为独立告警，不能归因于 DAED。
- [ ] DAED 未安装或未运行仅显示关闭/未安装状态，不能把整个仪表盘标为故障。
- [ ] 温度告警阈值在页面中集中定义，默认：

```text
warning >= 80°C
critical >= 90°C
```

### Step 5: Implement SVG charts and CSS

- [ ] 三组图表：
  1. WAN RX/TX bytes/s；
  2. CPU/内存百分比；
  3. CPU/NSS/三路 Wi-Fi 温度。
- [ ] 每张图同时显示当前数值、单位、图例与 SVG；SVG 失败时数值仍可读。
- [ ] CSS 网格：

```css
.athena-dashboard-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
@media (max-width: 1199px) {
  .athena-dashboard-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 767px) {
  .athena-dashboard-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
```

- [ ] 颜色使用 LuCI/Argon 可继承变量和安全后备值；状态同时包含图标/文字。
- [ ] 不给页面、卡片或图表设固定桌面宽度，不允许手机横向溢出。

### Step 6: Run focused tests

- [ ] Run:

```sh
python3 -m unittest tests.test_dashboard_assets -v
node tests/js/test_dashboard_chart.js
```

- [ ] Expected: 仪表盘静态契约和图表数学测试全部通过。

### Step 7: Commit

- [ ] Commit:

```sh
git add packages/luci-app-athena/htdocs/luci-static/resources/athena/dashboard.css \
  packages/luci-app-athena/htdocs/luci-static/resources/view/athena/dashboard.js \
  tests/test_dashboard_assets.py
git commit -m "feat: add modern Athena LuCI dashboard"
```

---

## Task 4: Replace the default LuCI overview without touching Argon

**Files:**

- Create: `packages/luci-app-athena/root/usr/share/luci/menu.d/zz-athena-dashboard.json`
- Modify: `tests/test_luci_app.py`
- Modify: `scripts/verify_web_config.py`

### Step 1: Write failing menu and ACL tests

- [ ] 在 `tests/test_luci_app.py` 增加：

```python
override = json.loads(
    (ROOT / "packages/luci-app-athena/root/usr/share/luci/menu.d/"
            "zz-athena-dashboard.json").read_text(encoding="utf-8")
)
self.assertEqual(
    override["admin/status/overview"]["action"],
    {"type": "view", "path": "athena/dashboard"},
)
self.assertEqual(
    override["admin/services/athena/status"]["action"],
    {"type": "view", "path": "athena/dashboard"},
)
```

- [ ] 验证 `dashboard` 仅出现在 ACL `read.ubus.athena`，不出现在 `write.ubus.athena`。
- [ ] 验证 `luci-mod-status` 和 Argon 主题文件未被复制或修改进自定义包。

### Step 2: Run the test to verify it fails

- [ ] Run:

```sh
python3 -m unittest tests.test_luci_app -v
```

- [ ] Expected: 因覆盖菜单不存在而失败。

### Step 3: Add the deterministic menu override

- [ ] 创建有效 UTF-8 JSON：

```json
{
  "admin/status/overview": {
    "title": "概况",
    "order": 1,
    "action": { "type": "view", "path": "athena/dashboard" },
    "depends": { "acl": [ "luci-app-athena" ] }
  },
  "admin/services/athena/status": {
    "title": "状态",
    "order": 10,
    "action": { "type": "view", "path": "athena/dashboard" },
    "depends": { "acl": [ "luci-app-athena" ] }
  }
}
```

- [ ] 使用 `zz-` 前缀确保该菜单在基础状态菜单后加载；不删除原路由、日志、进程和实时信息菜单。
- [ ] 保留原 `status.js` 作为不被菜单引用的回退源码，直到真机验收完成。

### Step 4: Extend Web validation

- [ ] `verify_web_config.py` 新增检查：
  - 覆盖菜单 JSON 可解析；
  - 两个路径都指向 `athena/dashboard`；
  - `dashboard.js`、`dashboard.css`、`chart.js` 存在；
  - 不存在外部 URL；
  - `192.168.50.1:8080` 恢复入口仍存在；
  - `127.0.0.1:2023` 反向代理仍存在；
  - 页面和 RPC 无 `uci set`、服务启动、停止或重启命令。

### Step 5: Run focused tests

- [ ] Run:

```sh
python3 -m unittest tests.test_luci_app tests.test_dashboard_assets -v
python3 scripts/verify_web_config.py --root .
```

- [ ] Expected: 菜单、ACL、资源和 Web 配置全部通过。

### Step 6: Commit

- [ ] Commit:

```sh
git add packages/luci-app-athena/root/usr/share/luci/menu.d/zz-athena-dashboard.json \
  tests/test_luci_app.py \
  scripts/verify_web_config.py
git commit -m "feat: make Athena dashboard the LuCI overview"
```

---

## Task 5: Make dashboard assets mandatory in source and firmware validation

**Files:**

- Modify: `scripts/verify_package_layout.py`
- Modify: `tests/test_package_layout_validation.py`
- Modify: `scripts/inspect_firmware.py`
- Modify: `tests/test_firmware_inspection.py`

### Step 1: Write failing package-layout tests

- [ ] 扩展最小布局夹具，默认创建：

```text
packages/athena-runtime/files/usr/lib/athena/dashboard.sh
packages/luci-app-athena/htdocs/luci-static/resources/athena/chart.js
packages/luci-app-athena/htdocs/luci-static/resources/athena/dashboard.css
packages/luci-app-athena/htdocs/luci-static/resources/view/athena/dashboard.js
packages/luci-app-athena/root/usr/share/luci/menu.d/zz-athena-dashboard.json
```

- [ ] 新增测试：删除任一仪表盘文件后，`verify_package_layout.py` 必须返回非零并列出缺失路径。

### Step 2: Run the test to verify it fails

- [ ] Run:

```sh
python3 -m unittest tests.test_package_layout_validation -v
```

- [ ] Expected: 验证器尚未要求仪表盘文件，因此“应失败”测试失败。

### Step 3: Extend package layout validation

- [ ] 将上述五个文件加入 `required`。
- [ ] 对 `zz-athena-dashboard.json` 执行 JSON 解析。
- [ ] 对 JS/CSS 做以下静态安全检查：

```text
禁止 http:// 与 https://
禁止 fs.exec
禁止 uci.set / uci.commit
禁止 localStorage / sessionStorage
禁止固定 192.168.50.1:2023
```

### Step 4: Extend offline firmware inspection

- [ ] 保持现有包清单检查，并在能够定位 `root-qualcommax` 或解包 rootfs 时检查：

```text
/usr/lib/athena/dashboard.sh
/www/luci-static/resources/athena/chart.js
/www/luci-static/resources/athena/dashboard.css
/www/luci-static/resources/view/athena/dashboard.js
/usr/share/luci/menu.d/zz-athena-dashboard.json
```

- [ ] 将结果写入 `firmware-inspection.json`：

```json
"dashboard_files": {
  "checked": true,
  "missing": []
}
```

- [ ] 如果构建树可检查且文件缺失，固件检查失败；如果测试夹具没有 rootfs，则用明确 `checked:false`，不得误报通过。
- [ ] 为 `tests/test_firmware_inspection.py` 增加：
  - 完整仪表盘文件通过；
  - 缺少 `dashboard.js` 时失败并报告路径；
  - 原有 `nginx-ssl` 替代包测试继续通过。

### Step 5: Run focused tests

- [ ] Run:

```sh
python3 -m unittest \
  tests.test_package_layout_validation \
  tests.test_firmware_inspection -v
python3 scripts/verify_package_layout.py --root .
```

- [ ] Expected: 新旧包布局和固件检查全部通过。

### Step 6: Commit

- [ ] Commit:

```sh
git add scripts/verify_package_layout.py \
  tests/test_package_layout_validation.py \
  scripts/inspect_firmware.py \
  tests/test_firmware_inspection.py
git commit -m "test: require dashboard assets in Athena firmware"
```

---

## Task 6: Document operation, recovery, and real-device acceptance

**Files:**

- Create: `docs/DASHBOARD.md`
- Modify: `README.md`
- Modify: `CHANGE_SUMMARY.md`
- Modify: `VALIDATION_REPORT.md`

### Step 1: Write the dashboard guide

- [ ] `docs/DASHBOARD.md` 必须包含：
  - 登录后默认进入位置；
  - 3 秒采样、200 点、10 分钟浏览器历史；
  - 每个卡片与曲线的数据含义；
  - DAED eBPF、时间、WAN、DNS、无线、温度告警解释；
  - DAED 未运行是安全默认状态；
  - 不保存历史、不上传数据、不返回凭据；
  - `状态 → 路由/防火墙/系统日志/进程/实时信息` 仍可使用；
  - 删除 `zz-athena-dashboard.json` 后恢复原概况页的方法；
  - `http://192.168.50.1:8080/` 恢复入口；
  - 真机验收清单。

### Step 2: Update project-facing documentation

- [ ] README 首页功能列表加入“现代化只读实时仪表盘”并链接 `docs/DASHBOARD.md`。
- [ ] `CHANGE_SUMMARY.md` 列出新增 RPC、LuCI 首页、SVG 图表、告警、菜单覆盖和测试。
- [ ] `VALIDATION_REPORT.md` 分开记录：
  - 本地自动测试结果；
  - GitHub Actions 构建结果；
  - 尚未执行的真机 initramfs 项；
  - 不得把未执行的真机项目写成通过。

### Step 3: Run documentation and security validators

- [ ] Run:

```sh
python3 scripts/verify_project.py --root .
python3 scripts/security_check.py --root .
```

- [ ] Expected: 无未解析模板变量、CRLF、合并标记或敏感信息。

### Step 4: Commit

- [ ] Commit:

```sh
git add docs/DASHBOARD.md README.md CHANGE_SUMMARY.md VALIDATION_REPORT.md
git commit -m "docs: describe Athena dashboard and recovery"
```

---

## Task 7: Run the complete verification gate and package the source

**Files:**

- Verify all modified files.
- Create deliverables outside the repository:
  - `jdy2-v19.0.0-rc1-dashboard-source.zip`
  - `jdy2-v19.0.0-rc1-dashboard-source.zip.sha256`
  - `ATHENA_DASHBOARD_VALIDATION.md`

### Step 1: Run every source test

- [ ] Run:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/js/test_dashboard_chart.js
bash scripts/test_runtime_scripts.sh
python3 scripts/verify_project.py --root .
python3 scripts/verify_templates.py \
  --templates packages/athena-runtime/files/usr/share/athena/templates \
  --rules packages/athena-runtime/files/usr/share/athena/rules
python3 scripts/verify_package_layout.py --root .
python3 scripts/verify_web_config.py --root .
python3 scripts/security_check.py --root .
```

- [ ] Expected:
  - 所有 Python 测试通过；
  - Node 图表测试通过；
  - 所有运行时 Shell 测试通过；
  - 项目、模板、包布局、Web 与安全检查通过。

### Step 2: Run shell syntax checks

- [ ] Run:

```sh
for file in \
  scripts/*.sh \
  packages/athena-runtime/files/usr/bin/athena-* \
  packages/athena-runtime/files/etc/init.d/athena-runtime \
  packages/athena-runtime/files/usr/lib/athena/*.sh \
  packages/athena-runtime/files/usr/libexec/rpcd/athena \
  packages/luci-app-athena/root/etc/uci-defaults/95-athena-web
do
  sh -n "$file"
done
```

- [ ] Expected: 所有文件退出码为 0。

### Step 3: Review the final diff

- [ ] Run:

```sh
git diff --check
git status --short
git diff --stat
```

- [ ] 确认：
  - 没有修改 Argon 上游源码；
  - 没有 SmartDNS；
  - 没有启用 DAED 默认启动；
  - 没有恢复 ECM/Flow Offload；
  - 没有删除 DAED 来源校验；
  - 没有改变 LAN、恢复入口或同源代理地址；
  - 没有真实节点、Wi-Fi 密码或其他凭据；
  - 所有用户可见中文文件均为 UTF-8。

### Step 4: Build the source ZIP

- [ ] 从已验证的 Git 工作树创建 ZIP，排除：

```text
.git/
__pycache__/
*.pyc
work/
scratch/
build outputs
private backups
```

- [ ] 生成 SHA-256，并重新解压到临时目录后重复运行：

```sh
python3 scripts/verify_project.py --root <extracted-directory>
python3 scripts/verify_package_layout.py --root <extracted-directory>
python3 scripts/verify_web_config.py --root <extracted-directory>
python3 scripts/security_check.py --root <extracted-directory>
```

### Step 5: Write the validation report

- [ ] `ATHENA_DASHBOARD_VALIDATION.md` 必须如实列出：
  - 源码提交或工作树状态；
  - 每条本地命令及结果；
  - ZIP 名称、大小和 SHA-256；
  - GitHub Actions 完整固件编译尚需重新运行；
  - initramfs 真机测试尚需执行；
  - sysupgrade 仅允许在 initramfs 通过后进行；
  - DAED `2026.07.26-r1` 来源校验仍是构建硬门槛。

### Step 6: Final handoff

- [ ] 将 ZIP、SHA256、验证报告和本计划复制到：

```text
C:\Users\mayib\Documents\Codex\2026-07-26\referenced-chatgpt-conversation-this-is-untrusted\outputs
E:\Users\mayib\Desktop\jd2
```

- [ ] 不推送 GitHub，不创建 Release，不声称未运行的 GitHub 或真机测试已经通过。

---

## Final Acceptance Checklist

- [ ] 登录后 `状态 → 概况` 打开 `athena/dashboard`。
- [ ] Athena 状态菜单复用同一视图。
- [ ] 页面每 3 秒采样，最多 200 点，刷新即清空。
- [ ] WAN、CPU、内存和温度曲线无负数、`NaN`、`Infinity` 或重置尖峰。
- [ ] CPU、内存、WAN、三路 Wi-Fi、IoT、DAED、NSS、ECM 和 Flow Offload 状态可读。
- [ ] DAED eBPF helper 不兼容被映射为明确告警。
- [ ] 1970 年或 NTP 未同步被映射为独立告警。
- [ ] 缺少 IPv6、ECM、IoT、thermal 或 DAED 时页面不崩溃。
- [ ] 连续两次 RPC 失败才显示中断，并保留最后成功时间。
- [ ] 无外部资源、遥测、凭据返回和配置写入。
- [ ] Argon 深色、浅色、自定义主色和移动端布局可用。
- [ ] DAED 仍默认关闭并只监听 `127.0.0.1:2023`。
- [ ] 恢复入口仍为 `192.168.50.1:8080`。
- [ ] SmartDNS 未内置。
- [ ] NSS/Wi-Fi offload 保留，ECM frontend 和 Flow Offload 仍停止。
- [ ] GitHub Actions 仍校验不可变 DAED 来源和两个固件镜像。
- [ ] 本地自动测试、ZIP 复验、GitHub 构建和真机测试结果均被分别、如实记录。
