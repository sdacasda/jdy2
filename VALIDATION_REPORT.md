# Athena v19.0.0-rc1 验证报告

验证日期：2026-07-27

## 输入证据

### 第 6 次 GitHub Actions

用户提供的完整步骤截图确认：

- 有效 OpenWrt 配置生成成功。
- 有效配置验证成功。
- 两个固件镜像的编译步骤成功，耗时约 3 小时 47 分钟。
- 固件检查步骤成功。
- 产物收集步骤报告 `Expected one initramfs, found 0`。
- 上传步骤因 `Athena-AX6600-v19-6` 中没有文件而跳过。

这证明包注册和固件编译问题已经越过。失败边界位于检查器向收集器传递已验证
镜像路径的过程，而不是 LiBwrt 编译过程。

### 第 5 次 GitHub Actions

检查了用户提供的 `Athena-AX6600-v19-5-test.zip`：

- SHA-256：
  `5A15E7D2F3AF671F14DAF93186FD63A46BEF9B2F268D2737D3540C3623A8FB4D`
- `athena-runtime` 已进入合并后的 `tmp/.packageinfo`。
- `luci-app-athena` 没有进入合并后的 `tmp/.packageinfo`。
- `athena-runtime` 已进入实际 `tmp/.config-package.in`。
- 该 Kconfig 符号包含：
  `depends on !(PACKAGE_TAR_XZ) || PACKAGE_xz-utils`。
- 有效配置为 `CONFIG_PACKAGE_TAR_XZ=y`，但
  `CONFIG_PACKAGE_xz-utils` 未选择。

由此确认：

1. `athena-runtime` 在 Kconfig 阶段因 GNU tar 的传递条件被隐藏。
2. `luci-app-athena` 在更早的包扫描阶段因缺少源码扫描签名而丢失。

## 反事实元数据验证

使用锁定的 LiBwrt 源码和第 5 次 Artifact 的完整包元数据，执行了以下验证：

- 删除运行时包的 `+tar +gzip` 后重新生成完整 Kconfig。
- 加入修复后的 LuCI 包元数据。
- 确认 `PACKAGE_athena-runtime` 和 `PACKAGE_luci-app-athena` 均可见。
- 确认运行时包不再带有 `TAR_XZ/xz-utils` 条件。
- 确认 LuCI 包正确选择 `athena-runtime` 与 Web 界面依赖。
- 确认其余平台条件在有效配置中满足：
  Linux 6.12、IPv6、firewall4。

## 测试驱动验证

针对第 6 次失败，先加入两个真实脚本行为测试并确认修复前失败：

- 检查报告给出两个有效镜像时，旧收集器仍重新按文件名搜索并报告 0。
- 收集失败后，旧收集器没有留下检查报告或错误文件。

修复后两个测试均通过。测试没有伪造 `find` 输出，而是直接运行真实
`collect_output.sh`，验证最终文件和失败副作用。

此前的包注册修复也遵循同样的失败—修复—通过流程：

修复前先加入回归测试并确认它们因以下原因失败：

- LuCI 包缺少 OpenWrt 扫描签名。
- Runtime 包包含多余的 `+tar +gzip` 依赖。
- 诊断脚本对标准 Kconfig 前导空白处理错误。

修复后，上述测试全部通过。

## 已通过

- Python 测试：26/26
- OpenWrt 运行时 Shell 测试：7/7
- 所有项目 Shell 脚本与运行时命令静态语法检查
- 项目结构与不可变源码锁验证
- DAED DNS、路由模板与域名列表验证
- OpenWrt 本地包布局验证
- Nginx、LuCI、DAED 反向代理与恢复入口配置验证
- 敏感信息扫描
- 完整包元数据反事实 Kconfig 验证
- 检查报告到 Artifact 的镜像路径交接测试
- 收集失败的诊断保留测试
- `git diff --check`

## 尚未完成

- Windows 本机不具备 OpenWrt 要求的区分大小写 Linux 文件系统和完整 Ubuntu
  构建环境，因此未执行完整 LiBwrt 固件编译。
- 尚未生成或真机测试新的 initramfs/sysupgrade 镜像。
- 第 6 次 GitHub Actions 已完成固件编译，但尚未验证修复后的 Artifact
  收集流程。

## 下一次 GitHub Actions 验收

使用：

```text
Parallel jobs: 2
Runtime profile: stable
Artifact stage: test
```

预期配置、编译和检查继续通过，随后 `Collect artifact` 应复用
`inspection/firmware-inspection.json` 中的两个镜像路径并上传 Artifact。
若仍失败，新的输出目录也会包含检查报告和
`ARTIFACT_COLLECTION_ERROR.txt`，不会再出现零证据失败。

即使云端编译成功，也必须先从 U-Boot 测试 initramfs。只有基础网络、2.4 GHz
IoT SSID、三路无线、Argon、DAED 面板及恢复入口验证通过后，才考虑刷写
sysupgrade。
