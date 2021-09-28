#!/usr/bin/env python3

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

import sys
from collections import namedtuple

import datasource


UpdateRow = namedtuple(
    'UpdateRow',
    (
        'pkgname',
        'oldversion',
        'newversion',
    )
)


def load():
    return open('data/void-updates.txt', 'r')


def parse(lines):
    for line in lines:
        if ' -> ' in line:
            fields = [i for i in line.split(' ') if i and i != '->']
            yield UpdateRow(*fields[:len(UpdateRow._fields)])


def build_db(source, repos):
    del repos
    raw = load()
    updates = parse(raw)
    for update in updates:
        source.update(
            pkgname=update.pkgname,
            set_upstreamver=update.newversion
        )


if __name__ == '__main__':
    datasource.update(lambda x: build_db(x, sys.argv[1:]))
