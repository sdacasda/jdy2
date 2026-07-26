dns {
  optimistic_cache: true
  optimistic_cache_ttl: 120
  max_cache_size: 8192

  upstream {
    china_primary: "udp://{{CHINA_DNS_PRIMARY}}:53"
    china_secondary: "udp://{{CHINA_DNS_SECONDARY}}:53"
    global_doh: "{{GLOBAL_DOH}}"
  }

  routing {
    request {
      sub() -> china_primary
      subnode() -> china_primary
      node() -> china_primary
{{ECH_RULE}}
      qname(geosite:cn) -> china_primary
      fallback: global_doh
    }
    response {
      upstream(global_doh) -> accept
      fallback: accept
    }
  }
}
