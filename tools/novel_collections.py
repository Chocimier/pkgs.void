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

sys.path.append('.')

import datasource # noqa, pylint: disable=wrong-import-position
from custom_types import Interest # noqa, pylint: disable=wrong-import-position

SOURCE = datasource.factory()
COLLECTIONS = SOURCE.metapackages()
for i in COLLECTIONS:
    if Interest(i['classification']) == Interest.NOVEL:
        print(i['pkgname'])
