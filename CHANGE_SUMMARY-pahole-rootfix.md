# Athena v19.0.0-rc1 变更摘要

## 本次：修复 `vmlinux-btf` 编译失败

第 7 次 GitHub Actions 的完整日志证明，固件没有成功生成。真正的首个包级错误是：

```text
pahole --jobs=1 --btf_encode_detached=.../vmlinux-btf .../vmlinux
bash: line 1: pahole: command not found
ERROR: package/custom/vmlinux-btf failed to build.
```

`Collect artifact` 报告的：

```text
Expected one initramfs, found 0
```

只是编译失败后的结果，不是镜像文件名或收集规则导致的根因。

本次修复：

- GitHub Actions 的 Ubuntu 22.04 构建依赖新增 `pahole`。
- 安装依赖后立即执行 `command -v pahole` 和 `pahole --version`。
- 缺少 BTF 主机工具时会在编译前快速失败，不再浪费约四小时。
- 新增工作流回归测试，强制要求安装并验证 `pahole`。
- Artifact 收集器在失败时保留完整 `build.log`。
- Artifact 额外生成 `diagnostics/build-error-summary.txt`，提取缺少命令、
  编译错误、失败包和 Make 错误。
- 新增行为测试，确认失败 Artifact 仍保留检查报告、目标目录清单、
  完整构建日志、错误摘要和明确的收集错误。

完整日志只出现一个包级失败：

```text
package/custom/vmlinux-btf
```

没有发现第二个并行编译包失败。日志中的若干 CMake/Autoconf “not found” 和
被标记为 ignored 的错误属于能力探测或允许失败的清理步骤。

## 此前已修复

### OpenWrt 本地包注册

- 删除 `athena-runtime` 不需要的 `+tar +gzip` 依赖，避免 Kconfig 因
  `TAR_XZ/xz-utils` 传递条件隐藏该包。
- 为 `luci-app-athena` 增加 OpenWrt 包扫描签名。
- 新增包注册前后诊断和对应回归测试。

### 固件检查与 Artifact 交接

- `firmware-inspection.json` 作为检查器与收集器之间的镜像路径数据源。
- 收集器复用检查阶段已验证的 initramfs 与 sysupgrade 路径。
- 无检查报告时使用 `find -L` 作为手动运行兼容回退。
- 成功与失败路径都保留可审计的诊断证据。

## 保持不变

- LAN：`192.168.50.1`
- DAED 默认关闭，仅监听 `127.0.0.1:2023`
- Argon 默认深色并保留配置能力
- DAED 通过同源反向代理嵌入 LuCI
- 不内置 SmartDNS
- 国内直连、国外代理
- 国内 UDP DNS、国外经代理 DoH、节点 bootstrap 直连
- Steam 下载、游戏和 BT 选择性直连
- 保留 NSS/Wi-Fi offload，停止 ECM frontend 和 flow offload
- 独立 2.4 GHz IoT SSID
- 提供 `athena-setup`、`athena-health`、`athena-backup`、
  `athena-rollback`、`athena-runtime`

## 当前状态

本地静态检查和行为测试已通过。Windows 本机不能完成 LiBwrt 的完整 Linux
固件编译，因此必须再次运行 GitHub Actions 验证 `pahole` 修复后的云端构建。
在 initramfs 真机测试通过前，不应刷写 sysupgrade。
