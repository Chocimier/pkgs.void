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

import sys
from collections import Counter, OrderedDict, defaultdict
from itertools import chain

import humanize

import datasource
import present
from custom_types import (
    Binpkgs, Field, FoundPackages,
    Interest, Repo, Response, ValueAt
)
from sink import same, now
from xbps import split_arch, verrev_from_pkgver, version_from_verrev
from workers.buildlog.buildlog import TASK_ERROR, TASK_PROCESSING, get_log


class RelevantProperty:
    def __init__(
            self, name,
            islist=False, formatter=None, combiner=None, parser=None
    ):
        # pylint: disable=too-many-arguments
        self.name = name
        self.islist = islist
        self.formatter = formatter or same
        self.combiner = combiner or present.combine_simple
        self.parser = parser or same


def _relevant_props():
    data = (
        {'name': 'short_desc'},
        {'name': 'homepage'},
        {'name': 'license'},
        {
            'name': 'maintainer',
            'parser': present.parse_contact
        },
        {'name': 'changelog'},
        {'name': 'repository'},
        {
            'name': 'build-date',
            'combiner': present.combine_minmax
        },
        {'name': 'build-options'},
        {
            'name': 'distfiles',
            'islist': True
        },
        {
            'name': 'installed_size',
            'combiner': present.combine_minmax
        },
        {
            'name': 'conflicts',
            'islist': True
        },
        {
            'name': 'provides',
            'islist': True
        },
        {
            'name': 'reverts',
            'islist': True
        },
        {
            'name': 'popularity',
            'combiner': present.combine_minmax
        },
        {
            'name': 'mainpkgname',
            'combiner': present.combine_set
        },
        {
            'name': 'upstreamver',
            'combiner': present.combine_set
        },
        {
            'name': 'shlib-provides',
            'islist': True
        },
        {
            'name': 'run_depends',
            'parser': set,
            'islist': True
        },
    )
    result = OrderedDict()
    for row in data:
        result[row['name']] = RelevantProperty(**row)
    return result


def _props_presentation(field):
    presentation = {
        'homepage': {'formatter': present.as_link},
        'changelog': {'formatter': present.as_link},
        'repository': {'formatter': present.as_repository},
        'build-date': {
            'formatter': present.as_date,
            'presenter': 'minmax',
        },
        'installed_size': {
            'formatter': present.as_size,
            'presenter': 'minmax',
        },
        'popularity': {'presenter': 'popularity'},
        'conflicts': {'formatter': present.as_package},
        'provides': {'formatter': present.as_package},
        'run_depends': {'formatter': present.as_package},
    }
    result = {
        'formatter': same,
        'presenter': None,
        **presentation.get(field, {})
    }
    return result


_RELEVANT_PROPS = _relevant_props()


_DISPLAY_FIELD_NAMES = {
    'build-date': 'Built at',
    'shlib-provides': 'Provided shlibs',
    'run_depends': 'Depending on',
    'mainpkg': 'Main package',
    'distfiles': 'Source files',
}


_RESTRICTED_BUILD_DATE = "It’s up to you"


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
    pkg['verrev'] = verrev_from_pkgver(pkg['pkgver'])
    pkg['version'] = version_from_verrev(pkg['verrev'])
    iset, libc = split_arch(row.arch)
    pkg['iset'] = iset
    pkg['libc'] = libc
    repo = separate_repository(row)
    if repo:
        pkg['repository'] = Repo(repo, row.restricted)
    pkg['mainpkgname'] = row.mainpkg
    pkg['upstreamver'] = row.upstreamver
    if row.builddate:
        pkg['build-date'] = row.builddate
    elif row.restricted:
        pkg['build-date'] = _RESTRICTED_BUILD_DATE
    if row.popularity is not None:
        pkg['popularity'] = row.popularity
    return pkg


def get_space(versions):
    space = [Counter(), Counter()]
    for i in versions.all:
        space[0][i.data['iset']] += 1
        space[1][i.data['libc']] += 1
    return space


def combine_fields(fields_dic, versions):
    fields = []
    space = get_space(versions)
    for field in fields_dic:
        prop = _RELEVANT_PROPS[field]
        field_title = display_field_name(field)
        field_content = prop.combiner(prop, fields_dic[field])
        presentation = {'space': space}
        fields.append(Field(field, field_title, field_content, presentation))
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
            separated[field.name] = field
        else:
            kept.append(field)
    fields[:] = kept
    return separated


def data_generator(pkgname, single):
    binpkgs = Binpkgs()
    source = datasource.factory()
    fields_dic = defaultdict(list)
    other_archs = False
    for row in source.read(pkgname=pkgname):
        if single and row.arch != single:
            other_archs = True
            continue
        pkg = make_pkg(row)
        binpkgs.add(pkg['verrev'], iset=pkg['iset'], libc=pkg['libc'])
        fields_dic_append(fields_dic, pkg)
    if not binpkgs:
        return FoundPackages(None, other_archs, None)
    fields = combine_fields(fields_dic, binpkgs)
    popularity_reports = next(source.auxiliary('popularity_reports'), None)
    if popularity_reports is None:
        fields = [i for i in fields if i.name != 'popularity']
    separated = separate_fields(fields, SEPARATED_FIELDS)
    upstreamver = new_versions(binpkgs, separated['upstreamver'].value)
    subpkgs = source.same_template(pkgname)
    return FoundPackages({
        'pkgname': pkgname,
        'short_desc': separated['short_desc'],
        'fields': fields,
        'versions': binpkgs,
        'mainpkg': {'pkgname': separated['mainpkgname']},
        'subpkgs': list(subpkgs),
        'upstreamver': upstreamver,
    }, other_archs, popularity_reports)


def page_generator(pkgname, single=None):
    found = data_generator(pkgname, single)
    parameters = found.parameters
    if not parameters:
        if not found.other:
            return find(pkgname, [])
        parameters = {
            'pkgname': pkgname,
            'other_archs': found.other,
        }
        return present.render_template('nopkg.html', **parameters).rstrip('\n')
    for field in chain(parameters['fields'], [parameters['short_desc']]):
        field.presentation.update(_props_presentation(field.name))
    parameters['single_pkg'] = single
    parameters['popularity_reports'] = found.popularity_reports
    return present.render_template('pkgs.void.html', **parameters)


def _update_time(source):
    return datasource.datetime_from_string(
        next(source.auxiliary('update_time'))
    )


def _ago(source):
    updated = _update_time(source)
    ago = humanize.naturaltime(now() - updated)
    updated_no_zone = updated.strftime('%Y-%m-%d %H:%M:%S')
    return f'{updated_no_zone} UTC ({ago})'


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


def find(term, fields):
    source = datasource.factory()
    packages = source.search(term, fields)
    all_fields = source.search_fields()
    parameters = {
        'fields': all_fields,
        'checked': fields or all_fields,
        'term': term,
    }
    if isinstance(packages, str):
        parameters['packages'] = []
        parameters['error'] = packages
    else:
        parameters['packages'] = list(packages)
        parameters['error'] = None
    return present.render_template('find.html', **parameters)


def of_day():
    source = datasource.factory()
    packages = source.of_day(now().date())
    parameters = {
        'title': 'Packages of the day',
        'packages': packages,
        'bullets': True,
    }
    return present.render_template('list.html', **parameters)


def which_package():
    return present.render_template('which.html')


def build_log(pkgname, arch, version):
    pkgver = f'{pkgname}-{version}'
    log = get_log(pkgver, arch)
    if log == TASK_PROCESSING:
        parameters = {
            'pkgver': pkgver,
            'arch': arch,
            'pkgname': pkgname,
            'version': version,
        }
        parameters['iset'], parameters['libc'] = split_arch(arch)
        content = present.render_template('buildlog.html', **parameters)
        return Response(content=content, redirect=None, error=None)
    if log == TASK_ERROR:
        text = 'Searching for build log failed, unfortunately.'
        content = present.render_paragraph(text=text)
        return Response(error=True, content=content, redirect=None)
    return Response(redirect=log, content=None, error=None)


class Collection:
    def __init__(self, dictionary):
        self._pkgname = dictionary['pkgname']
        interest = Interest(dictionary['classification'])
        # pylint: disable=superfluous-parens
        self.featured = (interest == Interest.BORING)

    def __str__(self):
        return self._pkgname


def metapackages():
    source = datasource.factory()
    packages = [Collection(i) for i in source.metapackages()]
    parameters = {
        'title': 'Package sets',
        'bullets': True,
        'packages': packages,
        'with_devel_and_so': True,
        'has_featured': any(i.featured for i in packages),
    }
    return present.render_template('list.html', **parameters)


def newest():
    source = datasource.factory()
    packages = source.newest(70)
    parameters = {
        'title': 'Newest packages',
        'subtitle': f'by {_ago(source)}',
        'packages': packages,
    }
    return present.render_template('list.html', **parameters)


def longest_names():
    source = datasource.factory()
    packages = source.longest_names(100)
    parameters = {
        'title': 'Packages with longest names',
        'packages': packages,
    }
    return present.render_template('list.html', **parameters)


def main_page():
    source = datasource.factory()
    lists = [
        {
            'title': 'Newest',
            'more': 'More newest',
            'address': 'newest',
            'packages': source.newest(20)
        },
        {
            'title': 'Popular',
            'more': 'More popular',
            'address': 'popular',
            'packages': source.popular(20)
        },
        {
            'title': 'Of day',
            'bullets': True,
            'address': 'of_day',
            'packages': source.of_day(now().date()),
        },
        {
            'title': 'Sets',
            'more': 'More sets',
            'bullets': True,
            'address': 'sets',
            'packages': [i['pkgname'] for i in source.metapackages([
                Interest.INTERESTING,
                Interest.NOVEL,
            ])]
        },
    ]
    parameters = {
        'title': 'Packages',
        'updated': _ago(source),
        'lists': lists,
    }
    return present.render_template('main.html', **parameters)


def popular():
    source = datasource.factory()
    packages = source.popular(70)
    parameters = {
        'title': 'Most popular packages',
        'subtitle': 'as reported by volunteers running PopCorn',
        'packages': packages,
        'with_devel_and_so': True,
    }
    return present.render_template('list.html', **parameters)


def lists_index():
    return present.render_template('toc.html')


def no_page():
    return present.render_paragraph('There is no such page.')


def opensearch_description(urlparts):
    server = urlparts._replace(path='', query='').geturl()
    return present.render_template(
        'opensearch.xml',
        present.SNIPPET,
        server=server
    )


def main():
    print(page_generator(sys.argv[1], sys.argv[2]))


if __name__ == '__main__':
    main()
