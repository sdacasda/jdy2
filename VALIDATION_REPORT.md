# Athena v19.0.0-rc1 验证报告

验证日期：2026-07-26

## 已通过

- Python 单元测试：17/17
- OpenWrt 运行时 Shell 测试：7/7
- 所有项目 Shell 脚本与运行时命令静态语法检查
- 项目结构与不可变源码锁检查
- DAED DNS/路由模板与域名列表验证
- 本地 OpenWrt 包布局验证
- Nginx、LuCI、DAED 环回代理与恢复入口配置验证
- 敏感信息扫描
- v19 固件 seed 配置与禁用包检查
- Git 工作树清洁性与脚本可执行权限检查
- Windows/GitHub 上传丢失可执行位的恢复测试

## 未在本机完成

- 未执行完整 LiBwrt/OpenWrt 编译。该步骤需要 Ubuntu 22.04 GitHub Actions 环境，预计耗时数小时。
- 未生成或验证真实 initramfs/sysupgrade 二进制；工作流会在缺少任一镜像、内核超过 6 MiB、必需包缺失或禁用包出现时失败。
- 未在 RE-CS-02 真机验证三路 Wi-Fi、NSS、DAED 代理、8080 恢复入口和独立 IoT SSID。
- 未用真实智能家居完成关联、DHCP、长期在线与重连测试。

这些未完成项是发布 `v19.0.0` 前的硬门槛。当前源码适合作为 `v19.0.0-rc1` 上传并运行 test Artifact 构建，不应在未测试 initramfs 的情况下直接刷写 sysupgrade。

## 已知设计取舍

- DAED 原计划标签 `v2026.07.09` 已不存在；锁定文件改用可验证的 `v2026.07.26` 对应提交。
- SmartDNS 不内置，DNS 分流由 DAED 单独承担。
- ECM L3/L4 frontend 与 Flow Offload 停止，但 NSS 数据面及 Wi-Fi offload 保留。
- IoT SSID 加入现有 LAN，不启用客户端隔离或独立 VLAN，以兼容局域网发现和控制。

## RC1 工作流修订

首次公开构建在 `Validate source project` 阶段暴露出 Windows/GitHub 上传将脚本保存为 `100644` 的平台差异。工作流现在会在测试前恢复执行权限，OpenWrt 包安装阶段也会强制把运行时命令设置为 `0755`。前置校验失败时，Artifact 收集会生成明确诊断文件，不再因缺少 `openwrt` 目录产生第二个无关错误。
