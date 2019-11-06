#!/bin/sh

# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2019 Piotr Wójcik <chocimier@tlen.pl>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# This script updates packages database and published source tarball.

mirror=https://alpha.de.repo.voidlinux.org
download=yes
templates=
updates=

cd "$(dirname "$0")" || exit 1
[ -r ./profile ] && . ./profile

while true
do
    case "$1" in
        -D) download= ;;
        -m)
            shift
            mirror="$1"
            ;;
        -t) templates=yes ;;
        -u) updates=yes ;;
        *) break
    esac
    shift
done

mkdir -p static/source
tar cjf static/source/tmp.tar.bz2  --exclude-ignore tar-exclude . || exit 1
mv static/source/tmp.tar.bz2  static/source/pkgs.void.tar.bz2 || exit 1

if [ "$templates" ]
then
    : "${XBPS_DISTDIR:=$(xdistdir)}"
    ( cd "$XBPS_DISTDIR" || exit $?
    git checkout xbps-src-p || exit $?
    if [ "$download" ]
    then
        git fetch origin || exit $?
        git rebase origin/master || exit $?
    fi
    ) || exit $?
fi

mkdir -p data
cd data || exit 1

repos=$(cat ../repos.list)

for path in $repos; do
	arch="$(echo "$path" | tr / _)"
	filename="$arch-repodata.tar.xz"
	extract_dir=$(../repopaths.py directory_name "$path")
	[ "$download" ] && wget -q -O "$filename" "$mirror/current/$path-repodata"
	rm -r "$extract_dir"
	mkdir "$extract_dir"
	tar xf "$filename" -C "$extract_dir"
done

[ "$download" ] && [ "$updates" ] && wget -q -O void-updates.txt "$mirror/void-updates/void-updates.txt"

cd .. || exit 1

rm -f newindex.sqlite3
./builddb.py $repos
[ "$templates" ] && ./dbfromrepo.py $repos
[ "$updates" ] && ./updates.py $repos

mv newindex.sqlite3 index.sqlite3
