# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2022-2023 Piotr Wójcik <chocimier@tlen.pl>
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

from xbps import pkgname_from_pkgver, verrev_from_pkgver, split_arch, join_arch


def test_pkgname_from_pkgver_python3():
    assert pkgname_from_pkgver('python3-3.8.1_1') == 'python3'


def test_pkgname_from_pkgver_python3_devel():
    assert pkgname_from_pkgver('python3-devel-3.8.1_1') == 'python3-devel'


def test_verrev_from_pkgver_python3():
    assert verrev_from_pkgver('python3-3.8.1_1') == '3.8.1_1'


def test_verrev_from_pkgver_python3_devel():
    assert verrev_from_pkgver('python3-devel-3.8.1_1') == '3.8.1_1'


def test_split_arch_x86_64_musl():
    assert split_arch('x86_64-musl') == ('x86_64', 'musl')


def test_split_arch2_aarch64():
    assert split_arch('aarch64') == ('aarch64', 'glibc')


def test_join_arch_x86_64():
    assert join_arch('x86_64', 'musl') == 'x86_64-musl'


def test_join_arch_aarch64():
    assert join_arch('aarch64', 'glibc') == 'aarch64'
