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

import sys
from collections import Counter, OrderedDict, defaultdict

import datasource
import present
from custom_types import Binpkgs, Field, ValueAt
from sink import same


class RelevantProperty:
    def __init__(self, name, islist=False, formatter=None, combiner=None, parser=None):
        from present import combine_simple
        self.name = name
        self.islist = islist
        self.formatter = formatter or same
        self.combiner = combiner or combine_simple
        self.parser = parser or same


DEFAULT_LIBC = 'glibc'


def split_arch(arch):
    try:
        iset, libc = arch.split('-')
    except ValueError:
        iset = arch
        libc = DEFAULT_LIBC
    return iset, libc


def join_arch(iset, libc):
    if not libc or libc == DEFAULT_LIBC:
        return iset
    return f'{iset}-{libc}'


def _relevant_props():
    data = (
        {'name': 'short_desc'},
        {'name': 'homepage', 'formatter': present.as_link},
        {'name': 'license'},
        {'name': 'maintainer', 'parser': present.parse_contact},
        {'name': 'changelog', 'formatter': present.as_link},
        {'name': 'repository', 'combiner': present.combine_with_template({
            'directory': 'repository',
            'to_template': (lambda value:
                            value if value == 'restricted' else 'additional')
        })},
        {
            'name': 'build-date',
            'formatter': present.as_date,
            'combiner': present.combine_minmax
        },
        {'name': 'build-options'},
        {'name': 'distfiles', 'islist': True},
        {
            'name': 'installed_size',
            'formatter': present.as_size,
            'combiner': present.combine_minmax
        },
        {
            'name': 'conflicts',
            'formatter': present.as_package,
            'islist': True
        },
        {
            'name': 'provides',
            'formatter': present.as_package,
            'islist': True
        },
        {'name': 'reverts', 'islist': True},
        {'name': 'mainpkgname', 'combiner': present.combine_simple},
        {'name': 'upstreamver', 'combiner': present.combine_set},
        {'name': 'shlib-provides', 'islist': True},
        {
            'name': 'run_depends',
            'formatter': present.as_package,
            'islist': True
        },
    )
    result = OrderedDict()
    for row in data:
        result[row['name']] = RelevantProperty(**row)
    return result


_RELEVANT_PROPS = _relevant_props()


_DISPLAY_FIELD_NAMES = {
    'build-date': 'Built at',
    'shlib-provides': 'Provided shlibs',
    'run_depends': 'Depending on',
    'mainpkg': 'Main package',
    'distfiles': 'Source files',
}


def display_field_name(field):
    try:
        return _DISPLAY_FIELD_NAMES[field]
    except KeyError:
        display = field
        display = display.replace('_', ' ')
        display = display.replace('-', ' ')
        display = display.capitalize()
        return display


def separate_repository(row):
    if row.restricted:
        return 'restricted'
    if 'multilib/nonfree' in row.repo:
        return 'multilib-nonfree'
    if 'nonfree' in row.repo:
        return 'nonfree'
    if 'multilib' in row.repo:
        return 'multilib'
    if 'debug' in row.repo:
        return 'debug'
    return None


def make_pkg(row):
    pkg = datasource.from_json(row.templatedata)
    pkg.update(datasource.from_json(row.repodata))
    pkg['verrev'] = pkg['pkgver'].rpartition('-')[-1]
    pkg['version'] = pkg['verrev'].partition('_')[0]
    iset, libc = split_arch(row.arch)
    pkg['iset'] = iset
    pkg['libc'] = libc
    repo = separate_repository(row)
    if repo:
        pkg['repository'] = repo
    pkg['mainpkgname'] = pkg.get('source-revisions', row.pkgname).split(':')[0]
    pkg['upstreamver'] = row.upstreamver
    return pkg


def get_space(versions):
    space = [Counter(), Counter()]
    for i in versions.all:
        space[0][i.data['iset']] += 1
        space[1][i.data['libc']] += 1
    return space


def combine_fields(fields_dic, versions, pkgname):
    fields = []
    space = get_space(versions)
    for field in fields_dic:
        prop = _RELEVANT_PROPS[field]
        field_title = display_field_name(field)
        field_content = prop.combiner(
            prop,
            fields_dic[field],
            space=space,
            pkgname=pkgname
        )
        fields.append(Field(field, field_title, field_content))
    return fields


def new_versions(binpkgs, upstream):
    packaged = set(i.version for i in binpkgs.all)
    upstream = set(i for i in upstream if i)
    return upstream.difference(packaged)


def fields_dic_append(fields_dic, pkg):
    for field, prop in _RELEVANT_PROPS.items():
        if field in pkg:
            value = prop.parser(pkg[field])
            coords = [pkg['iset'], pkg['libc']]
            fields_dic[field].append(ValueAt(value, coords))


SEPARATED_FIELDS = [
    'short_desc',
    'mainpkgname',
    'upstreamver'
]


def separate_fields(fields, separate):
    kept = []
    separated = {}
    for field in fields:
        if field.name in separate:
            separated[field.name] = field.value
        else:
            kept.append(field)
    fields[:] = kept
    return separated


def data_generator(pkgname, repos):
    binpkgs = Binpkgs()
    source = datasource.factory()
    fields_dic = defaultdict(list)
    for row in source.read(pkgname=pkgname):
        if row.arch not in repos:
            continue
        pkg = make_pkg(row)
        binpkgs.add(pkg['verrev'], iset=pkg['iset'], libc=pkg['libc'])
        fields_dic_append(fields_dic, pkg)
    if not binpkgs:
        return None
    fields = combine_fields(fields_dic, binpkgs, pkgname)
    separated = separate_fields(fields, SEPARATED_FIELDS)
    upstreamver = new_versions(binpkgs, separated['upstreamver'])
    return {
        'pkgname': pkgname,
        'short_desc': separated['short_desc'],
        'fields': fields,
        'versions': binpkgs,
        'mainpkg': {'pkgname': separated['mainpkgname']},
        'upstreamver': upstreamver,
    }


def page_generator(pkgname, repos, single=False):
    parameters = data_generator(pkgname, repos)
    if not parameters:
        parameters = {
            'pkgname': pkgname,
        }
        return present.render_template('nopkg.html', **parameters)
    template = '{}.void.html'.format(
        'single_pkg' if single else 'pkgs'
    )
    return present.render_template(template, **parameters)


def list_all():
    source = datasource.factory()
    packages = source.list_all()
    parameters = {
        'packages': ({
            'pkgname': i.pkgname,
            'short_desc': (
                datasource.from_json(i.repodata).get('short_desc') or
                datasource.from_json(i.templatedata).get('short_desc')
                )
            } for i in packages),
    }
    return present.render_template('all.html', **parameters)


def newest():
    source = datasource.factory()
    packages = source.newest(50)
    parameters = {
        'packages': packages,
    }
    return present.render_template('newest.html', **parameters)


def main():
    print(page_generator(sys.argv[1], sys.argv[2:]))


if __name__ == '__main__':
    main()
