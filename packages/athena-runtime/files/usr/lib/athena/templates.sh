#!/bin/sh

ATHENA_LIBDIR="${ATHENA_LIBDIR:-/usr/lib/athena}"
. "$ATHENA_LIBDIR/common.sh"

athena_template_escape() {
	printf '%s' "$1" | sed -e 's/[\/&]/\\&/g'
}

athena_domain_rule() {
	list="$1"
	action="$2"
	values=""
	while IFS= read -r domain; do
		case "$domain" in ""|\#*) continue ;; esac
		values="${values}${values:+, }suffix: $domain"
	done <"$list"
	[ -n "$values" ] && printf '  domain(%s) -> %s\n' "$values" "$action"
}

athena_render_templates() {
	output="$1"
	proxy_group="$2"
	node_hostname="$3"
	node_ips="$4"
	game_macs="${5:-}"
	case "$proxy_group" in ""|*[^-A-Za-z0-9_\ ]*) athena_die "invalid proxy group" ;; esac
	athena_is_hostname "$node_hostname" || athena_die "invalid node hostname"
	for ip in $(printf '%s' "$node_ips" | tr ',' ' '); do athena_is_ipv4 "$ip" || athena_die "invalid node IP"; done
	for mac in $(printf '%s' "$game_macs" | tr ',' ' '); do athena_is_mac "$mac" || athena_die "invalid game MAC"; done

	template_root="$(athena_root /usr/share/athena/templates)"
	rule_root="$(athena_root /usr/share/athena/rules)"
	stage="${output}.staging.$$"
	rm -rf "$stage"
	mkdir -p "$stage"
	china_primary="$(athena_uci_get athena.main.china_dns_primary 223.5.5.5)"
	china_secondary="$(athena_uci_get athena.main.china_dns_secondary 119.29.29.29)"
	global_doh="$(athena_uci_get athena.main.global_doh https://dns.google:443/dns-query)"
	quic="$(athena_uci_get athena.main.quic_policy proxy)"
	disable_ech="$(athena_uci_get athena.main.disable_ech 0)"

	cp "$template_root/global.dae.tpl" "$stage/global.dae"
	cp "$template_root/dns.dae.tpl" "$stage/dns.dae"
	cp "$template_root/routing.dae.tpl" "$stage/routing.dae"
	for file in "$stage/global.dae" "$stage/dns.dae" "$stage/routing.dae"; do
		sed -i \
			-e "s/{{CHINA_DNS_PRIMARY}}/$(athena_template_escape "$china_primary")/g" \
			-e "s/{{CHINA_DNS_SECONDARY}}/$(athena_template_escape "$china_secondary")/g" \
			-e "s/{{GLOBAL_DOH}}/$(athena_template_escape "$global_doh")/g" \
			-e "s/{{PROXY_GROUP}}/$(athena_template_escape "$proxy_group")/g" \
			-e "s/{{NODE_HOSTNAME}}/$(athena_template_escape "$node_hostname")/g" \
			-e "s/{{NODE_IPS}}/$(athena_template_escape "$node_ips")/g" "$file"
	done
	ech_rule=""
	[ "$disable_ech" = 1 ] && ech_rule="      qtype(https) -> reject"
	sed -i "s/{{ECH_RULE}}/$(athena_template_escape "$ech_rule")/" "$stage/dns.dae"
	steam_proxy="$(athena_domain_rule "$rule_root/steam-proxy-domains.txt" "$proxy_group")"
	steam_direct="$(athena_domain_rule "$rule_root/steam-direct-domains.txt" direct)"
	xbox_proxy="$(athena_domain_rule "$rule_root/xbox-proxy-domains.txt" "$proxy_group")"
	xbox_direct="$(athena_domain_rule "$rule_root/xbox-direct-domains.txt" direct)"
	game_rules=""
	for mac in $(printf '%s' "$game_macs" | tr ',' ' '); do
		game_rules="${game_rules}  mac('$mac') && l4proto(udp) -> direct
"
	done
	quic_rule=""
	[ "$quic" = block ] && quic_rule="  l4proto(udp) && dport(443) -> block"
	for pair in \
		"STEAM_PROXY_RULES|$steam_proxy" "STEAM_DIRECT_RULES|$steam_direct" \
		"XBOX_PROXY_RULES|$xbox_proxy" "XBOX_DIRECT_RULES|$xbox_direct" \
		"GAME_MAC_RULES|$game_rules" "QUIC_RULE|$quic_rule"; do
		key="${pair%%|*}"
		value="${pair#*|}"
		escaped="$(printf '%s' "$value" | sed ':a;N;$!ba;s/[\/&]/\\&/g;s/\n/\\n/g')"
		sed -i "s/{{$key}}/$escaped/" "$stage/routing.dae"
	done
	if grep -Rqs '{{[A-Z_]*}}' "$stage"; then
		rm -rf "$stage"
		athena_die "unresolved template variable"
	fi
	cat >"$stage/IMPORT.md" <<EOF
# DAED import order
1. Import global.dae.
2. Import dns.dae.
3. Import routing.dae.
4. Select the proxy group "$proxy_group" in DAED.
5. Save and start DAED manually.
EOF
	rm -rf "$output"
	mv "$stage" "$output"
}
