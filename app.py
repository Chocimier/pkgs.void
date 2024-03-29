#!/usr/bin/env python3

# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2019-2022 Piotr Wójcik <chocimier@tlen.pl>
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

from urllib.parse import quote, urlsplit

from flask import Flask, Response, redirect, request, send_from_directory

from settings import config
from voidhtml import (
    build_log as build_log_page,
    find, lists_index, longest_names, main_page, metapackages,
    newest, no_page, of_day, opensearch_description,
    page_generator, popular, which_package
)
from xbps import join_arch


app = Flask(__name__)


@app.route('/search/')
def search():
    term = request.args.get('term')
    finding = request.args.get('find')
    fields = request.args.getlist('by')
    if finding or fields or not term:
        return find(term, fields)
    term = quote(term)
    return redirect(config.ROOT_URL + '/package/' + term + '/')


@app.route('/all/')
def list_all_():
    return send_from_directory(config.GENERATED_FILES_PATH, 'all.html')


@app.route(config.GENERATED_FILES_URL + '/pkgs.void.tar.bz2')
def source_tarball():
    directory = config.GENERATED_FILES_PATH
    return send_from_directory(directory, 'pkgs.void.tar.bz2')


app.route('/')(main_page)
app.route('/toc/')(lists_index)
app.route('/of_day/')(of_day)
app.route('/newest/')(newest)
app.route('/sets/')(metapackages)
app.route('/popular/')(popular)
app.route('/longest_names/')(longest_names)
app.route('/package/')(which_package)


@app.route('/package/<pkgname>/')
def package(pkgname):
    return page_generator(pkgname)


@app.route('/package/<pkgname>/<iset>-<libc>/')
def package_arch(pkgname, iset, libc):
    return page_generator(pkgname, single=join_arch(iset, libc))


@app.route('/buildlog/<pkgname>/<iset>-<libc>/<version>/')
def build_log(pkgname, iset, libc, version):
    result = build_log_page(pkgname, join_arch(iset, libc), version)
    if result.redirect:
        return redirect(result.redirect)
    status = 202 if not result.error else 501
    return (result.content, status)


@app.route('/opensearch.xml')
def opensearch():
    urlparts = urlsplit(request.url)
    print(request.url, urlparts)
    response = Response(
        response=opensearch_description(urlparts),
        content_type='application/opensearchdescription+xml'
    )
    return response


@app.errorhandler(404)
def error404(err):
    del err
    return (no_page(), 404)


class UrlPrefixMiddleware():
    def __init__(self, prefix, application):
        self._app = application
        self._prefix = prefix
        self._prefix_len = len(prefix)

    def __call__(self, env, handler):
        if env['PATH_INFO'].startswith(self._prefix):
            env['PATH_INFO'] = env['PATH_INFO'][self._prefix_len:]
        return self._app(env, handler)


app.wsgi_app = UrlPrefixMiddleware(config.ROOT_URL, app.wsgi_app)
