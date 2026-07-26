# Athena v19.0.0-rc1 变更摘要

## 本次：OpenWrt 包注册诊断

GitHub Actions 第四次构建的 Artifact 已证明：

- `athena-runtime` 已进入 OpenWrt 合并后的 `tmp/.packageinfo`。
- 源配置已选择 `CONFIG_PACKAGE_athena-runtime=y` 和
  `CONFIG_PACKAGE_luci-app-athena=y`。
- `make defconfig` 后两个选项均从有效配置中消失。
- `athena-runtime` 的直接与传递依赖可以正常生成 Kconfig，
  没有发现会隐藏该包的依赖条件。

因此，故障已缩小到 OpenWrt 从包元数据生成 Kconfig，以及 Kconfig
解析源配置的边界。上一份 Artifact 没有保存实际使用的
`tmp/.config-package.in`，无法再从现有材料判断是哪一侧丢失。

本次增加：

- 在 `defconfig` 前显式执行并完成 `prepare-tmpinfo`。
- 在 `defconfig` 前后分别保存：
  - 完整 `tmp/.packageinfo`
  - 实际 `tmp/.config-package.in`
  - 由同一份 `.packageinfo` 重新计算的 Kconfig
  - Athena 两个本地包的独立扫描元数据
  - 当时的 `.config`
- 生成简短的 `registration-summary.txt`，直接显示两个包在每一层是否存在。
- 无论构建成功或失败，都把上述文件放入 GitHub Artifact。
- 新增行为回归测试，验证“实际 Kconfig 与重新计算结果不一致”时证据不会丢失。

这是一版有明确目的的诊断构建，不宣称已经通过完整云端固件编译。
下一次 GitHub Actions 运行会直接确认最终根因；如果显式
`prepare-tmpinfo` 同时消除了时序问题，构建也会继续进入固件编译。

## 保持不变

- LAN：`192.168.50.1`
- DAED 默认关闭，仅监听 `127.0.0.1:2023`
- Argon 默认深色并保留配置能力
- 不内置 SmartDNS
- 国内直连、国外代理
- 国内 UDP DNS、国外代理 DoH、节点 bootstrap 直连
- Steam 下载、游戏与 BT 选择性直连
- 保留 NSS 与 Wi-Fi offload，停止 ECM frontend 和 flow offload
- 独立 2.4 GHz IoT SSID
- `athena-setup`、`athena-health`、`athena-backup`、
  `athena-rollback`、`athena-runtime`
