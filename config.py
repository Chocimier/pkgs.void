DAILY_HASH_BITS = 9

DATASOURCE_CLASS = 'SqliteDataSource'

DATASOURCE_ARGUMENTS = ['index.sqlite3']

DATASOURCE_ARGUMENTS_TEMPORARY = ['newindex.sqlite3']

DEVEL_MODE = False

ROOT_URL = '/pkgs.void'

ASSETS_URL = '/pkgs.void/static'

VOIDLINUX_URL = 'https://voidlinux.org'

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
