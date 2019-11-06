#!/usr/bin/env python3

# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2019 Piotr Wójcik <chocimier@tlen.pl>
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

import os
import plistlib
import sys


def directory_name(repo):
    result = ''
    for i in ('multilib', 'nonfree', 'debug'):
        if i in repo:
            result += i + '_'
    result += repo.rpartition('/')[-1]
    return result


def index_path(repo):
    return os.path.join('data', directory_name(repo), 'index.plist')


def load_repo(path):
    try:
        with open(path, 'rb') as xml_file:
            plist_index = plistlib.load(xml_file, fmt=plistlib.FMT_XML)
        return plist_index
    except FileNotFoundError:
        return None


def usage(script_name):
    print(f'usage: {script_name} directory_name path', file=sys.stderr)


def main(*args):
    try:
        script_name, command, arg = args
    except ValueError:
        usage(args[0])
        exit(1)

    if command == 'directory_name':
        print(directory_name(arg))
    else:
        usage(script_name)
        exit(1)


if __name__ == '__main__':
    main(*sys.argv)
