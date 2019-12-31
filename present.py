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
from genshi.template import TemplateLoader
from genshi.template.loader import TemplateNotFound
from genshi.template.markup import Markup
from humanize import naturalsize

from custom_types import ValueAt
from sink import same, web_parameters
from config import ROOT_URL


_LOADER = TemplateLoader('templates')


def parse_contact(value):
    return value.split('<')[0].strip()


def render_link(href, text):
    return Element('a', href=href)(text)


def render_template(template_path, **kwargs):
    template = _LOADER.load(template_path)
    return Markup(template.generate(**web_parameters(), **kwargs))


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


def _as_mask(masks):
    if not masks:
        return ''
    return ', '.join('-'.join(mask) for mask in masks)


CombineWithTemplatesConfig = namedtuple(
    'CombineWithTemplatesConfig',
    (
        'single_plain',
        'directory',
        'top_template',
        'to_template',
    )
)


COMBINE_TEMPLATE_DEFAULTS = {
    'single_plain': True,
    'directory': 'generic',
    'top_template': 'list',
    'to_template': lambda x: 'entry',
}


def combine_simple(prop, values, space, pkgname):
    config = CombineWithTemplatesConfig(**COMBINE_TEMPLATE_DEFAULTS)
    return combine_with_templates(prop, values, space, pkgname, config=config)


def combine_with_template(config=None):
    config = config or {}
    conf = CombineWithTemplatesConfig(
        **{
            **COMBINE_TEMPLATE_DEFAULTS,
            **{
                'single_plain': False,
                'top_template': 'top',
            },
            **config
        }
    )
    return (lambda prop, values, space, pkgname:
            combine_with_templates(prop, values, space, pkgname, conf))


def group_variants(prop, values, space, config):
    distinct = set(i.value for i in values)
    if len(distinct) == 1 and config.single_plain:
        return prop.formatter(distinct.pop()), True
    distinct = sorted(distinct)
    variants = []
    for value in distinct:
        coords_of_value = [i.coords for i in values if i.value == value]
        mask = _as_mask(_masks(coords_of_value, space))
        variants.append({'value': prop.formatter(value), 'mask': mask})
    return variants, False


def combine_with_templates(prop, values, space, pkgname, config=None):
    conf = config or CombineWithTemplatesConfig(
        single_plain=False,
        directory=prop.name,
        top_template='top',
        to_template=same,
    )
    if prop.islist:
        values = [
            ValueAt(val, sublist.coords)
            for sublist in values
            for val in sublist.value
        ]
    variants, final = group_variants(prop, values, space, conf)
    if final:
        return variants
    entries = Markup('')
    for variant in variants:
        template_name = conf.to_template(variant['value'])
        template_path = f'present/{conf.directory}/{template_name}.html'
        params = {
            'pkgname': pkgname,
            'elem': variant,
        }
        try:
            entries += render_template(template_path, **params)
        except TemplateNotFound:
            continue
    if entries:
        template_name = conf.top_template
        template_path = f'present/{conf.directory}/{template_name}.html'
        try:
            return render_template(template_path, content=entries)
        except TemplateNotFound:
            return ''
    return ''


def combine_minmax(prop, values, **kwargs):
    del kwargs
    minimum = prop.formatter(min(i.value for i in values))
    maximum = prop.formatter(max(i.value for i in values))
    if minimum == maximum:
        return minimum
    return f'{minimum} - {maximum}'


def combine_set(prop, values, **kwargs):
    del prop
    del kwargs
    return set(i.value for i in values)
