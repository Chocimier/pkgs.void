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

from collections import Counter, namedtuple

from genshi.builder import Element
from genshi.output import XMLSerializer
from genshi.template import TemplateLoader
from genshi.template.markup import Markup
from humanize import naturalsize

from custom_types import ValueAt
from sink import web_parameters
from config import DEVEL_MODE, ROOT_URL


_CACHED_LOADER = TemplateLoader('templates')


Area = namedtuple('Area', ('value', 'coords'))


def _loader():
    if DEVEL_MODE:
        return TemplateLoader('templates')
    return _CACHED_LOADER


def _serializer(**kwargs):
    return XMLSerializer(strip_whitespace=False, **kwargs)


def parse_contact(value):
    return value.split('<')[0].strip()


def render_link(href, text):
    return Element('a', href=href)(text)


def _masks_as_string(masks_set):
    return ', '.join(map('-'.join, masks_set))


def _masks_presenter(values, space):
    masks_set = _masks(values, space) or {}
    return _masks_as_string(masks_set)


def render_template(template_path, **kwargs):
    template = _loader().load(template_path)
    template.serializer = _serializer
    return Markup(template.generate(
        masks_presenter=_masks_presenter,
        **web_parameters(),
        **kwargs
    ))


def as_new_version(versions):
    return render_template('small/as_new_version.html', versions=versions)


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
    href = ROOT_URL + '/package/' + pkgname
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
        pkgver = render_template('small/as_package.html', pairs=pairs)
    return render_link(href, pkgname) + pkgver


def as_link(value):
    return render_link(value, value)


def as_date(value):
    return value


def as_repository(value):
    name = 'restricted' if value.repo == 'restricted' else 'additional'
    return render_template(
        f'present/repository/{name}.html',
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
