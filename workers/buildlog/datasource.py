# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2019-2024 Piotr Wójcik <chocimier@tlen.pl>
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
import sqlite3
from collections import namedtuple

from settings import load_config

config = load_config('buildlog')


CONFIRMED = 'confirmed'
ERROR = 'error'
GUESS = 'guess'
REFUTED = 'refuted'


Batch = namedtuple(
    'Batch',
    (
        'arch',
        'batchnumber',
        'state',
    )
)


MaximalBatch = namedtuple(
    'MaximalBatch',
    (
        'arch',
        'batchnumber',
    )
)


_Package = namedtuple(
    'Package',
    (
        'pkgname',
        'pkgver',
        'arch',
        'batchnumber',
        'state',
    )
)


class Package(_Package):
    def __new__(
            cls,
            *,
            pkgname,
            pkgver,
            arch,
            batchnumber,
            state,
    ):
        # pylint: disable=unused-argument,too-many-arguments
        function_locals = locals()
        fields = {f: function_locals[f] for f in _Package._fields}
        return super().__new__(cls, **fields)

    @staticmethod
    def from_record(record):
        return Package(**dict(zip(_Package._fields, record)))


class Datasource(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __enter__(self):
        '''Enters runtime context.'''

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        '''Exits runtime context.'''

    @abc.abstractmethod
    def create(self, build_row):
        '''Saves information about build into database.'''

    @abc.abstractmethod
    def read(self, **kwargs):
        '''Finds packages that match criteria passed as keyword arguments.'''

    @abc.abstractmethod
    def update(self, **kwargs):
        '''Finds packages matching criteria passed as keyword arguments
        and sets values passed as keyword arguments prefixed with 'set_'.
        '''

    @abc.abstractmethod
    def create_batch(self, batch):
        pass

    @abc.abstractmethod
    def set_max_batch(self, arch, number):
        pass

    @abc.abstractmethod
    def unfetched_builds(self, arch, count):
        '''Returns numbers of not fetched packages.'''

    @abc.abstractmethod
    def random_arch(self):
        '''Returns iterable of one random known arch builder, if any.'''


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

    def _initialize(self):
        self._cursor.execute('''CREATE TABLE IF NOT EXISTS packages (
            pkgname text NOT NULL,
            pkgver text,
            arch text NOT NULL,
            batchnumber integer NOT NULL,
            state text NOT NULL)
            ''')
        self._cursor.execute('''CREATE TABLE IF NOT EXISTS batches (
            arch text NOT NULL,
            batchnumber integer NOT NULL,
            state text NOT NULL)
            ''')
        self._cursor.execute('''CREATE TABLE IF NOT EXISTS maximal_batch (
            arch text PRIMARY KEY,
            batchnumber integer NOT NULL)
            ''')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._db.commit()
        self._db.close()

    def create(self, build_row):
        '''Saves information about package into database.'''
        query = 'INSERT INTO packages ({}) VALUES ({})'.format(
            ', '.join(Package._fields),
            ', '.join('?' * len(Package._fields))
        )
        self._cursor.execute(query, build_row)

    def read(self, **kwargs):
        '''Finds packages that match criteria passed as keyword arguments.'''
        fixed = [i for i in kwargs if i in Package._fields]
        query = 'SELECT {} FROM packages WHERE {}'.format(
            ', '.join(Package._fields),
            ' AND '.join(f'{i} = ?' for i in fixed)
        )
        self._cursor.execute(query, [kwargs[i] for i in fixed])
        return (Package.from_record(x) for x in self._cursor.fetchall())

    @staticmethod
    def _sets(argname):
        prefix = 'set_'
        if argname.startswith(prefix):
            return argname[len(prefix):]
        return None

    def update(self, **kwargs):
        '''Finds packages matching criteria passed as keyword arguments
        and sets values passed as keyword arguments prefixed with 'set_'.
        '''
        updated = [i for i in kwargs if self._sets(i) in Package._fields]
        fixed = [
            i
            for i in kwargs
            if not self._sets(i) and i in Package._fields
        ]
        query = 'UPDATE packages SET {} WHERE {}'.format(
            ', '.join('{} = ?'.format(self._sets(i)) for i in updated),
            ' AND '.join('{} = ?'.format(i) for i in fixed) or True
        )
        self._cursor.execute(query, [kwargs[i] for i in updated + fixed])

    def create_batch(self, batch):
        '''Saves information about package into database.'''
        query = 'INSERT INTO batches ({}) VALUES ({})'.format(
            ', '.join(Batch._fields),
            ', '.join('?' * len(Batch._fields))
        )
        self._cursor.execute(query, batch)

    def set_max_batch(self, arch, number):
        query = '''INSERT INTO maximal_batch (arch, batchnumber)
            VALUES (?, ?)
            ON CONFLICT(arch) DO UPDATE SET
            batchnumber = excluded.batchnumber
            WHERE batchnumber < excluded.batchnumber'''
        self._cursor.execute(query, [arch, number])

    def unfetched_builds(self, arch, count):
        query = '''WITH RECURSIVE seq(n) AS (
               SELECT 1
               UNION
               SELECT n + 1 from seq
               LIMIT (SELECT batchnumber FROM maximal_batch WHERE arch = :arch)
            )
            SELECT n as batchnumber FROM seq
            EXCEPT
            SELECT batchnumber FROM batches
            WHERE arch = :arch
            ORDER BY batchnumber DESC
            LIMIT :count'''
        self._cursor.execute(query, {'arch': arch, 'count': count})
        return (i[0] for i in self._cursor.fetchall())

    def random_arch(self):
        query = '''SELECT arch FROM maximal_batch
            ORDER BY random()
            LIMIT 1'''
        self._cursor.execute(query, [])
        return (i[0] for i in self._cursor.fetchall())


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
        return func(source)
