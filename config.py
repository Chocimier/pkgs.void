DAILY_HASH_BITS = 8

DATASOURCE_CLASS = 'SqliteDataSource'

DATASOURCE_ARGUMENTS = ['index.sqlite3']

DATASOURCE_ARGUMENTS_TEMPORARY = ['newindex.sqlite3']

DEVEL_MODE = False

ROOT_URL = '/pkgs.void'

REPOS = [
    'aarch64',
    'aarch64-musl',
    'armv6l',
    'armv6l-musl',
    'armv7l',
    'armv7l-musl',
    'i686',
    'multilib_x86_64',
    'x86_64',
    'x86_64-musl',
    'unknown-unknown',
]
