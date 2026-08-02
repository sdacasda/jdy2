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

printf 'PASS: rpcd status\n'
