#!/usr/bin/env python3

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

from bottle import ServerAdapter, default_app, error, redirect
from bottle import request, route, run, server_names, static_file
from genshi.template import TemplateLoader

from config import ROOT_URL, REPOS
from voidhtml import join_arch, longest_names, page_generator


@route('')
@route('/')
@route('/newest')
def index():
    redirect(ROOT_URL + '/longest_names')


@route('/search')
def search():
    redirect(ROOT_URL + '/package/' + request.query.get('term'))


@route('/all')
def list_all_():
    return static_file('all.html', 'static/generated')


@route('/longest_names')
def longest_names_():
    return longest_names()


@route('/package')
def no_package():
    loader = TemplateLoader('.')
    return (
        loader
        .load('templates/which.html')
        .generate(root_url=ROOT_URL)
        .render('html')
    )


@route('/package/<pkgname>')
def package(pkgname):
    return page_generator(pkgname, repos=REPOS)


@route('/package/<pkgname>/<iset>-<libc>')
def package_arch(pkgname, iset, libc):
    return page_generator(pkgname, repos=[join_arch(iset, libc)], single=True)


@route('/static/<filename:path>')
def static(filename):
    return static_file(filename, 'static')


@error(404)
def error404(err):
    del err
    return 'Nothing here, sorry'


class UrlPrefixMiddleware():
    def __init__(self, prefix, app):
        self._app = app
        self._prefix = prefix
        self._prefix_len = len(prefix)

    def __call__(self, env, handler):
        if env['PATH_INFO'].startswith(self._prefix):
            env['PATH_INFO'] = env['PATH_INFO'][self._prefix_len:]
        return self._app(env, handler)


# https://www.bottlepy.org/docs/dev/recipes.html#ignore-trailing-slashes
class StripSlashMiddleware():
    def __init__(self, app):
        self._app = app

    def __call__(self, env, handler):
        env['PATH_INFO'] = env['PATH_INFO'].rstrip('/')
        return self._app(env, handler)


application = StripSlashMiddleware(
    UrlPrefixMiddleware(
        ROOT_URL,
        default_app()
    )
)


class FlupSocketFCGIServer(ServerAdapter):
    def run(self, handler):
        import flup.server.fcgi
        flup.server.fcgi.WSGIServer(handler).run()


if __name__ == '__main__':
    server_names['flup_socket'] = FlupSocketFCGIServer

    kwargs = {}

    try:
        kwargs['server'] = sys.argv[1]
    except IndexError:
        pass

    run(app=application, debug=True, **kwargs)
