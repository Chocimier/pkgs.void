# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2023 Piotr Wójcik <chocimier@tlen.pl>
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

from workers.buildlog.buildlog import _pkgver_of_mark_line


def test_pkgver_of_mark_line_plain():
    ''' https://build.voidlinux.org/builders/x86_64_builder/builds/40525/steps/shell_3/logs/stdio/text '''
    assert _pkgver_of_mark_line('=> gtk-doc-1.33.2_2: running do-pkg hook: 00-gen-pkg ...') == 'gtk-doc-1.33.2_2'


def test_pkgver_of_mark_line_color_code():
    ''' https://build.voidlinux.org/builders/x86_64_builder/builds/42139/steps/shell_3/logs/stdio/text '''
    assert _pkgver_of_mark_line('\x1b[1m=> skype-8.92.0.204_1: running do-pkg hook: 00-gen-pkg ...') == 'skype-8.92.0.204_1'


def test_pkgver_of_mark_line_two_color_codes():
    ''' https://build.voidlinux.org/builders/x86_64_builder/builds/41467/steps/shell_3/logs/stdio/text '''
    assert _pkgver_of_mark_line('\x1b[m\x1b[1m=> qalculate-4.5.1_1: running do-pkg hook: 00-gen-pkg ...') == 'qalculate-4.5.1_1'

