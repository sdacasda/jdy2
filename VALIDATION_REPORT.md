# Athena v19.0.0-rc1 验证报告

验证日期：2026-07-27

## 本次输入证据

检查了用户提供的 `Athena-AX6600-v19-4-test.zip`：

- SHA-256：
  `9C9FECDF69A8EF8409133CFA917F530B1C0CD63BE8FF8F3C6F2F90DC51FF4096`
- Artifact 中的 `athena-runtime-packageinfo.txt` 证明包扫描成功。
- `seed.config` 选择了两个 Athena 本地包。
- `effective.config` 中两个选项完全消失。
- `curl`、`gzip` 等可选依赖也未被选中，与运行时包没有进入最终
  Kconfig 解析结果相符。

另外以锁定的 LiBwrt 源码和相同本地包做了元数据级验证：

- `athena-runtime` Makefile 可独立输出合法包元数据。
- `luci-app-athena` Makefile 可独立输出合法包元数据。
- 从 `athena-runtime` 及其依赖生成的 Kconfig 中，该选项为可见
  `tristate`，没有额外 `depends on` 限制。
- 已检查已锁定 feeds，没有发现第二个同名 `athena-runtime` 包。

## 已通过

- Python 测试：22/22
- OpenWrt 运行时 Shell 测试：7/7
- 所有项目 Shell 脚本与运行时命令静态语法检查
- 项目结构与不可变源码锁验证
- DAED DNS、路由模板与域名列表验证
- 本地 OpenWrt 包布局验证
- Nginx、LuCI、DAED 反向代理与恢复入口配置验证
- 敏感信息扫描
- 包注册诊断脚本的行为回归测试
- `git diff --check`

## 尚未完成

- Windows 本机无法提供 OpenWrt 所要求的区分大小写 Linux
  文件系统和完整 Ubuntu 构建依赖，因此未在本机执行完整 LiBwrt
  固件编译。
- 本次新增的 `prepare-tmpinfo` 显式步骤及完整诊断采集仍需
  GitHub Actions 的 Ubuntu 22.04 环境验证。
- 尚未生成或真机测试新的 initramfs/sysupgrade 镜像。

## 下一次构建如何判断

下载新的 GitHub Artifact，查看：

```text
diagnostics/package-registration/pre-defconfig/registration-summary.txt
diagnostics/package-registration/post-defconfig/registration-summary.txt
```

判断：

- `actual ... present` 且最终配置仍缺失：问题位于 Kconfig 解析阶段。
- `actual ... missing`、`recomputed ... present`：OpenWrt 使用了过期或
  不完整的 `.config-package.in`。
- 两处均 `present` 且构建继续：显式元数据准备消除了原来的时序问题。

在 GitHub 完整构建和 initramfs 真机验证通过前，不应刷写 sysupgrade。
