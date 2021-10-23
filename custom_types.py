# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2019-2021 Piotr Wójcik <chocimier@tlen.pl>
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

from collections import defaultdict, namedtuple
from enum import Enum


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

    @staticmethod
    def _arch_sortkey(version):
        return '{iset}-{libc}'.format(**version.data)

    @property
    def by_version(self):
        versions = defaultdict(list)
        for value in self._data.values():
            versions[value.verrev].append(value)
        for key in sorted(versions.keys()):
            yield key, sorted(versions[key], key=self._arch_sortkey)

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

    @property
    def items(self):
        for item in self._data.items():
            yield item


Field = namedtuple('Field', ('name', 'title', 'value', 'presentation'))


FoundPackages = namedtuple(
    'FoundPackages',
    (
        'parameters',
        'other',
        'popularity_reports'
    )
)


class Interest(Enum):
    INTERESTING = 'i'
    BORING = 'b'
    NOVEL = 'n'


Repo = namedtuple('Repo', ('repo', 'reason'))


ValueAt = namedtuple('ValueAt', ('value', 'coords'))


class Version:
    def __init__(self, version, **kwargs):
        super().__init__()
        components = version.rsplit('_', 1)
        self.version = components[0]
        self.revision = components[1]
        self.data = kwargs
        self.verrev = version
