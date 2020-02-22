#!/usr/bin/env python3

# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2019-2020 Piotr Wójcik <chocimier@tlen.pl>
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

import sys
from datetime import datetime, timedelta

import datasource
from repopaths import index_path, load_repo
from sink import string_hash

_OFFSETS = {
    'CET': timedelta(0, 1*3600),
    'CEST': timedelta(0, 2*3600),
    'UTC': timedelta(0, 0),
    'GMT': timedelta(0, 0),
    'CDT': timedelta(0, -5*3600),
    'CST': timedelta(0, -6*3600),
}


def parse_date(string):
    time_str, zone_code = string.rsplit(' ', 1)
    try:
        time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
    except ValueError:
        return string
    utc_time = time - _OFFSETS[zone_code]
    result = utc_time.strftime('%Y-%m-%d %H:%M UTC')
    return result


def build_db(source, repos):
    for repo in repos:
        path = index_path(repo)
        repodata = load_repo(path)
        if repodata is None:
            continue
        arch = repo.rpartition('/')[-1]
        for pkgname in repodata:
            dictionary = {}
            for k, v in repodata[pkgname].items():
                if isinstance(v, bytes):
                    v = v.decode('utf-8')
                if k == 'build-date':
                    dictionary[k] = parse_date(v)
                else:
                    dictionary[k] = v
            source.create(datasource.PackageRow(
                arch=arch,
                pkgname=pkgname,
                pkgname_hash=string_hash(pkgname),
                pkgver=dictionary['pkgver'],
                restricted=False,
                builddate='',
                repodata=datasource.to_json(dictionary),
                templatedata=datasource.to_json({}),
                upstreamver='',
                repo=repo
            ))


if __name__ == '__main__':
    datasource.update(lambda x: build_db(x, sys.argv[1:]))
