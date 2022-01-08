#!/usr/bin/env python3

# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2020 Piotr Wójcik <chocimier@tlen.pl>
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
from collections import namedtuple
from datetime import datetime

import datasource
from repopaths import rsync_load


_DATE_FORMAT = "%Y/%m/%d %H:%M:%S"


Stats = namedtuple('Stats', ('perms', 'size', 'date', 'time', 'name'))


def _pkgver_from_filename(filename):
    return filename.rsplit('.', 2)[0]


def _stats(line):
    parts = filter(None, line.split())
    try:
        return Stats(*parts)
    except TypeError:
        return None


def _is_of_arch(binpkg, repo):
    arch = repo.rpartition('/')[2]
    try:
        binpkg_arch = binpkg.split('.')[-2]
    except IndexError:
        return False
    return binpkg_arch in (arch, 'noarch')


def _process_repo(source, repo, rsync_listing):
    """Sets build date for packages not defining it in index."""
    for line in rsync_listing:
        line = line.strip()
        record = _stats(line)
        if record and _is_of_arch(record.name, repo):
            date = datetime.strptime(
                record.date + ' ' + record.time,
                _DATE_FORMAT
            )
            source.update(
                pkgver=_pkgver_from_filename(record.name),
                repo=repo,
                builddate='',
                set_builddate=date.strftime('%Y-%m-%d %H:%M')
            )


def build_db(source, repos):
    for repo in repos:
        with rsync_load(repo) as listing:
            _process_repo(source, repo, listing)


if __name__ == '__main__':
    datasource.update(lambda x: build_db(x, sys.argv[1:]))
