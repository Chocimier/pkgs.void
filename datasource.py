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

import abc
import datetime
import hashlib
import sqlite3
from collections import namedtuple

import ujson as json

from settings import config
import sink
from custom_types import Interest
from metadata import MetapackageInterest
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


def datetime_to_string(datetime_obj):
    return datetime_obj.isoformat()


def datetime_from_string(string):
    return datetime.datetime.fromisoformat(string)


def _date_as_string(date):
    return date.strftime('%Y-%m-%d')


def dailyable(package_row):
    return (
        not package_row.repo.startswith('multilib')
        and not package_row.pkgname.endswith('-devel')
        and not package_row.pkgname.endswith('-dbg')
    )


def daily_hash(pkgname, date, bits=None):
    '''We want to select small (around 20) subset of packages
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
    string = pkgname + _date_as_string(date)
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

    @staticmethod
    @abc.abstractmethod
    def search_fields():
        '''Returns names of searchable fields'''

    @abc.abstractmethod
    def search(self, term, fields):
        '''Searches for packages described by term.
        Returns iterator of dictionaries with keys 'name', 'description'.'''

    @abc.abstractmethod
    def update(self, **kwargs):
        '''Finds packages matching criteria passed as keyword arguments
        and sets values passed as keyword arguments prefixed with 'set_'.'''

    @abc.abstractmethod
    def of_day(self, date):
        '''Returns different packages every day.'''

    @abc.abstractmethod
    def metapackages(self, allowed=None):
        '''Returns names of packages that solely depend on other packages,
        optionally limited to _allowed_ statuses.'''

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
    def add_auxiliary(self, key, value):
        '''Sets auxiliary values of _key_.'''

    @abc.abstractmethod
    def auxiliary(self, key):
        '''Returns auxiliary values of _key_.'''

    @abc.abstractmethod
    def finish_creating(self):
        '''Creates indices after data is stored'''


class SqliteDataSource(Datasource):
    def __init__(self, path, mode):
        '''Opens datasource stored as sqlite database.
        path: path of database file
        mode: 'read' or 'write'
        '''
        self._db = sqlite3.connect(path)
        self._cursor = self._db.cursor()
        if mode == 'write':
            self._initialize()
            self.metadata_interest = MetapackageInterest()

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
        self._cursor.execute('''create table if not exists pkgnames (
            pkgname text primary key,
            same_template text not null
            )
            ''')
        self._cursor.execute('''create table if not exists metapackages (
            pkgname text unique not null,
            classification text not null
            )
            ''')
        time = datetime_to_string(sink.now().replace(microsecond=0))
        self._cursor.execute('''create table if not exists auxiliary
            as select ? as key, ? as value
            ''', ['update_time', time])
        self._cursor.execute('''create virtual table if not exists
            search_terms using fts4(
            {},
            tokenize=porter
            )
            '''.format(', '.join(self.search_fields())))

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
            ', '.join('?' * len(PackageRow._fields))
        )
        self._cursor.execute(query, package_row)
        self._add_search_terms(package_row)
        self._add_daily_hashes(package_row, dates)
        self._register_metapackage(package_row)

    def _add_search_terms(self, package_row):
        for data in (package_row.repodata, package_row.templatedata):
            self._add_search_terms_from_data(package_row.pkgname, data)

    def _add_search_terms_from_data(self, pkgname, data):
        data = from_json(data)
        if not data:
            return
        query = 'INSERT INTO search_terms ({}) VALUES ({})'.format(
            ', '.join(self.search_fields()),
            ', '.join('?' * len(self.search_fields()))
        )
        self._cursor.execute(query, (
            pkgname,
            data.get('short_desc'),
            data.get('homepage'),
            ))

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
                    (package_row.pkgname, _date_as_string(date))
                )

    def _register_metapackage(self, package_row):
        pkgname = package_row.pkgname
        repodata = package_row.repodata
        if (package_row.depends_count
                and package_row.depends_count > 1
                and not pkgname.endswith('-32bit')
                and from_json(repodata).get('installed_size') == 0):
            query = '''INSERT OR IGNORE INTO metapackages
                (pkgname, classification)
                VALUES (?, ?)'''
            self._cursor.execute(
                query,
                [pkgname, self.metadata_interest.get(pkgname).value]
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
        query = ('SELECT pkgname '
                 'FROM pkgnames '
                 'WHERE same_template = ('
                 '  SELECT same_template '
                 '  FROM pkgnames '
                 '  WHERE pkgname = ? '
                 ') '
                 'ORDER BY pkgname')
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
    def search_fields():
        '''Returns names of searchable fields'''
        return (
            'name',
            'description',
            'homepage',
            )

    def search(self, term, fields):
        '''Searches for packages described by term.
        Returns iterator of dictionaries with keys 'name', 'description'.'''
        effective_fields = (
            set(self.search_fields()).intersection(fields)
            or self.search_fields()
        )
        query = '''select distinct name, description from search_terms
            where {}
            order by name'''.format(
                ' or '.join(f'{f} match ?' for f in effective_fields)
            )
        try:
            self._cursor.execute(query, [term]*len(effective_fields))
        except sqlite3.OperationalError:
            return 'Invalid search term'
        keys = ('name', 'description')
        return (dict(zip(keys, vals)) for vals in self._cursor.fetchall())

    @staticmethod
    def _sets(argname):
        prefix = 'set_'
        if argname.startswith(prefix):
            return argname[len(prefix):]
        return None

    def update(self, **kwargs):
        '''Finds packages matching criteria passed as keyword arguments
        and sets values passed as keyword arguments prefixed with 'set_'.

        NOTE: update of search_terms is done only for usage
        existing at the time of writing, that is adding templatedata
        '''
        updated = [i for i in kwargs if self._sets(i) in PackageRow._fields]
        fixed = [
            i
            for i in kwargs
            if not self._sets(i) and i in PackageRow._fields
        ]
        query = 'UPDATE packages SET {} WHERE {}'.format(
            ', '.join('{} = ?'.format(self._sets(i)) for i in updated),
            ' AND '.join('{} = ?'.format(i) for i in fixed) or True
        )
        self._cursor.execute(query, [kwargs[i] for i in updated + fixed])
        pkgname = kwargs.get('pkgname')
        templatedata = kwargs.get('set_templatedata')
        if pkgname and templatedata:
            self._add_search_terms_from_data(pkgname, templatedata)

    def of_day(self, date):
        '''Returns different packages every day'''
        query = (
            'select pkgname from daily_hash '
            + 'where date = ?'
            + 'order by pkgname'
        )
        self._cursor.execute(query, [_date_as_string(date)])
        return (x[0] for x in self._cursor.fetchall())

    def metapackages(self, allowed=None):
        '''Returns names of packages that solely depend on other packages,
        optionally limited to _allowed_ statuses.'''
        where = ''
        if allowed:
            where = 'where classification in ({})  '.format(
                ', '.join('?'*len(allowed))
            )
        query = (
            'select pkgname, classification from metapackages '
            + where
            + 'order by pkgname '
        )
        self._cursor.execute(query, [i.value for i in (allowed or [])])
        return (
            {'pkgname': x[0], 'classification': Interest(x[1])}
            for x in self._cursor.fetchall()
        )

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

    def add_auxiliary(self, key, value):
        '''Sets auxiliary values of _key_.'''
        query = (
            'INSERT INTO auxiliary (key, value)'
            'VALUES (?, ?)'
        )
        self._cursor.execute(query, [key, value])

    def auxiliary(self, key):
        '''Returns auxiliary values of _key_.'''
        query = (
            'select value from auxiliary '
            'where key = ? '
        )
        self._cursor.execute(query, [key])
        return (x[0] for x in self._cursor.fetchall())

    def finish_creating(self):
        self._cursor.execute('''insert into
            search_terms(search_terms)
            values('optimize')
            ''')
        self._cursor.execute('''insert or replace into
            pkgnames(pkgname, same_template)
            select first.pkgname, min(second.pkgname)
                from packages as first
                join packages as second
                on first.mainpkg = second.mainpkg
                group by first.pkgname
            ''')
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
        self._cursor.execute('''create index if not exists group_idx
            on pkgnames (
            same_template
            )
            ''')


def custom_factory(classname, *args, **kwargs):
    return globals()[classname](*args, **kwargs)


def datasource_arguments(temporary):
    if temporary:
        return config.DATASOURCE_ARGUMENTS_TEMPORARY.split(',')
    return config.DATASOURCE_ARGUMENTS.split(',')


def factory(temporary=False):
    return custom_factory(
        config.DATASOURCE_CLASS,
        *datasource_arguments(temporary=temporary)
    )


def update(func):
    with factory(temporary=True) as source:
        func(source)
        source.finish_creating()
