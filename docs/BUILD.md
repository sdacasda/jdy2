# 构建说明

在 GitHub Actions 中运行 `Build Athena AX6600 DAED v19`，建议参数：

```text
Parallel jobs: 2
Runtime profile: stable
Artifact stage: test
```

工作流不会自动创建 Release。源码输入由 `SOURCES.lock.json` 固定，构建前会执行 Python、JavaScript、运行时脚本、模板、包布局、Web 配置和敏感信息检查。

## 成功门槛

- initramfs 与 sysupgrade 各恰好一个。
- 持久化内核不超过 6 MiB。
- 锁定的 DAED 版本已注册并从 `package/custom/daed` 编译。
- Argon、Nginx、uHTTPd Lua、Athena 运行时与 LuCI 应用均存在。
- DAED 二进制使用 `/athena-daed/graphql`，不包含活动的浏览器端 `:2023/graphql`。
- `athena-daed.locations` 存在，旧 `athena-daed.conf` 不存在。
- SmartDNS、OpenClash、PassWall 和 HomeProxy 不存在。

## Artifact 重点文件

```text
firmware/SHA256SUMS
diagnostics/firmware-inspection.json
diagnostics/kernel-size.txt
diagnostics/step-outcomes.txt
diagnostics/daed-provenance/
tools/verify-after-flash.sh
docs/WEB_RECOVERY.md
```

云端构建成功后仍必须先测试 initramfs。若 `firmware-inspection.json` 的 `web_integration` 存在任何 `missing` 或 `forbidden` 项，不得刷写。
