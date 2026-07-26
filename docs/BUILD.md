# 构建

运行 GitHub Actions 工作流 `Build Athena AX6600 DAED v19`。建议首次使用 `compile_jobs=2`、`build_profile=stable`、`release_stage=test`。

构建输入来自 `SOURCES.lock.json`，工作流不会自动创建 Release。Artifact 必须同时包含 initramfs 与 sysupgrade。先运行 `tools/verify_checksums.sh` 校验。

GitHub 云端构建才是完整编译环境；本地静态检查不等于固件已成功编译。
