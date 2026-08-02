#!/bin/sh

json_init() {
	JSON_OUTPUT=''
	JSON_FIRST=1
}

json_add_pair() {
	key="$1"
	value="$2"
	[ "$JSON_FIRST" -eq 1 ] || JSON_OUTPUT="$JSON_OUTPUT,"
	JSON_FIRST=0
	JSON_OUTPUT="$JSON_OUTPUT\"$key\":$value"
}

json_add_string() {
	value="$(printf '%s' "$2" | sed 's/\\/\\\\/g; s/"/\\"/g')"
	json_add_pair "$1" "\"$value\""
}

json_add_boolean() {
	case "$2" in
		1|true) value=true ;;
		*) value=false ;;
	esac
	json_add_pair "$1" "$value"
}

json_dump() {
	printf '{%s}\n' "$JSON_OUTPUT"
}

json_add_object() { :; }
json_close_object() { :; }
json_load() { :; }
json_get_var() { eval "$1=''"; }
