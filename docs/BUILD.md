# 构建

运行 GitHub Actions 工作流 `Build Athena AX6600 DAED v19`。建议首次使用 `compile_jobs=2`、`build_profile=stable`、`release_stage=test`。

构建输入来自 `SOURCES.lock.json`，工作流不会自动创建 Release。Artifact 必须同时包含 initramfs 与 sysupgrade。先运行 `tools/verify_checksums.sh` 校验。

GitHub 云端构建才是完整编译环境；本地静态检查不等于固件已成功编译。

外置 BTF 生成依赖主机命令 `pahole`。GitHub Actions 会安装并在编译前验证它；
自行准备 Ubuntu 22.04 构建环境时也必须安装 `pahole`。

构建失败时下载诊断 Artifact，优先查看：

```text
diagnostics/build-error-summary.txt
diagnostics/step-outcomes.txt
diagnostics/ARTIFACT_COLLECTION_ERROR.txt
```

需要完整上下文时再查看 `diagnostics/build.log`。
