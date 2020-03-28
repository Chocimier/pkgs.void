# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2020 Piotr Wójcik <chocimier@tlen.pl>
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

import json

from custom_types import Interest


class MetapackageInterest:
    def __init__(self):
        self._map = {}
        with open('metadata/metapackage_interest.json') as file:
            for interest, packages in json.load(file).items():
                for package in packages:
                    self._map[package] = getattr(Interest, interest)

    def get(self, pkgname):
        return self._map.get(pkgname, Interest.NOVEL)
