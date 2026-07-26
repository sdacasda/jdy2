routing {
  dip(geoip:private) -> must_direct
  dip(224.0.0.0/3, "ff00::/8") -> must_direct

  dip({{CHINA_DNS_PRIMARY}}, {{CHINA_DNS_SECONDARY}}) && dport(53) -> must_direct
  domain(full: {{NODE_HOSTNAME}}) -> must_direct
  dip({{NODE_IPS}}) -> must_direct

{{STEAM_PROXY_RULES}}
{{XBOX_PROXY_RULES}}
{{STEAM_DIRECT_RULES}}
{{XBOX_DIRECT_RULES}}
{{GAME_MAC_RULES}}
  dport(25565) -> direct
  l4proto(udp) && dport(19132-19133) -> direct
  dscp(0x4) -> direct
{{QUIC_RULE}}
  dip(geoip:cn) -> direct
  domain(geosite:cn) -> direct
  fallback: {{PROXY_GROUP}}
}
