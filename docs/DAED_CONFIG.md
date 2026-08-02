# DAED DNS 与路由

`athena-setup` 生成三份可复制到 DAED 页面的模板，不直接修改 `wing.db`：

```text
/etc/athena/generated/global.dae
/etc/athena/generated/dns.dae
/etc/athena/generated/routing.dae
```

默认解析策略：

- 国内域名：AliDNS/DNSPod UDP 直连，优先低延迟。
- 国外域名：DoH 经代理访问，避免明文境外 DNS。
- 节点和订阅域名：bootstrap DNS 强制直连，避免“连接节点前又依赖节点解析”的循环。
- 国内 IPv4/IPv6：直连；国外 IPv4/IPv6：默认代理。

DAED 是高性能透明代理与 DNS 分流框架，但隐私仍取决于上游协议、路由规则、IPv6 接管和终端自身的安全 DNS 设置。启用前应确认模板中的代理组名称与 DAED 中实际名称一致。

DAED 前端通过 LuCI 的“服务 → DAED 面板”访问。浏览器不应直接连接 `:2023`；后台 GraphQL 请求必须使用同源地址 `/athena-daed/graphql`。
