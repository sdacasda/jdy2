#!/bin/sh
set -eu

SCRIPT="$PROJECT_ROOT/packages/athena-runtime/files/usr/libexec/rpcd/athena"
export ATHENA_JSHN="$PROJECT_ROOT/tests/runtime/fixtures/jshn.sh"
export ATHENA_LIBDIR="$PROJECT_ROOT/packages/athena-runtime/files/usr/lib/athena"
export ATHENA_DAED_ENABLED=1
export ATHENA_DAED_RUNNING=0
export ATHENA_DAED_API_REACHABLE=0
export ATHENA_DAED_ERROR_CLASS=ebpf

output="$(sh "$SCRIPT" call status)"
printf '%s' "$output" | grep -q '"daed_enabled":true'
printf '%s' "$output" | grep -q '"daed_running":false'
printf '%s' "$output" | grep -q '"daed_api_reachable":false'
printf '%s' "$output" | grep -q '"daed_error_class":"ebpf"'
printf '%s' "$output" | grep -q '"recovery_url":"http://192.168.50.1:8080/"'

listing="$(sh "$SCRIPT" list)"
printf '%s' "$listing" | grep -q '"daed_start"'
printf '%s' "$listing" | grep -q '"daed_stop"'
! printf '%s' "$listing" | grep -q '"templates"'
set +e
template_output="$(sh "$SCRIPT" call templates 2>&1)"
template_code=$?
set -e
[ "$template_code" -eq 1 ]
printf '%s' "$template_output" | grep -q '"error":"unknown method"'

# A valid GraphQL error response still proves that the management API is
# reachable.  DAED returns application errors (for example, an empty proxy
# group) while its HTTP/GraphQL backend is otherwise healthy.
mock_bin="$(mktemp -d)"
trap 'rm -rf "$mock_bin"' EXIT
cat >"$mock_bin/wget" <<'EOF'
#!/bin/sh
printf '%s\n' '{"errors":[{"message":"configuration pending"}]}'
exit 8
EOF
command -v chmod >/dev/null 2>&1 && chmod +x "$mock_bin/wget" || true
unset ATHENA_DAED_API_REACHABLE ATHENA_DAED_ERROR_CLASS
export ATHENA_DAED_RUNNING=1
output="$(PATH="$mock_bin:$PATH" sh "$SCRIPT" call status)"
printf '%s' "$output" | grep -q '"daed_running":true'
printf '%s' "$output" | grep -q '"daed_api_reachable":true'
printf '%s' "$output" | grep -q '"daed_error_class":"none"'

# Some OpenWrt BusyBox wget builds reject --post-data.  A failed wget probe
# must fall through to the local TCP probe instead of reporting a false
# disconnect while the DAED GraphQL listener is healthy.
cat >"$mock_bin/wget" <<'EOF'
#!/bin/sh
printf '%s\n' 'wget: unrecognized option: post-data' >&2
exit 1
EOF
cat >"$mock_bin/nc" <<'EOF'
#!/bin/sh
cat >/dev/null
printf 'HTTP/1.1 401 Unauthorized\r\nContent-Type: application/json\r\n\r\n'
printf '%s\n' '{"errors":[{"message":"authentication required"}]}'
EOF
command -v chmod >/dev/null 2>&1 && chmod +x "$mock_bin/wget" "$mock_bin/nc" || true
output="$(PATH="$mock_bin:$PATH" sh "$SCRIPT" call status)"
printf '%s' "$output" | grep -q '"daed_api_reachable":true'
printf '%s' "$output" | grep -q '"daed_error_class":"none"'

printf 'PASS: rpcd status\n'
