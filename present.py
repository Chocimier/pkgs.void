# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2019-2023 Piotr Wójcik <chocimier@tlen.pl>
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

from collections import Counter, namedtuple
from urllib.parse import quote as urlquote

# pylint can't import modules from create_module, so import-error
# some functions are used only in templates, so unused-import
# above makes lines too long, so noqa
import tenjin.helpers  # pylint: disable=import-error
from humanize import naturalsize
from tenjin import MemoryCacheStorage, SafeEngine, SafePreprocessor
from tenjin.escaped import as_escaped, to_escaped  # noqa, pylint: disable=import-error
from tenjin.helpers import echo, to_str  # noqa, pylint: disable=unused-import,import-error

from custom_types import ValueAt
from settings import config


Area = namedtuple('Area', ('value', 'coords'))


class CustomPreprocessor(SafePreprocessor):
    def _localvars_assignments(self):
        '''
        Preprocessor calls _decode_params without defining it
        '''
        return (
            super()._localvars_assignments()
            + "_decode_params = tenjin.helpers._decode_params;"
        )


class LoaderCache:
    def __init__(self):
        self.engine = None

    def loader(self):
        if config.DEVEL_MODE or self.engine is None:
            self.engine = SafeEngine(
                path=['templates'],
                preprocess=True,
                preprocessorclass=CustomPreprocessor,
                cache=MemoryCacheStorage()
            )
        return self.engine


_loader_cache = LoaderCache()
_loader = _loader_cache.loader


def web_parameters():
    return {
        'root_url': config.ROOT_URL,
        'assets_url': config.ASSETS_URL,
        'voidlinux_url': config.VOIDLINUX_URL,
        'generated_files_url': config.GENERATED_FILES_URL,
        'urlquote': urlquote,
    }


def parse_contact(value):
    return value.split('<')[0].strip()


def render_link(href, text):
    code = '<a href="{}">{}</a>'
    return as_escaped(code.format(
        tenjin.helpers.escape(href),
        tenjin.helpers.escape(text)
    ))


def _masks_as_string(masks_set):
    return ', '.join(map('-'.join, masks_set))


def _masks_presenter(values, space):
    masks_set = _masks(values, space) or {}
    return _masks_as_string(masks_set)


SNIPPET = object()


def render_template(template_path, template_mode=None, **kwargs):
    context = {
        'masks_presenter': _masks_presenter,
        **web_parameters(),
        **kwargs
    }
    if template_mode is SNIPPET:
        return as_escaped(_loader().render(template_path, context))
    return _loader().render(template_path, context, layout='base.html')


def render_paragraph(text):
    return render_template('paragraph.html', text=text)


def as_new_version(versions):
    return render_template(
        'small/as_new_version.html',
        SNIPPET, versions=versions
    )


def as_package(value):
    pkgname = value
    pkgver = ''
    for char in '><-':
        pos = value.rfind(char)
        if pos >= 0:
            pkgname = value[:pos]
            pkgver = value[pos:]
            break
    if pkgver == '>=0':
        pkgver = ''
    href = config.ROOT_URL + '/package/' + urlquote(pkgname)
    if '_' in pkgver:
        pairs = []
        version = ''
        revision = ''
        while pkgver:
            if revision:
                if pkgver[0].isdigit():
                    revision += pkgver[0]
                else:
                    pairs.append((version, revision))
                    version = pkgver[0]
                    revision = ''
            else:
                if pkgver[0] == '_':
                    revision = pkgver[0]
                else:
                    version += pkgver[0]
            pkgver = pkgver[1:]
        if version:
            pairs.append((version, revision))
        pkgver = render_template('small/as_package.html', SNIPPET, pairs=pairs)
    else:
        pkgver = to_escaped(pkgver)
    return as_escaped(
        render_link(href, pkgname)
        + as_escaped(pkgver.rstrip('\n'))
    )


def as_link(value):
    return render_link(value, value)


def as_date(value):
    return value


def as_popularity(value):
    return f'{value}'


def as_repository(value):
    name = (
        value.repo
        if value.repo in ['restricted', 'bootstrap']
        else 'additional'
    )
    return render_template(
        f'present/repository/{name}.html',
        SNIPPET,
        **value._asdict()
    )


def as_size(value):
    return naturalsize(value, binary=True, format='%.2f')


def _covering_labels(elems, space):
    for dim in reversed(range(len(space))):
        found = True
        having = Counter()
        for elem in elems:
            having[elem[dim]] += 1
        for point in having:
            if having[point] != space[dim][point]:
                found = False
                break
        if found:
            return dim, having.keys()
    return None


def _mask(elems, dim, point, space):
    if space[dim][point] == 1:
        return next(elem for elem in elems if elem[dim] == point)
    return [point if i == dim else '*' for i in range(len(space))]


def _masks(elems, space):
    if len(elems) == sum(space[0].values()):
        return None
    covering = _covering_labels(elems, space)
    if covering is None:
        return elems
    dim, points = covering
    return [_mask(elems, dim, point, space) for point in points]


def combine_simple(prop, values):
    if prop.islist:
        values = [
            ValueAt(val, sublist.coords)
            for sublist in values
            for val in sublist.value
        ]
    distinct = sorted({i.value for i in values})
    variants = []
    for value in distinct:
        coords_of_value = [i.coords for i in values if i.value == value]
        variants.append(Area(value, coords_of_value))
    return variants


def combine_minmax(prop, values):
    del prop
    minimum = min(i.value for i in values)
    maximum = max(i.value for i in values)
    return {'min': minimum, 'max': maximum}


def combine_set(prop, values):
    del prop
    return set(i.value for i in values)
