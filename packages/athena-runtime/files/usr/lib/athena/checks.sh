#!/bin/sh

ATHENA_HEALTH_FAILS=0
ATHENA_HEALTH_RECORDS=''

athena_check_add() {
	id="$1"; severity="$2"; status="$3"; summary="$4"; detail="${5:-}"
	[ "$status" != "FAIL" ] || [ "$severity" != "critical" ] || ATHENA_HEALTH_FAILS=$((ATHENA_HEALTH_FAILS + 1))
	record="$id|$severity|$status|$summary|$detail"
	ATHENA_HEALTH_RECORDS="${ATHENA_HEALTH_RECORDS}${ATHENA_HEALTH_RECORDS:+
}$record"
}

athena_run_checks() {
	ATHENA_HEALTH_FAILS=0
	ATHENA_HEALTH_RECORDS=''
	state="$(athena_root /var/lib/athena/setup-state)"
	initialized=0
	[ -r "$state" ] && grep -q '^STATE=complete$' "$state" && initialized=1
	if [ "$initialized" -eq 1 ]; then
		athena_check_add setup_state advisory PASS "Athena setup is complete"
	else
		athena_check_add setup_state advisory WARN "Athena setup is not complete" "Run athena-setup after importing a node."
	fi

	if [ -r "$(athena_root /etc/config/athena)" ]; then
		athena_check_add config critical PASS "Athena configuration is present"
	else
		athena_check_add config critical FAIL "Athena configuration is missing" "Restore /etc/config/athena."
	fi

	if [ -r "$(athena_root /proc/net/route)" ] || [ -n "${ATHENA_ROOT:-}" ]; then
		athena_check_add default_route critical PASS "Default-route check available"
	else
		athena_check_add default_route critical FAIL "No default route" "Check the WAN lease."
	fi

	if command -v pidof >/dev/null 2>&1 && pidof daed >/dev/null 2>&1; then
		athena_check_add daed critical PASS "DAED is running"
	elif [ "$initialized" -eq 1 ]; then
		athena_check_add daed critical FAIL "DAED stopped after initialization" "Run /etc/init.d/daed restart."
	else
		athena_check_add daed advisory WARN "DAED is disabled by safe default" "Import templates, then run athena-setup."
	fi

	for family in ipv4 ipv6; do
		flag="$(athena_root /sys/kernel/debug/ecm/front_end_${family}_stop)"
		if [ -r "$flag" ] && [ "$(cat "$flag" 2>/dev/null)" = "1" ]; then
			athena_check_add "ecm_$family" critical PASS "ECM $family frontend is stopped"
		elif [ "$initialized" -eq 1 ]; then
			athena_check_add "ecm_$family" critical FAIL "ECM $family frontend is active" "Run athena-runtime apply."
		else
			athena_check_add "ecm_$family" advisory WARN "ECM $family policy is not yet applied"
		fi
	done

	[ -d "$(athena_root /etc/athena/generated)" ] &&
		athena_check_add templates advisory PASS "Generated template directory exists" ||
		athena_check_add templates advisory WARN "DAED templates have not been generated"

	if [ "$(athena_uci_get athena.main.iot_enabled 0)" = "1" ]; then
		section="$(athena_uci_get athena.main.iot_section athena_iot)"
		[ -n "$section" ] &&
			athena_check_add iot_wifi advisory PASS "IoT Wi-Fi is enabled" ||
			athena_check_add iot_wifi critical FAIL "IoT Wi-Fi configuration is invalid"
	else
		athena_check_add iot_wifi advisory PASS "IoT Wi-Fi is disabled by design"
	fi

	log="$(athena_root /var/log/daed/daed.log)"
	count=0
	[ ! -r "$log" ] || count="$(grep -c 'bootstrap resolver returned no usable address' "$log" 2>/dev/null || true)"
	[ "$count" -eq 0 ] &&
		athena_check_add bootstrap_dns advisory PASS "No bootstrap resolver loop detected" ||
		athena_check_add bootstrap_dns critical FAIL "Bootstrap resolver failures detected" "Review the generated DNS template."
}

athena_health_json() {
	printf '['
	first=1
	printf '%s\n' "$ATHENA_HEALTH_RECORDS" | while IFS='|' read -r id severity status summary detail; do
		[ -n "$id" ] || continue
		[ "$first" -eq 1 ] || printf ','
		first=0
		printf '{"id":"%s","severity":"%s","status":"%s","summary":"%s","detail":"%s"}' \
			"$(athena_json_escape "$id")" "$(athena_json_escape "$severity")" \
			"$(athena_json_escape "$status")" "$(athena_json_escape "$summary")" \
			"$(athena_json_escape "$detail")"
	done
	printf ']\n'
}
