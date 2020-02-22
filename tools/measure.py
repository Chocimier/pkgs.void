#!/usr/bin/env python3

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

import cProfile
import subprocess
import sys
import timeit

import gprof2dot

sys.path.append('.')
import voidhtml # noqa, pylint: disable=wrong-import-position
from config import REPOS # noqa, pylint: disable=wrong-import-position


_PROFILE = 'profile'
_TIMEIT = 'timeit'


_GCC = 'gcc'
_NEWEST = 'newest'


def is_func(constant, variable):
    return variable is None or variable == constant


def _heat_up():
    voidhtml.page_generator('gcc', REPOS)
    voidhtml.newest()


def _timeit_run(name, code):
    time = timeit.timeit(
        code,
        setup="import voidhtml; from config import REPOS",
        number=100
    )
    print(f'{name}: {time}s')


def _timeit(func):
    if is_func(_GCC, func):
        _timeit_run(_GCC, "voidhtml.page_generator('gcc', REPOS)")
    if is_func(_NEWEST, func):
        _timeit_run(_NEWEST, "voidhtml.newest()")


def _profile_run(code):
    cProfile.run(code, filename='profile.log')
    gprof2dot.main(['-f', 'pstats', 'profile.log', '-o', 'profile.dot'])
    subprocess.call(['dot', '-Tsvg', '-oprofile.svg', 'profile.dot'])


def _profile(func):
    if func == _GCC:
        _profile_run("voidhtml.page_generator('gcc', REPOS)")
    elif func == _NEWEST:
        _profile_run("voidhtml.newest()")
    else:
        print('pass func name', file=sys.stderr)
        sys.exit(1)


def main(mode=None, func=None):
    _heat_up()
    if is_func(_PROFILE, mode):
        _profile(func)
    if is_func(_TIMEIT, mode):
        _timeit(func)


def usage(status):
    funcs = f'{_GCC}|{_NEWEST}'
    print(
        sys.argv[0] + f' {_TIMEIT} [{funcs}]\n' +
        sys.argv[0] + f' {_PROFILE} {funcs}'
    )
    if status is not None:
        sys.exit(status)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        usage(1)
    main(*sys.argv[1:])
