global {
  lan_interface: "br-lan"
  wan_interface: "auto"
  auto_config_kernel_parameter: true
  dial_mode: "domain"
  sniffing_timeout: 30ms
  allow_insecure: false
  log_level: warn
  disable_thp: true
  mptcp: false
  bootstrap_resolver: "{{CHINA_DNS_PRIMARY}}:53"
  fallback_resolver: "{{CHINA_DNS_SECONDARY}}:53"
  check_interval: 60s
  check_tolerance: 100ms
}
