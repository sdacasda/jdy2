# DAED DNS 与路由

- 国内域名：AliDNS/DNSPod UDP 直连。
- 国外域名：DoH 经代理。
- 节点/订阅域名：bootstrap DNS 强制直连。
- 国内 IPv4/IPv6：直连；国外 IPv4/IPv6：代理。

DAED 是高性能透明代理框架，但并不自动保证所有 DNS 加密。隐私取决于上游协议、路由规则、IPv6 接管和浏览器自己的安全 DNS 设置。
