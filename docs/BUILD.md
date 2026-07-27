# 构建

在 GitHub Actions 中运行 `Build Athena AX6600 DAED v19`，建议参数：

```text
Parallel jobs: 2
Runtime profile: stable
Artifact stage: test
```

工作流不会自动创建 Release。源码输入由 `SOURCES.lock.json` 固定，构建前会
验证 `pahole`、OpenWrt 包注册、有效配置和模板安全性。

成功构建必须满足：

- initramfs 恰好 1 个；
- sysupgrade 恰好 1 个；
- 持久化内核不超过 6 MiB；
- 必需包全部存在，其中 Nginx 运行时允许 `nginx` 或 `nginx-ssl`；
- SmartDNS、OpenClash、PassWall 和 HomeProxy 不存在；
- Artifact 中不存在 Windows 大小写文件名冲突。

Artifact 中优先查看：

```text
firmware/SHA256SUMS
firmware/UPSTREAM_SHA256SUMS
diagnostics/firmware-inspection.json
diagnostics/kernel-size.txt
diagnostics/step-outcomes.txt
```

失败时再查看：

```text
diagnostics/build-error-summary.txt
diagnostics/ARTIFACT_COLLECTION_ERROR.txt
diagnostics/build.log
diagnostics/package-registration/
```

完整云端构建成功后仍必须先测试 initramfs。只有基础网络、三路无线、独立
2.4 GHz IoT SSID、Argon、DAED 面板和恢复入口都通过，才能考虑刷写
sysupgrade。
