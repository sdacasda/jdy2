# Athena v19.0.0-rc1 验证报告

## 仪表盘变更验证范围

### 本地自动化

本次源码变更要求以下项目在打包前全部通过：

- Python 单元与行为测试；
- Node.js 图表采样数学测试；
- OpenWrt 运行时 Shell 测试；
- 项目、模板、包布局、Web 配置和敏感信息检查；
- Shell 语法检查；
- 重新解压源码 ZIP 后重复执行核心验证。

2026-07-30 的工作树验证结果：

```text
Python 单元/行为测试：45/45 通过
Node.js 图表数学测试：通过
运行时 Shell 测试：8/8 通过
Shell 语法：27 个文件通过
项目、模板、包布局、Web、安全检查：全部通过
```

最终 ZIP 哈希和解压复验记录在随交付包生成的
`ATHENA_DASHBOARD_VALIDATION.md`。

### GitHub Actions

已有第 9 次工作流证明仪表盘修改前的 v19 基础构建可以成功生成两种镜像。**当前仪表盘源码修改尚未重新运行 GitHub Actions 完整编译**，不能将旧结果视为新仪表盘已进入固件的证明。新版工作流会运行图表测试，并在可定位 rootfs 时检查所有仪表盘文件。

### 真机

**尚未执行本次修改后的 initramfs 真机验收，也未执行 sysupgrade。** 必须先验证 LuCI 首页、Argon 响应式布局、DAED eBPF 告警、三路无线、IoT SSID、恢复入口和重启持久化。initramfs 未通过前不得刷写 sysupgrade。

验证日期：2026-07-27

## 第 9 次 GitHub Actions Artifact

文件：

```text
Athena-AX6600-v19-9-test.zip
```

ZIP SHA-256：

```text
a4f19842aaad8fa91ddf7a43dce3c0d6d334668c6f1e675a02259299e2dfb83e
```

ZIP 验证：

- ZIP 中共有 36 个文件；
- ZIP CRC 全部通过；
- Windows 大小写文件名冲突为 0；
- `UPSTREAM_SHA256SUMS` 与 `SHA256SUMS` 均存在；
- validate、defconfig、configcheck、compile、inspect 全部为 success。

固件：

```text
70c14865ad4f13428bbdcf6698f435d4b9b19292d02966fc4e8f78fd7bab084b  athena-v19-initramfs-uImage.itb
94b1bf9cbd3183dd60f237dfbc3106ca51b476db46386d41843587dde51e2b79  athena-v19-squashfs-sysupgrade.bin
```

`firmware/SHA256SUMS` 全部通过。initramfs 被识别为有效的 Device Tree
Blob/FIT；sysupgrade 被识别为 POSIX tar，包含：

```text
sysupgrade-jdcloud_re-cs-02/CONTROL
sysupgrade-jdcloud_re-cs-02/kernel
sysupgrade-jdcloud_re-cs-02/root
```

CONTROL：

```text
BOARD=jdcloud_re-cs-02
```

内核 5,561,400 字节，rootfs 40,239,104 字节，内核距离 6 MiB 上限仍有
730,056 字节余量。必需包完整，禁用包为 0。

### 总校验清单问题

根目录 `SHA256SUMS.txt` 的所有普通文件均通过，但列出的 16 个隐藏诊断文件
没有出现在下载的 Artifact 中。原因是 `actions/upload-artifact` 默认忽略
以 `.` 开头的文件，而校验清单在上传前已经包含它们。

这不影响固件镜像、manifest、profiles、配置或构建日志，但会破坏 Artifact
整体可验证性。工作流已加入 `include-hidden-files: true`，并用回归测试保护。

## 输入证据

### 第 8 次 GitHub Actions 日志

文件：

```text
logs_81935989017.zip
```

SHA-256：

```text
CE4F27BE649CA79F028A3762D4ADABEC4A18A8B0A44A24893557EC2F864B35E6
```

### 第 8 次 GitHub Actions Artifact

文件：

```text
Athena-AX6600-v19-8-test.zip
```

SHA-256：

```text
F30B0406A0DAE7F9AE12B0F9B79CEA582C59D344790EE08355586D3DCE263CCC
```

## 云端构建结果

以下阶段成功：

- Validate source project
- Install build dependencies
- Clone immutable LiBwrt source
- Prepare feeds and locked packages
- Generate effective OpenWrt config
- Verify effective OpenWrt config
- Build both images
- Collect artifact

最终状态为 `inspect=failure`。原始检查报告只有一项失败：

```json
"missing_packages": ["nginx"]
```

实际 manifest 包含：

```text
luci-nginx
nginx-mod-luci
nginx-mod-ubus
nginx-ssl
nginx-ssl-util
```

项目配置本来就选择 `CONFIG_PACKAGE_nginx-ssl=y`，没有选择
`CONFIG_PACKAGE_nginx=y`。因此这是检查器与配置不一致造成的假失败。

## 真实固件数据

| 项目 | 结果 |
|---|---:|
| initramfs 数量 | 1 |
| initramfs 大小 | 47,858,932 字节 |
| sysupgrade 数量 | 1 |
| sysupgrade 大小 | 45,814,032 字节 |
| 持久化内核大小 | 5,561,400 字节 |
| 内核上限 | 6,291,456 字节 |
| 内核剩余空间 | 730,056 字节 |
| 禁用包命中 | 0 |

镜像 SHA-256：

```text
BC949502751AE07777D41AE698CAA5989E663C416F8D31950FCC1E90167F63A8  athena-v19-initramfs-uImage.itb
BE34666629D59914AC78FCF0659C320801B67F4F3E11C5A4EF1658FFB15FF3FC  athena-v19-squashfs-sysupgrade.bin
```

修复后的检查器使用第 8 次真实镜像、manifest 和内核大小重新运行：

```text
PASS: firmware inspection
missing_packages: []
forbidden_packages: []
kernel_margin: 730056
```

## Artifact 兼容性问题

第 8 次 ZIP 同时包含 `firmware/SHA256SUMS` 和
`firmware/sha256sums`。两者只存在大小写差异，Windows 解压工具无法同时
创建，导致 Artifact 解压报错或覆盖。

修复后：

```text
firmware/SHA256SUMS
firmware/UPSTREAM_SHA256SUMS
```

新增测试会枚举 `firmware/` 下所有文件，并确保文件名经过
`casefold()` 后仍然唯一。

## 测试驱动验证

修复前新增的两个行为测试均失败：

- `nginx-ssl` 不能满足检查器的 Nginx 要求。
- 收集器没有生成 `UPSTREAM_SHA256SUMS`，且产生 Windows 名称冲突。

最小修复后：

- Python 单元/行为测试：28/28 通过。
- OpenWrt 运行时 Shell 测试：7/7 通过。
- Shell 静态语法检查：通过。
- 项目结构与不可变源码锁：通过。
- 敏感信息扫描：通过。
- DAED DNS、路由模板和域名列表：通过。
- OpenWrt 本地包布局：通过。
- Nginx、LuCI、DAED 反向代理和恢复入口：通过。
- `git diff --check`：通过。
- 第 8 次真实构建数据复检：通过。

## 未完成项目

- 修复后的源码尚未再次运行 GitHub Actions；下一次工作流应在
  `Inspect firmware` 和 `Collect artifact` 阶段都成功。
- 尚未在京东云雅典娜真机上启动本次 initramfs。
- 尚未验证独立 IoT SSID 对具体智能家居设备的兼容性。
- 尚未验证 sysupgrade；在 initramfs 真机测试通过前不得刷写。

## 下一次 GitHub Actions 参数

```text
Parallel jobs: 2
Runtime profile: stable
Artifact stage: test
```

预期关键结果：

```text
Build both images: success
Inspect firmware: success
Collect artifact: success
Enforce build result: success
```
