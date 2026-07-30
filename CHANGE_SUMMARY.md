# Athena v19.0.0-rc1 变更摘要

## 现代化只读实时仪表盘

- 新增只读 `athena.dashboard` RPC，以固定 JSON 结构提供系统、CPU、内存、WAN、温度、无线、DAED 和加速状态。
- LuCI“状态 → 概况”和“Athena 优化 → 状态”统一进入新的 Argon 兼容仪表盘。
- 新增 WAN、CPU/内存和温度 SVG 曲线；3 秒采样，浏览器内最多 200 点，不写闪存。
- 新增 DAED eBPF 不兼容、时间未同步、WAN、DNS、无线和温度告警。
- 页面不包含外部 CDN、远程遥测、配置写入或凭据返回。
- 构建前源码布局检查和构建后 rootfs 检查均强制要求所有仪表盘资源存在。
- 保留 DAED 默认关闭、`127.0.0.1:2023` 同源代理、`192.168.50.1:8080` 恢复入口、NSS/Wi-Fi offload 与 ECM/Flow Offload 策略。

## 第 9 次 Artifact 补充修复

第 9 次工作流已经全绿，固件检查、编译和 Artifact 收集均成功。下载后的
Artifact 仍暴露出一个纯打包问题：

- `SHA256SUMS.txt` 包含 16 个以 `.` 开头的包注册诊断文件；
- `actions/upload-artifact` 默认不上传隐藏文件；
- 因此总校验会报告这些诊断文件缺失；
- `firmware/SHA256SUMS` 以及两个固件本体校验不受影响，均已通过。

工作流现已为 Artifact 上传启用：

```yaml
include-hidden-files: true
```

并新增回归测试，确保总校验清单中记录的隐藏诊断文件能够随 Artifact 一起
上传。

## 第 8 次云构建结论

第 8 次 GitHub Actions 已成功完成固件编译，两个目标镜像都已生成：

- `athena-v19-initramfs-uImage.itb`：47,858,932 字节
- `athena-v19-squashfs-sysupgrade.bin`：45,814,032 字节

工作流最终失败并非编译失败，而是编译后的固件检查器要求包名必须为
`nginx`。本项目实际、合法地使用 `nginx-ssl`，同时还有 `luci-nginx`、
`nginx-mod-luci` 和 `nginx-mod-ubus`。因此检查器产生了假失败。

第 8 次 Artifact 还同时包含：

```text
firmware/SHA256SUMS
firmware/sha256sums
```

Windows 文件系统不区分大小写，解压时这两个文件会发生冲突。

## 本次修复

- 固件检查器现在接受 `nginx` 或 `nginx-ssl` 作为 Nginx 运行时。
- 仍然严格要求 DAED、LuCI、Argon、Athena 运行时和恢复 Web 服务等包。
- 上游的 `sha256sums` 改名保存为 `UPSTREAM_SHA256SUMS`。
- 项目生成的固件校验文件继续使用 `SHA256SUMS`。
- 新增真实行为测试，覆盖 Nginx 包名兼容和 Windows 文件名冲突。
- 用第 8 次真实镜像、manifest 和内核大小重新执行修复后的检查器，结果通过。

## 此前已完成

- 安装并预检 `pahole`，修复外置 BTF 生成失败。
- 修复 `athena-runtime` 和 `luci-app-athena` 的 OpenWrt 包注册。
- 收集器复用检查器已经确认的镜像路径。
- 失败 Artifact 保留完整构建日志、错误摘要、包注册状态和目标目录清单。
- 独立 2.4 GHz IoT SSID，兼容只支持 WPA2/AES 的智能家居设备。
- LAN 固定为 `192.168.50.1`，DAED 默认关闭。
- Argon 默认深色并保留配置能力。
- DAED 仅监听 `127.0.0.1:2023`，通过同源反向代理嵌入 LuCI。
- 不内置 SmartDNS；国内 UDP DNS、国外经代理 DoH、节点 bootstrap 直连。
- Steam 下载、游戏和 BT 选择性直连。
- 保留 NSS/Wi-Fi offload，停止 ECM frontend 和 flow offload。
- 提供 `athena-setup`、`athena-health`、`athena-backup`、
  `athena-rollback` 和 `athena-runtime`。

## 安全提示

云端编译和离线检查已经通过，不等于真机验证完成。必须先从 U-Boot 启动
initramfs，验证基础网络、三路无线、IoT SSID、Argon、DAED 面板和恢复入口。
只有 initramfs 验证通过后，才能考虑写入 sysupgrade。
