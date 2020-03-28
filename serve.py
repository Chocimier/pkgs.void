#!/usr/bin/env python3

# pkgs.void - web catalog of Void Linux packages.
# Copyright (C) 2019-2020 Piotr Wójcik <chocimier@tlen.pl>
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

from config import DEVEL_MODE, ROOT_URL, REPOS
from voidhtml import (
    lists_index, longest_names, main_page, metapackages,
    newest, of_day, page_generator, popular
)
from xbps import join_arch


@route('/search')
def search():
    term = request.query.get('term')  # pylint: disable=no-member
    redirect(ROOT_URL + '/package/' + term)


@route('/all')
def list_all_():
    return static_file('all.html', 'static/generated')


route('/')(route('')(main_page))
route('/toc')(lists_index)
route('/of_day')(of_day)
route('/newest')(newest)
route('/sets')(metapackages)
route('/popular')(popular)
route('/longest_names')(longest_names)


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


application = StripSlashMiddleware(  # pylint: disable=invalid-name
    UrlPrefixMiddleware(
        ROOT_URL,
        default_app()
    )
)


class FlupSocketFCGIServer(ServerAdapter):
    def run(self, handler):
        # pylint: disable=import-outside-toplevel
        import flup.server.fcgi
        flup.server.fcgi.WSGIServer(handler).run()


def serve(args):
    server_names['flup_socket'] = FlupSocketFCGIServer

    kwargs = {}

    try:
        kwargs['server'] = args[0]
    except IndexError:
        pass

    run(app=application, debug=True, reloader=DEVEL_MODE, **kwargs)


if __name__ == '__main__':
    serve(sys.argv[1:])
