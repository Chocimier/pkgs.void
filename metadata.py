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

import json

from custom_types import Interest


class MetapackageInterest:
    def __init__(self):
        self._map = {}
        self._load_interest('metadata/metapackage_interest.json')
        self._load_interest('metadata/metapackage_interest.local.json')

    def _load_interest(self, path):
        try:
            file = open(path)
        except FileNotFoundError:
            return
        for interest, packages in json.load(file).items():
            for package in packages:
                self._map[package] = getattr(Interest, interest)
        file.close()

    def get(self, pkgname):
        return self._map.get(pkgname, Interest.NOVEL)
