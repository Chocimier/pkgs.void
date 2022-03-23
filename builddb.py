#!/usr/bin/env python3

# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2019-2020 Piotr Wójcik <chocimier@tlen.pl>
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

import sys
from datetime import datetime, timedelta
from sink import now

import datasource
from repopaths import index_path, load_repo
from thirdparty import plistop

_OFFSETS = {
    'CET': timedelta(hours=1),
    'CEST': timedelta(hours=2),
    'UTC': timedelta(hours=0),
    'GMT': timedelta(hours=0),
    'CDT': timedelta(hours=-5),
    'CST': timedelta(hours=-6),
}


def parse_date(string):
    time_str, zone_code = string.rsplit(' ', 1)
    try:
        time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
    except ValueError:
        return string
    if zone_code not in _OFFSETS:
        print("unknown timezone: {}".format(zone_code), file=sys.stderr)
        _OFFSETS[zone_code] = timedelta(hours=0)
    utc_time = time - _OFFSETS[zone_code]
    result = utc_time.strftime('%Y-%m-%d %H:%M')
    return result


def to_std_types(plist):
    if isinstance(plist, bytes):
        return plist.decode()
    if isinstance(plist, plistop.PListArray):
        return [to_std_types(i) for i in plist]
    if isinstance(plist, plistop.PListDict):
        return {k: to_std_types(plist[k]) for k in plist}
    return plist


def build_db(source, repos):
    today = now().date()
    tomorrow = today + timedelta(days=1)
    for repo in repos:
        path = index_path(repo)
        repodata = load_repo(path)
        if repodata is None:
            continue
        arch = repo.rpartition('/')[-1]
        for pkgname, pkgdict in repodata.iteritems():
            dictionary = {}
            for k, v in pkgdict.iteritems():
                if k == 'build-date':
                    dictionary[k] = parse_date(v)
                else:
                    dictionary[k] = to_std_types(v)
            depends_count = len(dictionary.get('run_depends', []))
            mainpkg = dictionary.get('source-revisions', pkgname).split(':')[0]
            source.create(datasource.PackageRow(
                arch=arch,
                pkgname=pkgname,
                pkgver=dictionary['pkgver'],
                builddate=dictionary.get('build-date', ''),
                repodata=dictionary,
                mainpkg=mainpkg,
                depends_count=depends_count,
                repo=repo
            ), dates=[today, tomorrow])


if __name__ == '__main__':
    datasource.update(lambda x: build_db(x, sys.argv[1:]))
