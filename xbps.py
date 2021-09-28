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


DEFAULT_LIBC = 'glibc'


def pkgname_from_pkgver(pkgver):
    '''Extracts pkgname (like python3) from pkgver (like python3-3.8.1_1)'''
    return pkgver.rpartition('-')[0]


def verrev_from_pkgver(pkgver):
    '''Extracts verrev (like 3.8.1_1) from pkgver (like python3-3.8.1_1)'''
    return pkgver.rpartition('-')[2]


def version_from_pkgver(pkgver):
    '''Extracts version (like 3.8.1) from pkgver (like python3-3.8.1_1)'''
    return version_from_verrev(verrev_from_pkgver(pkgver))


def revision_from_pkgver(pkgver):
    '''Extracts revision (like 1) from pkgver (like python3-3.8.1_1)'''
    return revision_from_verrev(verrev_from_pkgver(pkgver))


def version_from_verrev(verrev):
    '''Extracts version (like 3.8.1) from verrev (like 3.8.1_1)'''
    return verrev.partition('_')[0]


def revision_from_verrev(verrev):
    '''Extracts revision (like 1) from verrev (like 3.8.1_1)'''
    return verrev.rpartition('_')[2]


def split_arch(arch):
    '''Returns instruction set and libc matching arch, like
    x86_64-musl -> x86_64, musl
    aarch64 -> aarch64, glibc
    '''
    try:
        iset, libc = arch.split('-')
    except ValueError:
        iset = arch
        libc = DEFAULT_LIBC
    return iset, libc


def join_arch(iset, libc):
    '''Returns arch matching instruction set and libc, like
    x86_64, musl -> x86_64-musl
    aarch64, glibc -> aarch64
    '''
    if not libc or libc == DEFAULT_LIBC:
        return iset
    return f'{iset}-{libc}'
