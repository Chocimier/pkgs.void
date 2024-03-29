#!/usr/bin/env python3

# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2019-2020 Piotr Wójcik <chocimier@tlen.pl>
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

import os
import subprocess
import sys
from collections import defaultdict
from datetime import timedelta

import datasource
from sink import now


DISTDIR = os.environ['XBPS_DISTDIR']


_XBPS_SRC_FIELDS = {
    'Upstream URL': 'homepage',
    'License(s)': 'license',
}


_SINGLE_VALUE_FIELDS = {
    'build-date',
    'homepage',
    'license',
    'maintainer',
    'pkgname',
    'pkgver',
    'restricted',
    'revision',
    'short_desc',
    'version',
}


def templatedata(pkgname, arch):
    del arch
    result = defaultdict(list)
    try:
        xbps_src = subprocess.run(
            [DISTDIR + '/xbps-src', 'show', '-p', 'restricted*', pkgname],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        return result
    lines = xbps_src.stdout.decode('utf-8').split('\n')
    for line in lines:
        try:
            field, value = line.split(':', 1)
        except ValueError:
            continue
        result[field].append(value.strip())
    return result


def build_db(source, repos):
    today = now().date()
    tomorrow = today + timedelta(days=1)
    srcpkgs = os.path.join(DISTDIR, 'srcpkgs')
    for pkgname in os.listdir(srcpkgs):
        entry = os.path.join(srcpkgs, pkgname)
        if os.path.islink(entry) or not os.path.isdir(entry):
            continue
        raw_data = templatedata(pkgname, repos[0])
        dictionary = {}
        for k, v in raw_data.items():
            k = _XBPS_SRC_FIELDS.get(k, k)
            if k in _SINGLE_VALUE_FIELDS:
                dictionary[k] = v[0]
            else:
                dictionary[k] = v
        try:
            pkgver = '{pkgname}-{version}_{revision}'.format(**dictionary)
        except KeyError:
            continue
        dictionary['pkgver'] = pkgver
        dictionary['source-revisions'] = dictionary['pkgname']
        template_json = datasource.to_json(dictionary)
        restricted = dictionary.get('restricted', False)
        in_source = source.exists(pkgname=pkgname, pkgver=pkgver)
        if 'restricted' in dictionary or not in_source:
            if restricted == 'yes':
                restricted = True
            source.create(datasource.PackageRow(
                pkgname=pkgname,
                pkgver=pkgver,
                arch='unknown-unknown',
                restricted=restricted,
                templatedata=template_json,
                mainpkg=pkgname,
                repo=''
            ), dates=[today, tomorrow])
        else:
            source.update(
                pkgname=pkgname,
                pkgver=pkgver,
                set_templatedata=template_json
            )


if __name__ == '__main__':
    datasource.update(lambda x: build_db(x, sys.argv[1:]))
