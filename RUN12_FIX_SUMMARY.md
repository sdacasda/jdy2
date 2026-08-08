# GitHub Actions 第 12 次构建修复说明

日期：2026-08-08

## 根因

第 12 次构建已经通过项目、OpenWrt 配置和包选择检查。真正失败发生在 `package/custom/daed` 下载源码时：

```text
daed-src-2026.07.26-ecbc5c99d632.tar.gz
HTTP 404
ERROR: package/custom/daed failed to build
```

锁定的 `openwrt-daede` 提交仍引用该文件，但上游 `daed-src` Release 会清理旧资产，因此“Git 提交不可变”并没有保证其外部 Release 文件永久存在。随后出现的：

```text
Expected one initramfs, found 0
```

只是 DAED 包失败、固件未完成后的收集阶段结果。

## 修复

- 新增 `scripts/assemble_daed_source.sh`，读取锁定 DAED 仓库中的 `ci/pins.env`。
- 从不可变提交组装 DAED、dae-wing、dae-core、outbound 和 quic-go。
- 在 `pnpm build` 前应用 DAED 同源 GraphQL 修补，确认编译结果包含 `/athena-daed/graphql`。
- 使用规范化 tar/gzip 参数生成本地源码包。
- 新增 `scripts/install_daed_source.py`，把源码包复制到 OpenWrt `dl/`，并把实际 SHA-256 写入 DAED Makefile。
- 完整编译前运行 `make -C openwrt package/daed/download V=s`，单独确认名称和哈希被 OpenWrt 接受。
- 使用 assembly manifest 将缓存归档绑定到全部组件 pins、SHA-256、大小和源码根目录，并逐次检查源码及已编译 Web 的同源端点；缓存异常时自动重建。
- 在 DAED 下载预检成功后立即保存 GitHub Actions Cache，使后续固件编译失败也不会丢失已验证的组装结果。
- Artifact 保存 pins、源码包哈希、文件清单、组装日志和 OpenWrt 下载校验日志。

## 已完成的本地验证

- 72 项 Python 测试通过。
- 9 组 BusyBox/OpenWrt 运行时测试通过。
- 仪表盘 JavaScript 测试通过。
- 项目、模板、包布局、Web 配置和凭据扫描通过。
- 新增测试覆盖本地归档安装、哈希写回、不可变提交校验、前端修补顺序、缓存 manifest、压缩 Web 资源、归档结构和工作流前置门槛。
- Shell 与 Python 语法、工作流 YAML 解析、Git 补丁格式通过。

## 仍需验证

本地 Windows 环境没有 Go 1.26/Linux OpenWrt 完整工具链，因此没有在本机执行真实 DAED 组装和 LiBwrt 全量编译。上传新源码后，下一次 GitHub Actions 应先通过 `Assemble pinned DAED source`，再进入完整固件编译。只有绿色构建生成的新 initramfs 才可用于 RAM 启动测试；不要使用第 12 次的诊断 ZIP 刷机。
