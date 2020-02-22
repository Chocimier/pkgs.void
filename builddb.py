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


def build_db(source, repos):
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
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
                    v = v.decode()
                dictionary[k] = v
            depends_count = len(dictionary.get('run_depends', []))
            source.create(datasource.PackageRow(
                arch=arch,
                pkgname=pkgname,
                pkgver=dictionary['pkgver'],
                repodata=dictionary,
                depends_count=depends_count,
                repo=repo
            ), dates=[today, tomorrow])


if __name__ == '__main__':
    datasource.update(lambda x: build_db(x, sys.argv[1:]))
