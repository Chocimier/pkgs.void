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

import abc
import json
import sqlite3
from collections import namedtuple

import config
from sink import string_hash


PackageRow = namedtuple(
    'PackageRow',
    (
        'pkgname',
        'pkgname_hash',
        'pkgver',
        'arch',
        'restricted',
        'repodata',
        'templatedata',
        'upstreamver',
        'repo',
    )
)


def to_json(dictionary):
    return json.dumps(dictionary, sort_keys=True)


def from_json(text):
    return json.loads(text)


class Datasource(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __enter__(self):
        '''Enters runtime context.'''

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        '''Exits runtime context.'''

    @abc.abstractmethod
    def create(self, package_row):
        '''Saves information about package into database.'''

    @abc.abstractmethod
    def read(self, **kwargs):
        '''Finds packages that match criteria passed as keyword arguments.'''

    @abc.abstractmethod
    def list_all(self):
        '''Returns list of all packages.'''

    @abc.abstractmethod
    def update(self, **kwargs):
        '''Finds packages matching criteria passed as keyword arguments
        and sets values passed as keyword arguments prefixed with 'set_'.'''

    @abc.abstractmethod
    def delete(self, **kwargs):
        '''Removes from storage packages that match criteria
        passed as keyword arguments'''

    @abc.abstractmethod
    def of_day(self, date):
        '''Returns different packages every day'''

    @abc.abstractmethod
    def longest_names(self, at_most):
        '''Finds names of packages having name longer than '''
        '''at_most-th longest-name-bearing package'''

    @abc.abstractmethod
    def finish_creating(self):
        '''Creates indices after data is stored'''


class SqliteDataSource(Datasource):
    def __init__(self, path):
        self._db = sqlite3.connect(path)
        self._cursor = self._db.cursor()
        self._initialize()

    def _initialize(self):
        self._cursor.execute('''create table if not exists packages (
            arch text not null,
            pkgname text not null,
            pkgname_hash text not null,
            pkgver text not null,
            restricted integer not null,
            repodata text not null,
            templatedata text not null,
            upstreamver text not null,
            repo text not null)
            ''')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._db.commit()
        self._db.close()

    def create(self, package_row):
        '''Saves information about package into database.'''
        query = 'INSERT INTO packages ({}) VALUES ({})'.format(
            ', '.join(PackageRow._fields),
            ', '.join('?' * len(package_row))
        )
        self._cursor.execute(query, package_row)

    def read(self, **kwargs):
        '''Finds packages that match criteria passed as keyword arguments.'''
        fixed = [i for i in kwargs if i in PackageRow._fields]
        query = 'SELECT {} FROM packages WHERE {}'.format(
            ', '.join(PackageRow._fields),
            ' AND '.join(f'{i} = ?' for i in fixed)
        )
        self._cursor.execute(query, [kwargs[i] for i in fixed])
        return (PackageRow(*x) for x in self._cursor.fetchall())

    def list_all(self):
        '''Returns list of all packages.'''
        query = 'SELECT {} FROM packages group by pkgname'.format(
            ', '.join(PackageRow._fields),
        )
        self._cursor.execute(query)
        return [PackageRow(*x) for x in self._cursor.fetchall()]

    @staticmethod
    def _sets(argname):
        prefix = 'set_'
        if argname.startswith(prefix):
            return argname[len(prefix):]
        return None

    def update(self, **kwargs):
        '''Finds packages matching criteria passed as keyword arguments
        and sets values passed as keyword arguments prefixed with 'set_'.'''
        updated = [i for i in kwargs if self._sets(i) in PackageRow._fields]
        fixed = [
            i
            for i in kwargs
            if not self._sets(i) and i in PackageRow._fields
        ]
        query = 'UPDATE packages SET {} WHERE {}'.format(
            ', '.join('{} = ?'.format(self._sets(i)) for i in updated),
            ' AND '.join('{} = ?'.format(i) for i in fixed)
        )
        self._cursor.execute(query, [kwargs[i] for i in updated + fixed])

    def delete(self, **kwargs):
        '''Removes from storage packages that match criteria
        passed as keyword arguments'''
        ...

    def of_day(self, date):
        '''Returns different packages every day'''
        query = (
            'select distinct pkgname from packages '
            'where repo not like "multilib%" '
            'and pkgname not like "%-devel" '
            'and pkgname not like "%-dbg" '
            'and pkgname_hash like ? || "%"'
            'order by pkgname'
        )
        self._cursor.execute(query, [string_hash(date)[:2]])
        return (x[0] for x in self._cursor.fetchall())

    def longest_names(self, at_most):
        '''Finds names of packages having name longer than '''
        '''at_most-th longest-name-bearing package'''
        query = (
            'select distinct pkgname from packages '
            'where repo not like "multilib%" '
            'and pkgname not like "%-devel" '
            'and pkgname not like "%-dbg" '
            'and length(pkgname) > ('
            '  select length(pkgname) from ('
            '    select distinct pkgname '
            '    from packages '
            '    where repo not like "multilib%" '
            '    and pkgname not like "%-devel" '
            '    and pkgname not like "%-dbg" '
            '  )'
            '  order by length(pkgname) desc'
            '  limit 1 offset ?'
            ')'
            'order by pkgname'
        )
        self._cursor.execute(query, [int(at_most)])
        return (x[0] for x in self._cursor.fetchall())

    def finish_creating(self):
        self._cursor.execute('''create index if not exists pkgname_idx
            on packages (
            pkgname
            )
            ''')
        self._cursor.execute('''create index if not exists pkgname_hash_idx
            on packages (
            pkgname_hash
            )
            ''')


def custom_factory(classname, *args, **kwargs):
    return globals()[classname](*args, **kwargs)


def datasource_arguments(temporary):
    if temporary:
        return config.DATASOURCE_ARGUMENTS_TEMPORARY
    return config.DATASOURCE_ARGUMENTS


def factory(temporary=False):
    return custom_factory(
        config.DATASOURCE_CLASS,
        *datasource_arguments(temporary=temporary)
    )


def update(func):
    with factory(temporary=True) as source:
        func(source)
        source.finish_creating()
