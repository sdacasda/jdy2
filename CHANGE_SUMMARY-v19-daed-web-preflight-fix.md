# Athena v19 DAED Web 源码预检修复摘要

## 问题定位

第 24 次 GitHub Actions 构建没有进入 OpenWrt 编译阶段。`Assemble pinned DAED source` 已成功完成 5 个前端构建任务，随后被 DAED Web 安全预检拒绝：

```text
DAED source cache validation failed: embedded Web bundle contains unsafe login error content
```

根因是预检对整个生产前端 bundle 搜索 `ClientError`、`request.variables`、`request.body` 和 `console.*`。这些标识符会正常存在于 GraphQL 客户端依赖中，仅凭出现不能证明登录错误或密码会显示到浏览器。

## 修改内容

- 保留对固定提交中 `Setup.tsx` 登录源码的严格摘要和结构检查。
- 编译产物只拒绝可以证明存在浏览器错误泄露的高置信模式：
  - 凭据测试哨兵；
  - 直接显示捕获异常的 toast；
  - 序列化捕获错误对象。
- GraphQL 客户端运行时可以合法包含 `ClientError`、请求结构字段和控制台方法。
- 安全失败只输出规则名称和资源路径，不回显匹配内容。
- 同一检查同时应用于静态 DAED UI 和嵌入 Go 源码的 gzip Web 资源。
- 新增正常 GraphQL 依赖通过与真实凭据哨兵拒绝的回归测试。

## GitHub 重新构建

上传新版源码到仓库根目录后运行：

```text
Branch: main
Parallel jobs: 2
Runtime profile: stable
Artifact stage: test
```

缓存键已经包含修改过的安装器和验证器，新提交会自动生成新的 DAED 源码缓存键，不需要手工删除旧缓存。

## 不变的安全与功能要求

- DAED 默认关闭，监听地址仍为 `127.0.0.1:2023`。
- 浏览器继续只使用同源 `/athena-daed/` 与 `/athena-daed/graphql`。
- LAN、IoT、NSS/Wi-Fi offload、ECM frontend、Flow Offload、IPv6 和恢复入口策略均未改动。
- 未降低登录源码检查、固定提交检查、静态资源完整性检查或固件内容检查。
