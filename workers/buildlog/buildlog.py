# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2021-2024 Piotr Wójcik <chocimier@tlen.pl>
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
import re
from urllib.request import urlopen

from celery import Celery, chain
from celery.utils.log import get_task_logger

import xbps
from settings import load_config
from sink import removeprefix, removesuffix
from workers.buildlog.datasource import (
    ERROR, CONFIRMED, GUESS, REFUTED, Batch, Package, factory, update
)


BATCH_MARK = 'Finished building packages: '
PACKAGE_MARK_REGEXP = re.compile(
    '^(?:\x1b[^=]+)?=> (\\S+): running do-pkg hook: 00-gen-pkg [.]{3}$'
)
PACKAGE_MARK_SUFFIX = ': running do-pkg hook: 00-gen-pkg ...'
BUILDER_NAME_SUFFIX = '_builder'
COMMIT_UPDATE = ': update to '
TASK_PROCESSING = object()
TASK_ERROR = object()


config = load_config('buildlog')
app = Celery(__name__, broker=config.BROKER, backend=config.BROKER)
logger = get_task_logger(__name__)


@app.task()
def scrap_batches(arch, numbers):
    numbers = list(numbers)
    if not numbers:
        logger.info('no batch numbers for %s', arch)
        return
    numbers_formatted = ', '.join(str(i) for i in numbers)
    logger.info('scraping %s batches number %s', arch, numbers_formatted)
    update(lambda datasource: _scrap_batches(arch, numbers, datasource))


def _scrap_batches(arch, numbers, datasource):
    if not numbers:
        return
    raw_data = fetch_batches(arch, numbers)
    data = json.loads(raw_data)
    for number, batch_data in data.items():
        batch = parse_batch(batch_data, arch, number, datasource)
        datasource.create_batch(batch)


def fetch_batches(arch, numbers):
    if not numbers:
        return '{}'
    url = config.BATCHES_URL.format(arch=arch)
    for number in numbers:
        url += config.BATCHES_URL_NUMBER_PARAM.format(number=number)
    logger.info('fetching from %s', url)
    with urlopen(url) as response:
        return response.read()


def guess_pkgver(message):
    subject = message.split('\n')[0]
    if COMMIT_UPDATE in subject:
        parts = subject.partition(COMMIT_UPDATE)
        pkgname = parts[0]
        version = parts[2].split()[0].rstrip('.')
        pkgver = f'{pkgname}-{version}_1'
        logger.info('guessing %s from subject %s', pkgver, repr(subject))
        return pkgname, pkgver
    logger.info('guessing nothing from subject %s', repr(subject))
    return None, None


def parse_batch(data, arch, number, datasource):
    if 'error' in data:
        return Batch(arch, number, ERROR)
    arch = removesuffix(data['builderName'], BUILDER_NAME_SUFFIX)
    number = data['number']
    packages = []
    pkgver_dict = {}
    for step in data.get('steps', []):
        text_list = step.get('text')
        if not text_list:
            continue
        text = text_list[0]
        if text.startswith(BATCH_MARK):
            packages = removeprefix(text, BATCH_MARK).split(' ')
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
    return Batch(arch, number, CONFIRMED)


def scrap_log(arch, number, desired_pkgver=None):
    return update(
        lambda datasource: _scrap_log(arch, number, datasource, desired_pkgver)
    )


@app.task()
def scrap_log_chain_link(already_found, arch, number, desired_pkgver):
    if already_found:
        logger.info(
            'already found log for %s %s, skipping fetching %s',
            desired_pkgver, arch, number
        )
        return True
    return scrap_log(arch, number, desired_pkgver)


def _scrap_log(arch, number, datasource, desired_pkgver=None):
    url = config.PACKAGE_URL.format(arch=arch, number=number)
    logger.info('scrapping %s', url)
    already_found = False
    with urlopen(url) as response:
        datasource.update(arch=arch, batchnumber=number, set_state=REFUTED)
        for pkgver in parse_log_file(response):
            pkgname = xbps.pkgname_from_pkgver(pkgver)
            package = Package(
                pkgname=pkgname,
                pkgver=pkgver,
                arch=arch,
                batchnumber=number,
                state=CONFIRMED)
            logger.info('found %s in batch %s', package, number)
            datasource.create(package)
            if pkgver == desired_pkgver:
                already_found = True

    return already_found


def parse_log_file(response):
    for line in response:
        line = line.decode(errors='replace').strip()
        pkgver = _pkgver_of_mark_line(line)
        if pkgver:
            yield pkgver


def _pkgver_of_mark_line(line):
    if not line.endswith(PACKAGE_MARK_SUFFIX):
        return None
    match = PACKAGE_MARK_REGEXP.match(line)
    if not match:
        logger.warning('line almost matches build pattern: %s', line)
        return None
    return match.group(1)


def _package_order_key(package, pkgver):
    if package.pkgver == pkgver:
        return -math.inf
    return -int(package.batchnumber)


def get_log(pkgver, arch):
    datasource = factory()
    known = known_log(pkgver, arch, datasource)
    if known:
        return known
    try:
        find_log.delay(pkgver, arch)
    except Exception:  # pylint: disable=broad-except
        return TASK_ERROR
    return TASK_PROCESSING


@app.task()
def find_log(pkgver, arch):
    datasource = factory()
    logger.info('looking for log of %s %s', pkgver, arch)
    if known_log(pkgver, arch, datasource):
        logger.info('already known log of %s %s', pkgver, arch)
        return
    pkgname = xbps.pkgname_from_pkgver(pkgver)
    packages = list(datasource.read(pkgname=pkgname, arch=arch, state=GUESS))
    packages.sort(key=lambda bld: _package_order_key(bld, pkgver))

    def sig(package):
        return scrap_log_chain_link.s(arch, package.batchnumber, pkgver)

    logger.info('chaining %s', packages)
    chain(sig(package) for package in packages).delay(False)


@app.task()
def scrap_max_batchnumbers():
    update(_scrap_max_batchnumbers)


def _scrap_max_batchnumbers(datasource):
    url = config.BUILDERS_URL
    logger.info('fetching newest batches numbers from %s', url)
    with urlopen(url) as response:
        raw_data = response.read()
    data = json.loads(raw_data)
    for builder_name, builder_data in data.items():
        arch = removesuffix(builder_name, BUILDER_NAME_SUFFIX)
        max_number = max(builder_data['cachedBuilds'], default=0)
        logger.info('found batch %s for %s', max_number, arch)
        datasource.set_max_batch(arch, str(max_number))


def known_log(pkgver, arch, datasource):
    for package in datasource.read(pkgver=pkgver, arch=arch, state=CONFIRMED):
        return config.PACKAGE_URL.format(arch=arch, number=package.batchnumber)
    return None


@app.task()
def scrap_few_random():
    datasource = factory()
    arch_list = list(datasource.random_arch())
    if not arch_list:
        logger.info('no archs to scrap from')
        return
    arch = arch_list[0]
    count = config.PERIODIC_SCRAP_COUNT
    numbers = list(datasource.unfetched_builds(arch, count))
    logger.info('scrapping ahead batches %s for %s', numbers, arch)
    scrap_batches.delay(arch, numbers)


@app.on_after_configure.connect
def _setup_periodic_tasks(sender, **kwargs):
    del kwargs
    period = config.PERIODIC_SCRAP_PERIOD
    sender.add_periodic_task(10 * period, scrap_max_batchnumbers.s())
    sender.add_periodic_task(period, scrap_few_random.s())
