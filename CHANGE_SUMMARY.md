# Athena v19.0.0-rc1 变更摘要

## 本次：修复成功编译后的产物收集

第 6 次 GitHub Actions 已经通过：

```text
Generate effective OpenWrt config
Verify effective OpenWrt config
Build both images
Inspect firmware
```

完整编译耗时约 3 小时 47 分钟。失败只发生在 `Collect artifact`：

```text
Expected one initramfs, found 0
```

`Inspect firmware` 已经以相同设备规则验证了唯一的 initramfs 与 sysupgrade，
但旧收集器没有复用检查结果，而是通过 Bash `find -type f` 再独立发现一次镜像。
两套发现逻辑产生分歧后，收集器退出；因为输出目录当时只有空目录，
`upload-artifact` 最终也没有任何文件可以上传。

本次调整：

- `firmware-inspection.json` 成为检查和收集之间的唯一镜像路径数据源。
- 收集器直接复制检查阶段已经验证的 initramfs 与 sysupgrade。
- 仅在没有检查报告时使用 `find -L` 作为手动运行的兼容回退。
- 严格校验报告中的路径仍然存在且可读取。
- 在严格校验之前保存检查报告。
- 收集失败时写入 `ARTIFACT_COLLECTION_ERROR.txt`，确保 GitHub 始终能上传证据。
- 成功收集时同时保存 `build.log`、检查报告与内核尺寸报告。
- 新增两个行为回归测试：
  - 收集器复用检查器验证的非默认镜像路径。
  - 收集失败仍保留可上传的诊断证据。

## 前一项：修复 OpenWrt 本地包注册

第 5 次 GitHub Actions Artifact 已经提供了完整证据，本次修复两个相互独立的根因。

### 1. `athena-runtime` 被 Kconfig 隐藏

运行时包原先显式依赖：

```text
+tar +gzip
```

LiBwrt 中 `tar` 包在启用 `CONFIG_PACKAGE_TAR_XZ=y` 时还要求
`CONFIG_PACKAGE_xz-utils=y`。当前有效配置没有选择 `xz-utils`，因此
`athena-runtime` 在 `make defconfig` 阶段不可见并被移除。

Athena 的备份和回滚脚本只使用 OpenWrt BusyBox 已提供的
`tar -czf`、`tar -xzf`，不需要 GNU tar/gzip 包。本次删除这两个多余依赖，
保留 `jshn`、`jsonfilter`、`rpcd`、`ucode`、`curl` 和 `ca-bundle`。

### 2. `luci-app-athena` 没有进入包扫描

OpenWrt 的包扫描器先通过源码文本寻找 `BuildPackage` 等签名，再决定是否扫描
Makefile。LuCI 包缺少标准扫描标记，所以即使 Makefile 可单独输出合法元数据，
也不会进入合并后的 `tmp/.packageinfo`。

本次加入 LuCI 标准签名：

```make
# call BuildPackage - OpenWrt buildroot signature
```

### 3. 加强回归保护与诊断

- 包布局检查现在会拒绝缺少 OpenWrt 扫描签名的 LuCI 包。
- 包布局检查现在会拒绝运行时包重新引入可选 GNU `tar`/`gzip` 依赖。
- 包注册诊断使用 OpenWrt `package-metadata.pl config FILE` 的真实调用方式。
- Kconfig 符号检查允许标准的前导空白，避免诊断报告误报。
- 新增行为测试，覆盖以上两个根因以及诊断脚本。

## 保持不变

- LAN：`192.168.50.1`
- DAED 默认关闭，仅监听 `127.0.0.1:2023`
- Argon 默认深色并保留配置能力
- 不内置 SmartDNS
- 国内直连、国外代理
- 国内 UDP DNS、国外经代理 DoH、节点 bootstrap 直连
- Steam 下载、游戏和 BT 选择性直连
- 保留 NSS/Wi-Fi offload，停止 ECM frontend 和 flow offload
- 独立 2.4 GHz IoT SSID
- 提供 `athena-setup`、`athena-health`、`athena-backup`、
  `athena-rollback`、`athena-runtime`

## 重要说明

本次已经在本地完成静态检查、行为测试和完整包元数据反事实验证，但 Windows
环境不能完成 LiBwrt 的 Linux 固件编译。下一次 GitHub Actions 运行仍是最终
云端验证；在 initramfs 真机测试通过前，不应刷写 sysupgrade。
