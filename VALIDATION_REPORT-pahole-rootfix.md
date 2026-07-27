# Athena v19.0.0-rc1 验证报告

验证日期：2026-07-27

## 输入证据

### 第 7 次 GitHub Actions 完整日志

用户提供：

```text
logs_81907503319.zip
```

SHA-256：

```text
F5E824A9CA8EB125D71B5DDB408CC65FBBC91B48591229C0BF723533E8A5AD8D
```

日志显示以下步骤成功：

- 源码项目验证
- 构建依赖安装
- 锁定 LiBwrt 源码检出
- Feeds 和锁定包准备
- 有效 OpenWrt 配置生成
- 有效配置验证

`Build both images` 在运行约四小时后失败。关键日志：

```text
pahole --jobs=1 --btf_encode_detached=.../vmlinux-btf .../vmlinux
bash: line 1: pahole: command not found
make[3]: *** [.../.built] Error 127
ERROR: package/custom/vmlinux-btf failed to build.
make[2]: *** [package/Makefile:198: package/custom/vmlinux-btf/compile] Error 1
```

随后没有生成 initramfs 或 sysupgrade，因此：

- `Inspect firmware` 失败。
- `Collect artifact` 报告 `Expected one initramfs, found 0`。
- 第 7 次 Artifact 只有诊断文件，没有固件。

对 51 MB 编译日志逐行扫描后，只发现一个：

```text
ERROR: package/... failed to build
```

对应 `package/custom/vmlinux-btf`。其他 `not found` 多数为 CMake/Autoconf
能力探测；其他明确标记为 ignored 的 Make 错误不构成本次失败。

## 根因

锁定的 `vmlinux-btf` 包直接调用主机命令：

```text
pahole --jobs=1 --btf_encode_detached=...
```

工作流的 Ubuntu 依赖列表没有安装 `pahole`。因此内核已链接完成，但外置 BTF
生成阶段以退出码 127 失败。

## 修复

工作流现在：

```text
apt-get install ... pahole
command -v pahole
pahole --version
```

Ubuntu 22.04 的官方软件仓库提供 `pahole`，当前 Runner 日志也确认
`jammy-updates/universe` 已启用。

同时增强失败诊断：

- 复制完整 `build.log` 到 Artifact。
- 生成 `diagnostics/build-error-summary.txt`。
- 保留 `firmware-inspection.json`、目标目录清单、
  `ARTIFACT_COLLECTION_ERROR.txt` 和步骤结果。

## 测试驱动验证

### `pahole` 依赖

先加入回归测试，要求工作流同时：

- 安装 `pahole`
- 执行 `command -v pahole`

修复前测试失败，修复后通过。

### 失败 Artifact 诊断

先让行为测试使用真实 `collect_output.sh` 模拟：

```text
pahole: command not found
ERROR: package/custom/vmlinux-btf failed to build.
```

测试要求失败后仍生成错误摘要并保留完整日志。修复前缺少摘要文件而失败，
修复后通过。

### 此前的回归保护

- `athena-runtime` 不再引入多余 GNU `tar`/`gzip` 依赖。
- `luci-app-athena` 包含 OpenWrt 扫描签名。
- 包注册诊断可捕获陈旧 Kconfig。
- 检查器与收集器共享已经验证的镜像路径。

## 已通过

- Python 测试：27/27
- OpenWrt 运行时 Shell 测试：7/7
- Shell 静态语法：30 个文件，0 失败
- 项目结构与不可变源码锁验证
- DAED DNS、路由模板与域名列表验证
- OpenWrt 本地包布局验证
- Nginx、LuCI、DAED 反向代理与恢复入口配置验证
- 敏感信息扫描
- Artifact 成功与失败路径行为测试
- `git diff --check`

## 尚未完成

- Windows 本机不具备完整 Ubuntu/OpenWrt 构建环境，未重新编译固件。
- 修复后的 GitHub Actions 云端完整构建尚未执行。
- 尚未生成并真机验证新的 initramfs/sysupgrade。
- 本机未安装 `actionlint`/`yamllint`；工作流已被此前 GitHub Actions 正常解析，
  本次工作流改动另有回归测试保护。

## 下一次 GitHub Actions 验收

建议：

```text
Parallel jobs: 2
Runtime profile: stable
Artifact stage: test
```

预期在 `Install build dependencies` 中看到：

```text
/usr/bin/pahole
v1.25
```

版本号可能随 Ubuntu 更新变化，但命令必须存在。

成功条件：

- `Build both images` 为 success。
- `Inspect firmware` 为 success。
- `Collect artifact` 为 success。
- Artifact 同时包含 initramfs、sysupgrade、校验和与诊断文件。

即使云端构建成功，也必须先从 U-Boot 测试 initramfs。只有基础网络、独立
2.4 GHz IoT SSID、三路无线、Argon、DAED 面板和恢复入口验证通过后，才考虑
刷写 sysupgrade。
