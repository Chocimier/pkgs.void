#!/bin/sh

# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2021 Piotr Wójcik <chocimier@tlen.pl>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Generates output of `xbps-src show` for all templates,
# using output form previous run.

# Data structure:
#
# $cachedir
# └── {complete,tmp}/
#     ├── meta/
#     │   └── revision
#     ├── pkg/
#     │   ├── commD
#     │   ├── libA
#     │   ├── libA-devel -> ../subpkg/libA/libA-devel
#     │   └── libA-doc -> ../subpkg/libA/libA-doc
#     └── subpkg/
#         └── libA/
#             ├── libA-devel
#             └── libA-doc
#
# meta/revision contains git revision of void-packages at time of generating
# data
#
# Files in pkg/ are:
# - for main packages: xbps-src-show output
# - for subpackages: links to subpkg/MAINPKG/SUBPKG
#
# Directories in subpkg/ are named after main pkgs, and contain empty
# files named after subpackages

generate() {
	pkg="${1:?}"
	if [ -e "$opdir/pkg/$pkg" ] ; then
		return
	fi
	echo "$(date -Iseconds) generating $pkg" >> "$logfile"
	if [ -h "srcpkgs/$pkg" ]; then
		mainpkg="$(basename "$(realpath "srcpkgs/$pkg")")"
		mainpkgdir="$opdir/subpkg/$mainpkg"
		mkdir -p "$mainpkgdir"
		# output for subpackages is wrong and ignored anyway
		: ./xbps-src show -p 'restricted*' "$pkg" > "$mainpkgdir/$pkg"
		ln -sr "$mainpkgdir/$pkg" "$opdir/pkg/$pkg"
	else
		./xbps-src show -p 'restricted*' "$pkg" > "$opdir/pkg/$pkg"
	fi
}

generate_all() {
	for i in srcpkgs/*; do
		generate "$(basename "$i")"
	done
}

remove() {
	pkg="${1:?}"
	mainpkg=$(basename "$(find "$opdir/subpkg" -type f -name "$pkg" -exec basename '{}' ';')")
	: "${mainpkg:=$pkg}"
	echo "$(date -Iseconds) removing data of $mainpkg ($pkg)" >> "$logfile"
	rm -rf "${opdir:?}/pkg/${mainpkg:?}" "${opdir:?}/subpkg/${mainpkg:?}"
}

init_storage() {
	mkdir -p "$opdir/pkg" "$opdir/subpkg" "$opdir/meta"
}

clean_broken_files() {
	find -P "${opdir:?}" -xtype l -delete
}

copy_cache() {
	rm -fr "${opdir:?}"
	[ -d "$cachedir/complete" ] && cp -r "$cachedir/complete" "$opdir"
	init_storage
}

main() {
	argdir="$1"
	validity="$2"
	logfile="$3"
	if [ -z "$argdir" ] || [ -z "$validity" ] || [ -z "$logfile" ]; then
		echo "Usage:	$0 cachedir validity logfile"
		exit 1
	fi

	mkdir -p "$argdir" || exit 1
	cd "$argdir" || exit 1
	cachedir="$(pwd)" || exit 1
	opdir="$cachedir/tmp" || exit 1
	echo "$(date -Iseconds) parsing templates into $cachedir begins" >> "$logfile"
	[ -e "$opdir" ] && rm -r "$opdir"

	cd "$(xdistdir)" || exit 1

	if [ -s "$cachedir/complete/meta/times_used" ]; then
		times_used=$(cat "$cachedir/complete/meta/times_used")
	fi
	: "${times_used:=0}"

	if [ "$times_used" -lt "$validity" ] && [ -d "$cachedir/complete" ] && [ -s "$cachedir/complete/meta/revision" ]; then
		echo "$(date -Iseconds)" trying to reuse cache >> "$logfile"
		use_old=1
		old_revision=$(cat "$cachedir/complete/meta/revision")
		git diff "$old_revision" --name-only | while read -r path; do
			case "$path" in
				srcpkgs/*) ;;
				common/shlibs) ;;
				COPYING) ;;
				.github/*) ;;
				*.md) ;;
				*)
					echo "$(date -Iseconds) dropping cache due to change of $path" >> "$logfile"
					use_old=
					;;
			esac
		done
	else
		echo "$(date -Iseconds)" not trying to reuse cache >> "$logfile"
		use_old=
	fi

	if [ "$use_old" ]; then
		copy_cache
		git diff "$old_revision" --name-only | while read -r path; do
			case "$path" in
				srcpkgs/*)
					template="${path#srcpkgs/}"
					template="${template%%/*}"
					remove "$template"
					;;
			esac
		done
		clean_broken_files
		echo $((times_used + 1)) > "$opdir/meta/times_used"
	else
		init_storage
		echo 1 > "$opdir/meta/times_used"
	fi
	generate_all

	git rev-parse --verify HEAD > "$opdir/meta/revision"
	[ -e "$cachedir/complete" ] && rm -r "$cachedir/complete"
	rm -fr "$cachedir/complete"
	mv "$opdir" "$cachedir/complete"
}

main "$@"
