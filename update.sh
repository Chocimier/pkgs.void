#!/bin/sh

# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2019 Piotr Wójcik <chocimier@tlen.pl>
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

# This script updates packages database and published source tarball.

download=yes
templates=yes
updates=
popularity=yes

path="$(realpath "$(dirname "$0")")"
dir="$(basename "$path")"
cd $path || exit 1
. venv/bin/activate

logfile="$PWD/data/log"
mkdir -p "$(dirname "$logfile")"
echo "$(date -Iseconds)" UPDATING BEGINS >> "$logfile"

while true
do
    case "$1" in
        -D) download= ;;
        -P) popularity= ;;
        -T) templates= ;;
        -t) templates=yes ;;
        -u) updates=yes ;;
        *) break
    esac
    shift
done

mirror="$(./settings.py REPODATA_MIRROR)"
rsyncmirror="$(./settings.py RSYNC_MIRROR)"
popcornmirror="$(./settings.py POPCORN_MIRROR)"
generated="$(./settings.py GENERATED_FILES_PATH)"

echo "$(date -Iseconds)" publishing code >> "$logfile"
mkdir -p "$generated"
cd .. || exit 1
tar cjf "$dir/$generated/tmp.tar.bz2" --exclude-ignore tar-exclude "$dir" || exit 1
cd "$dir" || exit 1
mv "$generated"/tmp.tar.bz2 "$generated"/pkgs.void.tar.bz2 || exit 1

if [ "$templates" ]
then
    echo "$(date -Iseconds)" fetching templates >> "$logfile"
    : "${XBPS_DISTDIR:=$(xdistdir)}"
    : "${XBPS_DISTDIR:?}"
    (cd "$XBPS_DISTDIR" || exit $?
    if [ "$download" ]
    then
        git fetch -q origin || exit $?
    fi
    git checkout -q origin/master || exit $?
    ) || exit $?
fi

echo "$(date -Iseconds)" fetching repodata >> "$logfile"
mkdir -p data
cd data || exit 1

repos=$(cat ../repos.list)

for path in $repos; do
	extract_dir=$(cd ..; ./repopaths.py directory_name "$path")
	[ -e "$extract_dir" ] && rm -r "$extract_dir"
done

for path in $repos; do
	arch="$(echo "$path" | tr / _)"
	filename="$arch-repodata.tar.xz"
	extract_dir=$(cd ..; ./repopaths.py directory_name "$path")
	[ "$download" ] && wget -q -O "$filename" "$mirror/current/$path-repodata"
	if ! [ -s "$filename" ]; then
		continue
	fi
	mkdir "$extract_dir" || exit $?
	tar xf "$filename" -C "$extract_dir"
done

echo "$(date -Iseconds)" listing package create date >> "$logfile"
for path in $repos; do
	echo "$(cd ..; ./repopaths.py rsync_path "$path")"
done | sort -u | while read dir; do
	filename="$(cd ..; ./repopaths.py rsync_filename "$dir")"
	[ "$download" ] && rsync --list-only "${rsyncmirror}${dir}" --include '*.xbps' --exclude='*' > "${filename}"
done

echo "$(date -Iseconds)" fetching updates >> "$logfile"
[ "$download" ] && [ "$updates" ] && wget -q -O void-updates.txt "$mirror/void-updates/void-updates.txt"
echo "$(date -Iseconds)" fetching popcorn >> "$logfile"
[ "$download" ] && [ "$popularity" ] &&
  wget -q -O popcorn.today.json "$popcornmirror/popcorn_$(date +%Y-%m-%d).json" &&
  mv popcorn.today.json popcorn.json

cd .. || exit 1

rm -f newindex.sqlite3
echo "$(date -Iseconds)" parsing repodata >> "$logfile"
./builddb.py $repos
echo "$(date -Iseconds)" parsing templates >> "$logfile"
[ "$templates" ] && ./dbfromrepo.py $repos
echo "$(date -Iseconds)" parsing updates >> "$logfile"
[ "$updates" ] && ./updates.py $repos
echo "$(date -Iseconds)" parsing popcorn >> "$logfile"
[ "$popularity" ] && ./popularity.py
echo "$(date -Iseconds)" parsing package create date >> "$logfile"
./rsyncdata.py $repos

mv newindex.sqlite3 index.sqlite3

echo "$(date -Iseconds)" generating static pages >> "$logfile"
python -c 'import voidhtml; print(voidhtml.list_all())' > "$generated"/all.html
echo "$(date -Iseconds) update done" >> "$logfile"
