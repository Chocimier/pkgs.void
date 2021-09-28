#!/usr/bin/env python3

# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2019-2021 Piotr Wójcik <chocimier@tlen.pl>
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

import json
import os

import datasource
from repopaths import DATADIR


def build_db(source):
    data = json.load(open(os.path.join(DATADIR, 'popcorn.json')))
    reports = data.get('UniqueInstalls')
    if not reports:
        return
    source.add_auxiliary('popularity_reports', reports)
    source.update(
        set_popularity=0
    )
    for pkgname, copies in data['Packages'].items():
        source.update(
            pkgname=pkgname,
            set_popularity=copies
        )


if __name__ == '__main__':
    datasource.update(build_db)
