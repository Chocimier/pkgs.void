# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2019-2020 Piotr Wójcik <chocimier@tlen.pl>
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
import hashlib
import json
import sqlite3
from collections import namedtuple

import config
from xbps import pkgname_from_pkgver


_PackageRow = namedtuple(
    'PackageRow',
    (
        'pkgname',
        'pkgver',
        'arch',
        'restricted',
        'builddate',
        'repodata',
        'templatedata',
        'mainpkg',
        'depends_count',
        'upstreamver',
        'repo',
        'popularity',
    )
)


class PackageRow(_PackageRow):
    def __new__(
            cls,
            *,
            pkgver,
            arch,
            repo,
            pkgname=None,
            restricted=False,
            builddate='',
            repodata=None,
            templatedata=None,
            mainpkg='',
            depends_count=None,
            upstreamver='',
            popularity=0,
    ):
        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-locals
        # pylint: disable=unused-argument
        def to_jsondata(arg):
            if isinstance(arg, str):
                return arg
            if arg is None:
                return to_json({})
            return to_json(arg)
        if not pkgname:
            pkgname = pkgname_from_pkgver(pkgver)
        repodata = to_jsondata(repodata)
        templatedata = to_jsondata(templatedata)
        function_locals = locals()
        fields = {f: function_locals[f] for f in _PackageRow._fields}
        return super().__new__(cls, **fields)

    @staticmethod
    def from_record(record):
        return PackageRow(**dict(zip(_PackageRow._fields, record)))


def to_json(dictionary):
    return json.dumps(dictionary, sort_keys=True)


def from_json(text):
    return json.loads(text)


def date_as_string(date):
    return date.strftime('%Y-%m-%d')


def dailyable(package_row):
    return (
        not package_row.repo.startswith('multilib')
        and not package_row.pkgname.endswith('-devel')
        and not package_row.pkgname.endswith('-dbg')
    )


def daily_hash(pkgname, date, bits=None):
    '''We want to select small (around 50) subset of packages
    with following properties:
    - changing daily
    - not partitioning: every pair of packages has chance to be chosen some day
    - precomputable: not forcing to process every package to select
    - adding or removing package do not affect choise of other packages
    - size may vary
    To achieve this, we compute hash of pair of pkgname and date.
    Then package is chosen when such hash has common prefix with hash of date.
    Lenght of prefix in bits is adjusted such that set has required size.
    '''
    string = pkgname + date_as_string(date)
    hash_value = hashlib.md5(string.encode()).digest()
    integer = int.from_bytes(hash_value, 'big')
    binary = "{num:0{width}b}".format(num=integer, width=8*len(hash_value))
    return binary[:bits]


class Datasource(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __enter__(self):
        '''Enters runtime context.'''

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        '''Exits runtime context.'''

    @abc.abstractmethod
    def create(self, package_row, dates):
        '''Saves information about package into database.
        Computes if it is daily package, and register if so.'''

    @abc.abstractmethod
    def read(self, **kwargs):
        '''Finds packages that match criteria passed as keyword arguments.'''

    @abc.abstractmethod
    def same_template(self, pkgname):
        '''Returns names of packages built from same template.'''

    @abc.abstractmethod
    def list_all(self):
        '''Returns list of all packages.'''

    @abc.abstractmethod
    def update(self, **kwargs):
        '''Finds packages matching criteria passed as keyword arguments
        and sets values passed as keyword arguments prefixed with 'set_'.'''

    @abc.abstractmethod
    def of_day(self, date):
        '''Returns different packages every day'''

    @abc.abstractmethod
    def metapackages(self):
        '''Returns names of packages that solely depend on other packages.'''

    @abc.abstractmethod
    def newest(self, count):
        '''Finds names of _count_ most recently build packages'''

    @abc.abstractmethod
    def popular(self, at_most):
        '''Finds names of packages being more popular than
        at_most-th most popular package'''

    @abc.abstractmethod
    def longest_names(self, at_most):
        '''Finds names of packages having name longer than
        at_most-th longest-name-bearing package'''

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
            pkgver text not null,
            restricted integer not null,
            builddate text not null,
            repodata text not null,
            templatedata text not null,
            mainpkg text not null,
            depends_count integer,
            upstreamver text not null,
            repo text not null,
            popularity integer default 0)
            ''')
        self._cursor.execute('''create table if not exists daily_hash (
            pkgname text not null,
            date text not null,
            unique(pkgname, date)
            )
            ''')
        self._cursor.execute('''create table if not exists metapackages (
            pkgname text unique not null
            )
            ''')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._db.commit()
        self._db.close()

    def create(self, package_row, dates):
        '''Saves information about package into database.
        Computes if it is daily package, and register if so.'''
        query = 'INSERT INTO packages ({}) VALUES ({})'.format(
            ', '.join(PackageRow._fields),
            ', '.join('?' * len(package_row))
        )
        self._cursor.execute(query, package_row)
        self._add_daily_hashes(package_row, dates)
        self._register_metapackage(package_row)

    def _add_daily_hashes(self, package_row, dates):
        if not dailyable(package_row):
            return
        hash_query = '''INSERT OR IGNORE INTO daily_hash (pkgname, date)
            VALUES (?, ?)'''
        for date in dates:
            hash_value = daily_hash(
                package_row.pkgname,
                date,
                config.DAILY_HASH_BITS
            )
            if daily_hash('', date).startswith(hash_value):
                self._cursor.execute(
                    hash_query,
                    (package_row.pkgname, date_as_string(date))
                )

    def _register_metapackage(self, package_row):
        pkgname = package_row.pkgname
        if (package_row.depends_count
                and package_row.depends_count > 1
                and not pkgname.endswith('-32bit')
                and '"installed_size": 0' in package_row.repodata):
            query = '''INSERT OR IGNORE INTO metapackages (pkgname)
                VALUES (?)'''
            self._cursor.execute(
                query,
                [pkgname]
            )

    def read(self, **kwargs):
        '''Finds packages that match criteria passed as keyword arguments.'''
        fixed = [i for i in kwargs if i in PackageRow._fields]
        query = 'SELECT {} FROM packages WHERE {}'.format(
            ', '.join(PackageRow._fields),
            ' AND '.join(f'{i} = ?' for i in fixed)
        )
        self._cursor.execute(query, [kwargs[i] for i in fixed])
        return (PackageRow.from_record(x) for x in self._cursor.fetchall())

    def same_template(self, pkgname):
        '''Returns names of packages built from same template.'''
        query = ('select distinct second.pkgname '
                 'from packages as first '
                 'join packages as second '
                 'on first.mainpkg = second.mainpkg '
                 'where first.pkgname = ? '
                 'order by second.pkgname')
        self._cursor.execute(query, [pkgname])
        return (x[0] for x in self._cursor.fetchall())

    def list_all(self):
        '''Returns list of all packages.'''
        query = 'SELECT {} FROM packages group by pkgname'.format(
            ', '.join(PackageRow._fields),
        )
        self._cursor.execute(query)
        return (PackageRow.from_record(x) for x in self._cursor.fetchall())

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

    def of_day(self, date):
        '''Returns different packages every day'''
        query = (
            'select pkgname from daily_hash '
            'where date = ?'
            'order by pkgname'
        )
        self._cursor.execute(query, [date_as_string(date)])
        return (x[0] for x in self._cursor.fetchall())

    def metapackages(self):
        '''Returns names of packages that solely depend on other packages.'''
        query = (
            'select pkgname from metapackages '
            'order by pkgname '
        )
        self._cursor.execute(query, [])
        return (x[0] for x in self._cursor.fetchall())

    def newest(self, count):
        '''Finds names of _count_ most recently build packages'''
        query = (
            'select distinct pkgname from packages '
            'where repo not like "multilib%" '
            'and pkgname not like "%-devel" '
            'and pkgname not like "%-dbg" '
            "and builddate != '' "
            'order by builddate desc '
            'limit ?'
        )
        self._cursor.execute(query, [int(count)])
        return (x[0] for x in self._cursor.fetchall())

    def popular(self, at_most):
        '''Finds names of packages being more popular than
        at_most-th most popular package'''
        query = (
            'select distinct pkgname from packages '
            'where popularity > ('
            '  select popularity from ('
            '    select distinct pkgname, popularity '
            '    from packages '
            '    where popularity > 0 '
            '    order by popularity desc'
            '    limit 1 offset ?'
            '  )'
            ')'
            'order by popularity desc'
        )
        self._cursor.execute(query, [int(at_most)])
        return (x[0] for x in self._cursor.fetchall())

    def longest_names(self, at_most):
        '''Finds names of packages having name longer than
        at_most-th longest-name-bearing package'''
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
        self._cursor.execute('''create index if not exists pkgver_idx
            on packages (
            pkgver
            )
            ''')
        self._cursor.execute('''create index if not exists builddate_idx
            on packages (
            builddate desc
            )
            ''')
        self._cursor.execute('''create index if not exists mainpkg_idx
            on packages (
            mainpkg,
            pkgname
            )
            ''')
        self._cursor.execute('''create index if not exists popularity_idx
            on packages (
            popularity
            )
            ''')
        self._cursor.execute('''create index if not exists daily_hash_idx
            on daily_hash (
            date
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
