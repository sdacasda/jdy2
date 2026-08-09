# Athena v19 第 13 次构建修复摘要

日期：2026-08-09

## 结论

第 13 次运行并非编译失败。GitHub Actions 已成功：

- 从固定组件提交组装 DAED 源码；
- 编译自定义 DAED 与两个 OpenWrt 镜像；
- 校验编译后的 DAED 来源；
- 生成 initramfs 与 sysupgrade Artifact。

最后失败的是固件离线检查器。DAED Web 的大文件在嵌入二进制前会被 gzip 压缩，旧检查器只在 ELF 明文中搜索 `/athena-daed/graphql`，因此把正确固件误报为缺少同源端点。

## 修复

- 检查器现在会查找有效 gzip 成员，以 32 MiB 上限有界解压后检查端点。
- 同源 `/athena-daed/graphql` 在压缩资源中会通过。
- 浏览器直连 `:2023/graphql` 在压缩资源中仍会失败。
- `actions/setup-go` 关闭无效的根目录模块缓存，消除缺少根目录 `go.mod` 的警告。
- 项目的 DAED 源码归档缓存保持启用并继续执行 manifest、提交号、SHA-256 与嵌入 Web 校验。

## 第 13 次 Artifact 证据

- initramfs：恰好 1 个；
- sysupgrade：恰好 1 个；
- 内核大小：5,561,400 字节；
- 6 MiB 槽位余量：730,056 字节；
- 缺少必需包：0；
- 命中禁止包：0；
- 仪表盘缺失文件：0；
- 唯一失败项：旧检查器报告 `daed-binary-same-origin-endpoint` 缺失。

## 使用要求

上传本次修复源码后重新运行 `stable / test`。只有新的运行全绿后，才下载新的 initramfs 进行 U-Boot 内存启动验证。第 13 次镜像虽然已生成，但不建议绕过红色 CI 直接刷写；在 initramfs 真机验证全部通过前禁止 sysupgrade。
