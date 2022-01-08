#!/bin/sh

update() {
	[ -f "$1" ] || exit
	installed="$(mktemp)"
	explicit="$(mktemp)"
	pip freeze | sed 's/==/>=/' > "$installed"
	cat "$1" | sed 's/[[].*[]]//' | sed 's/=.*//' > "$explicit"
	grep -f "$explicit" "$installed" > "$1"
	rm "$installed" "$explicit"
}

update requirements.txt
update requirements-dev.txt
