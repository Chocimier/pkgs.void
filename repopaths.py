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

import os
import sys

from thirdparty import plistop


DATADIR = 'data'


def directory_name(repo):
    result = ''
    if 'musl/' in repo:
        result += 'musl_'
    for i in ('multilib', 'nonfree', 'debug'):
        if i in repo:
            result += i + '_'
    result += repo.rpartition('/')[-1]
    return result


def rsync_path(repo):
    result = ''
    for part in repo.split('/')[:-1]:
        result += part + '/'
    return result


def rsync_filename(path):
    return 'rsync-' + path.strip('/').replace('/', '_')


def rsync_load(repo):
    filename = rsync_filename(rsync_path(repo))
    return open(os.path.join(DATADIR, filename))


def index_path(repo):
    return os.path.join(DATADIR, directory_name(repo), 'index.plist')


def load_repo(path):
    try:
        with open(path, 'rb') as xml_file:
            plist_index = plistop.parse(xml_file)
        return plist_index
    except FileNotFoundError:
        return None


_COMMANDS = {
    'directory_name': directory_name,
    'rsync_path': rsync_path,
    'rsync_filename': rsync_filename,
}


def usage(script_name, bad_command=None):
    def show(string):
        print(string, file=sys.stderr)
    show(f'usage: {script_name} <command> path')
    if bad_command is not None:
        show(f'{bad_command} is not known command')
    show('commands:')
    for command in _COMMANDS:
        show(f'  {command}')


def main(*args):
    try:
        script_name, command, arg = args
    except ValueError:
        usage(args[0])
        sys.exit(1)

    try:
        func = _COMMANDS[command]
    except KeyError:
        usage(script_name, command)
        sys.exit(1)
    print(func(arg))


if __name__ == '__main__':
    main(*sys.argv)
