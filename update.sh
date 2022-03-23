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
builddate=yes

path="$(realpath "$(dirname "$0")")"
dir="$(basename "$path")"
cd $path || exit 1
[ -d venv ] && . venv/bin/activate

while true
do
    case "$1" in
        -B) builddate= ;;
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
newindex="$(./settings.py DATASOURCE_ARGUMENTS_TEMPORARY | sed 's/,.*//')"
index="$(./settings.py DATASOURCE_ARGUMENTS | sed 's/,.*//')"
mkdir -p "$generated"
cd .. || exit 1
tar cjf "$dir/$generated/tmp.tar.bz2" --exclude-ignore tar-exclude "$dir" || exit 1
cd "$dir" || exit 1
mv "$generated"/tmp.tar.bz2 "$generated"/pkgs.void.tar.bz2 || exit 1

if [ "$templates" ]
then
    : "${XBPS_DISTDIR:=$(xdistdir)}"
    ( cd "$XBPS_DISTDIR" || exit $?
    if [ "$download" ]
    then
        git fetch -q origin || exit $?
    fi
    git checkout -q origin/master || exit $?
    ) || exit $?
fi

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

if [ "$builddate" ]; then
	for path in $repos; do
		echo "$(cd ..; ./repopaths.py rsync_path "$path")"
	done | sort -u | while read dir; do
		filename="$(cd ..; ./repopaths.py rsync_filename "$dir")"
		[ "$download" ] && rsync --list-only "${rsyncmirror}${dir}" --include '*.xbps' --exclude='*' > "${filename}"
	done
fi

[ "$download" ] && [ "$updates" ] && wget -q -O void-updates.txt "$mirror/void-updates/void-updates.txt"
[ "$download" ] && [ "$popularity" ] &&
  wget -q -O popcorn.today.json "$popcornmirror/popcorn_$(date +%Y-%m-%d).json" &&
  mv popcorn.today.json popcorn.json

cd .. || exit 1

rm -f "$newindex"
./builddb.py $repos
[ "$templates" ] && ./dbfromrepo.py $repos
[ "$updates" ] && ./updates.py $repos
[ "$popularity" ] && ./popularity.py
[ "$builddate" ] && ./rsyncdata.py $repos

mv "$newindex" "$index"

python -c 'import voidhtml; print(voidhtml.list_all())' > "$generated"/all.html
