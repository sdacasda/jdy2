# Audit

v19 构建输入全部锁定至完整提交 SHA。CI 执行单元测试、运行时脚本测试、模板验证、包布局、Web 配置、安全扫描、有效配置检查和固件产物检查。

安全扫描拒绝公开节点链接、Token、私钥、Wi-Fi 密码等凭据。DAED 数据库和私人配置不进入 Artifact。缺少 initramfs/sysupgrade、内核超过 6 MiB、必需包缺失或禁用包出现都会使构建失败。
