#!/usr/bin/env python3

# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2021 Piotr Wójcik <chocimier@tlen.pl>
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

import configparser
import sys

from custom_types import Attributes


DEFAULT_SECTION = 'common'


def load_config(section=DEFAULT_SECTION):
    parser = configparser.ConfigParser(
        delimiters=('=',),
        comment_prefixes=('#',),
        empty_lines_in_values=False,
        default_section=section,
        interpolation=None,
    )
    parser.optionxform = lambda x: x
    with open('configs/defaults.ini') as defaults:
        parser.read_file(defaults)
    parser.read(('config.ini',))
    values = Attributes(parser[parser.default_section])
    convert_types(values, section)
    return values


def convert_types(values, section):
    if section == 'common':
        values.DEVEL_MODE = (values.DEVEL_MODE == 'yes')
        values.DAILY_HASH_BITS = int(values.DAILY_HASH_BITS)


def usage(script_name, bad_command=None):
    def show(string):
        print(string, file=sys.stderr)
    show(f'usage: {script_name} key')
    if bad_command is not None:
        show(f'"{bad_command}" is not defined key')
    show('Defined keys:')
    for key in dir(config):
        if not key.startswith('_'):
            show(f'  {key}')


def main(*args):
    try:
        script_name, key = args
    except ValueError:
        usage(args[0])
        sys.exit(1)
    try:
        value = getattr(config, key)
    except AttributeError:
        usage(script_name, key)
        sys.exit(1)
    print(value)


config = load_config()


if __name__ == '__main__':
    main(*sys.argv)
