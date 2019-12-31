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

from collections import namedtuple


class Attributes:
    def __init__(self, dic):
        super().__init__()
        for i in dic.keys():
            setattr(self, i, dic[i])


class Binpkgs:
    def __init__(self):
        super().__init__()
        self._data = {}
        self._isets = set()
        self._libcs = set()

    def __len__(self):
        return len(self._data)

    def add(self, version, *, iset, libc):
        self._data[(iset, libc)] = Version(version, iset=iset, libc=libc)
        self._isets.add(iset)
        self._libcs.add(libc)

    @property
    def by_libc(self):
        for libc in sorted(self._libcs):
            yield Attributes({
                'libc': libc,
                'by_iset': (self._data.get((iset, libc))
                            for iset in sorted(self._isets))
            })

    @property
    def by_iset(self):
        for iset in sorted(self._isets):
            yield Attributes({
                'iset': iset,
                'by_libc': (self._data.get((iset, libc))
                            for libc in sorted(self._libcs))
            })

    @property
    def all(self):
        for version in self._data.values():
            yield version


Field = namedtuple('Field', ('name', 'title', 'value'))


FoundPackages = namedtuple('FoundPackages', ('parameters', 'other'))


Repo = namedtuple('Repo', ('repo', 'reason'))


ValueAt = namedtuple('ValueAt', ('value', 'coords'))


class Version:
    def __init__(self, version, **kwargs):
        super().__init__()
        components = version.rsplit('_', 1)
        self.version = components[0]
        self.revision = components[1]
        self.data = kwargs
