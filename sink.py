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


import datetime


def removeprefix(string, prefix):
    '''from PEP 616'''
    if string.startswith(prefix):
        return string[len(prefix):]
    return string


def removesuffix(string, suffix):
    '''from PEP 616'''
    if suffix and string.endswith(suffix):
        return string[:-len(suffix)]
    return string


def same(arg):
    return arg


def now():
    return datetime.datetime.now(datetime.timezone.utc)
