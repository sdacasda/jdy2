# DAED DNS 与路由

`/usr/share/athena/templates` 和 `/usr/share/athena/rules` 保留为固件内部的
维护参考数据。它们不在 LuCI 中展示，`athena-setup` 也不会生成、导入或应用
其中的内容。

默认参考策略为：

- 国内域名：AliDNS/DNSPod UDP 直连，优先低延迟。
- 国外域名：DoH 经代理访问，避免明文境外 DNS。
- 节点和订阅域名：bootstrap DNS 强制直连，避免“连接节点前又依赖节点解析”的循环。
- 国内 IPv4/IPv6：直连；国外 IPv4/IPv6：默认代理。

DAED 是高性能透明代理与 DNS 分流框架，但隐私仍取决于上游协议、路由规则、
IPv6 接管和终端自身的安全 DNS 设置。需要启用时，请在 DAED 面板中完成并验证
自己的配置；Athena 不会直接修改 `wing.db`。

DAED 前端通过 LuCI 的“服务 → Athena 优化 → DAED 面板”访问。浏览器不应直接
连接 `:2023`；后台 GraphQL 请求必须使用同源地址 `/athena-daed/graphql`。
