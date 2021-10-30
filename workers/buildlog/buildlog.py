# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2021 Piotr Wójcik <chocimier@tlen.pl>
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

import json
import math
from urllib.request import urlopen

from celery import Celery

import xbps
from settings import load_config
from workers.buildlog.datasource import (
    CONFIRMED, GUESS, Batch, Package, factory, update
)


BATCH_MARK = 'Finished building packages: '
PACKAGE_MARK_PREFIX = '=> '
PACKAGE_MARK_SUFFIX = ': running do-pkg hook: 00-gen-pkg ...'
BUILDER_NAME_SUFFIX = '_builder'
COMMIT_UPDATE = ': update to '


config = load_config('buildlog')
app = Celery(__name__, broker=config.BROKER)


@app.task()
def scrap_batch(arch, number):
    update(lambda datasource: _scrap_batch(arch, number, datasource))


def _scrap_batch(arch, number, datasource):
    raw_data = fetch_batch(arch, number)
    data = json.loads(raw_data)[str(number)]
    parse_batch(data, arch, number, datasource)
    datasource.create_batch(Batch(arch, number, CONFIRMED))


def fetch_batch(arch, number):
    url = config.RUN_URL.format(arch=arch, number=number)
    with urlopen(url) as response:
        return response.read()


def guess_pkgver(message):
    subject = message.split('\n')[0]
    if COMMIT_UPDATE in subject:
        parts = subject.partition(COMMIT_UPDATE)
        pkgname = parts[0]
        version = parts[2].split()[0].removesuffix('.')
        return pkgname, f'{pkgname}-{version}_1'
    return None, None


def parse_batch(data, arch, number, datasource):
    packages = []
    pkgver_dict = {}
    for step in data.get('steps', []):
        text_list = step.get('text')
        if not text_list:
            continue
        text = text_list[0]
        if text.startswith(BATCH_MARK):
            packages = text.removeprefix(BATCH_MARK).split(' ')
    for change in data['sourceStamps'][0]['changes']:
        pkgname, pkgver = guess_pkgver(change['comments'])
        if pkgver:
            pkgver_dict[pkgname] = pkgver
    for pkgname in packages:
        if not pkgname:
            continue
        package = Package(
            pkgname=pkgname,
            pkgver=pkgver_dict.get(pkgname, ''),
            arch=arch,
            batchnumber=number,
            state=GUESS)
        datasource.create(package)


@app.task()
def scrap_log(arch, number):
    update(lambda datasource: _scrap_log(arch, number, datasource))


def _scrap_log(arch, number, datasource):
    url = config.LOG_URL.format(arch=arch, number=number)
    print('scraping', url)
    with urlopen(url) as response:
        datasource.delete(batchnumber=number)
        for line in response.readlines():
            line = line.decode().strip()
            if _is_log_mark_line(line):
                pkgver = _pkgver_of_mark_line(line)
                pkgname = xbps.pkgname_from_pkgver(pkgver)
                package = Package(
                    pkgname=pkgname,
                    pkgver=pkgver,
                    arch=arch,
                    batchnumber=number,
                    state=CONFIRMED)
                datasource.create(package)


def _is_log_mark_line(line):
    return (
        line.startswith(PACKAGE_MARK_PREFIX)
        and line.endswith(PACKAGE_MARK_SUFFIX)
    )


def _pkgver_of_mark_line(line):
    return line[len(PACKAGE_MARK_PREFIX):-len(PACKAGE_MARK_SUFFIX)]


def _package_order_key(package, pkgver):
    if package.pkgver == pkgver:
        return -math.inf
    return -int(package.batchnumber)


@app.task()
def find_log(pkgver, arch):
    datasource = factory()
    if known_log(pkgver, arch, datasource):
        return
    pkgname = xbps.pkgname_from_pkgver(pkgver)
    packages = list(datasource.read(pkgname=pkgname, state=GUESS))
    packages.sort(key=lambda bld: _package_order_key(bld, pkgver))
    for package in packages:
        scrap_log.delay(arch, package.batchnumber)


@app.task()
def scrap_max_batchnumbers():
    update(_scrap_max_batchnumbers)


def _scrap_max_batchnumbers(datasource):
    url = config.BUILDERS_URL
    with urlopen(url) as response:
        raw_data = response.read()
    data = json.loads(raw_data)
    for builder_name, builder_data in data.items():
        arch = builder_name.removesuffix(BUILDER_NAME_SUFFIX)
        max_number = max(builder_data['cachedBuilds'], default=0)
        datasource.set_max_batch(arch, str(max_number))


def known_log(pkgver, arch, datasource):
    for package in datasource.read(pkgver=pkgver, arch=arch, state=CONFIRMED):
        return config.LOG_URL.format(arch=arch, number=package.batchnumber)
    return None


@app.task()
def scrap_few_random():
    datasource = factory()
    arch_list = list(datasource.random_arch())
    if not arch_list:
        return
    arch = arch_list[0]
    numbers = datasource.unfetched_builds(arch, config.PERIODIC_SCRAP_COUNT)
    for number in numbers:
        scrap_batch.delay(arch, number)


@app.on_after_configure.connect
def _setup_periodic_tasks(sender, **kwargs):
    del kwargs
    period = config.PERIODIC_SCRAP_PERIOD
    sender.add_periodic_task(10 * period, scrap_max_batchnumbers.s())
    sender.add_periodic_task(period, scrap_few_random.s())
