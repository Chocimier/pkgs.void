#!/usr/bin/env python3

# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2020-2021 Piotr Wójcik <chocimier@tlen.pl>
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

import cProfile
import subprocess
import sys
import timeit

import gprof2dot

sys.path.append('.')
import voidhtml # noqa, pylint: disable=wrong-import-position,unused-import


_PROFILE = 'profile'
_TIMEIT = 'timeit'


_CODE_MAP = {
    "gcc": "voidhtml.page_generator('gcc')",
    "main": "voidhtml.main_page()",
    "newest": "voidhtml.newest()",
    "of_day": "voidhtml.of_day()",
    "popular": "voidhtml.popular()",
    "sets": "voidhtml.metapackages()",
    "longest": "voidhtml.longest_names()",
    "find": "voidhtml.find('void', [])",
    "find-nothing": "voidhtml.find('sgzfalcoxjvfmpgrme', [])",
}


def is_func(constant, variable):
    return variable is None or variable == constant


def _timeit_run(name, code):
    time = timeit.timeit(
        code,
        setup="import voidhtml",
        number=1000
    )
    print(f'{name}: {time}s')


def _code(func):
    return _CODE_MAP.get(func)


def _timeit(func):
    if func:
        _timeit_run(func, _code(func))
        return
    for real_func in _CODE_MAP:
        _timeit_run(real_func, _code(real_func))


def _profile_run(code):
    cProfile.run(code, filename='profile.log')
    gprof2dot.main([
        '-f', 'pstats',
        '--color-nodes-by-selftime',
        '-o', 'profile.dot',
        'profile.log',
    ])
    subprocess.call(['dot', '-Tsvg', '-oprofile.svg', 'profile.dot'])


def _profile(func):
    code = _code(func)
    if code:
        _profile_run(';'.join([code]*1000))
    else:
        print('pass func name', file=sys.stderr)
        sys.exit(1)


def main(mode=None, func=None):
    if is_func(_PROFILE, mode):
        _profile(func)
    if is_func(_TIMEIT, mode):
        _timeit(func)


def usage(status):
    funcs = '|'.join(_CODE_MAP.keys())
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
