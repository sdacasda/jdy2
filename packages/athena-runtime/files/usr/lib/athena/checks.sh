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

athena_check_override() {
	name="$1"
	eval "present=\${${name}+x}"
	[ "$present" = x ] || return 2
	eval "value=\${$name}"
	[ "$value" = 1 ]
}

athena_nginx_ok() {
	athena_check_override ATHENA_NGINX_OK
	case $? in 0) return 0;; 1) return 1;; esac
	command -v nginx >/dev/null 2>&1 &&
		nginx -t >/dev/null 2>&1 &&
		pidof nginx >/dev/null 2>&1
}

athena_web_ports_ok() {
	athena_check_override ATHENA_WEB_PORTS_OK
	case $? in 0) return 0;; 1) return 1;; esac
	if command -v ss >/dev/null 2>&1; then
		listeners="$(ss -lntp 2>/dev/null || true)"
		printf '%s\n' "$listeners" | grep -Eq '(:|\])80[[:space:]].*nginx' &&
			printf '%s\n' "$listeners" | grep -Eq '(:|\])443[[:space:]].*nginx' &&
			printf '%s\n' "$listeners" | grep -Eq '192\.168\.50\.1:8080[[:space:]].*uhttpd'
		return
	fi
	awk '
		$4 == "0A" && $2 ~ /:(0050|01BB|1F90)$/ { found[substr($2, length($2)-3)] = 1 }
		END { exit !(found["0050"] && found["01BB"] && found["1F90"]) }
	' "$(athena_root /proc/net/tcp)" "$(athena_root /proc/net/tcp6)" 2>/dev/null
}

athena_recovery_web_ok() {
	athena_check_override ATHENA_RECOVERY_WEB_OK
	case $? in 0) return 0;; 1) return 1;; esac
	command -v wget >/dev/null 2>&1 || return 1
	response="$(wget -S -O /dev/null -T 2 http://192.168.50.1:8080/athena-recovery.html 2>&1 || true)"
	printf '%s\n' "$response" | grep -Eq 'HTTP/[0-9.]+[[:space:]]+[0-9]{3}'
}

athena_health_daed_enabled() {
	athena_check_override ATHENA_DAED_ENABLED
	case $? in 0) return 0;; 1) return 1;; esac
	/etc/init.d/daed enabled >/dev/null 2>&1
}

athena_health_daed_running() {
	athena_check_override ATHENA_DAED_RUNNING
	case $? in 0) return 0;; 1) return 1;; esac
	pidof daed >/dev/null 2>&1
}

athena_health_daed_api() {
	athena_check_override ATHENA_DAED_API_REACHABLE
	case $? in 0) return 0;; 1) return 1;; esac
	athena_health_daed_running || return 1
	command -v wget >/dev/null 2>&1 || return 1
	response="$(wget -S -O /dev/null -T 2 http://127.0.0.1:2023/graphql 2>&1 || true)"
	printf '%s\n' "$response" | grep -Eq 'HTTP/[0-9.]+[[:space:]]+[0-9]{3}'
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

	if athena_nginx_ok; then
		athena_check_add nginx critical PASS "Nginx configuration and process are healthy"
	else
		athena_check_add nginx critical FAIL "Nginx primary Web entry is unavailable" "Use the recovery entry on port 8080."
	fi
	if athena_web_ports_ok; then
		athena_check_add web_ports critical PASS "Primary and recovery Web ports have one owner"
	else
		athena_check_add web_ports critical FAIL "Web listener ownership is invalid" "Nginx must own 80/443 and uHTTPd must own 192.168.50.1:8080."
	fi
	if athena_recovery_web_ok; then
		athena_check_add recovery_web critical PASS "Recovery Web entry is reachable"
	else
		athena_check_add recovery_web critical FAIL "Recovery Web entry is unreachable" "Restart uHTTPd and check port 8080."
	fi

	if athena_health_daed_enabled; then
		athena_check_add daed_enabled advisory PASS "DAED is enabled at boot"
	elif [ "$initialized" -eq 1 ]; then
		athena_check_add daed_enabled critical FAIL "DAED is not enabled after setup" "Enable DAED after validating its configuration."
	else
		athena_check_add daed_enabled advisory WARN "DAED is disabled by safe default" "Import templates, then run athena-setup."
	fi
	if athena_health_daed_running; then
		athena_check_add daed_process advisory PASS "DAED process is running"
	elif [ "$initialized" -eq 1 ]; then
		athena_check_add daed_process critical FAIL "DAED process stopped after initialization" "Review DAED logs before restarting it."
	else
		athena_check_add daed_process advisory WARN "DAED process is stopped by safe default"
	fi
	if athena_health_daed_api; then
		athena_check_add daed_api advisory PASS "DAED loopback API is reachable"
	elif [ "$initialized" -eq 1 ]; then
		athena_check_add daed_api critical FAIL "DAED loopback API is unreachable" "Check for eBPF, configuration, or memory startup errors."
	else
		athena_check_add daed_api advisory WARN "DAED API is unavailable while DAED is off"
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
