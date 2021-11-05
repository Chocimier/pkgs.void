#!/usr/bin/env python3

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
import urllib.parse

from bottle import ServerAdapter, default_app, error, redirect
from bottle import request, route, run, server_names, static_file

from settings import config
from voidhtml import (
    find, lists_index, longest_names, main_page, metapackages,
    newest, no_page, of_day, page_generator, popular, which_package
)
from xbps import join_arch


@route('/search')
def search():  # pylint: disable=inconsistent-return-statements
    term = request.query.get('term')  # pylint: disable=no-member
    finding = request.query.get('find')  # pylint: disable=no-member
    fields = request.query.getall('by')  # pylint: disable=no-member
    if finding or fields or not term:
        return find(term, fields)
    redirect(config.ROOT_URL + '/package/' + urllib.parse.quote(term))


@route('/all')
def list_all_():
    return static_file('all.html', config.GENERATED_FILES_PATH)


@route(config.GENERATED_FILES_URL + '/pkgs.void.tar.bz2')
def source_tarball():
    return static_file('pkgs.void.tar.bz2', config.GENERATED_FILES_PATH)


route('/')(route('')(main_page))
route('/toc')(lists_index)
route('/of_day')(of_day)
route('/newest')(newest)
route('/sets')(metapackages)
route('/popular')(popular)
route('/longest_names')(longest_names)
route('/package')(which_package)


@route('/package/<pkgname>')
def package(pkgname):
    return page_generator(pkgname)


@route('/package/<pkgname>/<iset>-<libc>')
def package_arch(pkgname, iset, libc):
    return page_generator(pkgname, single=join_arch(iset, libc))


@route('/static/<filename:path>')
def static(filename):
    return static_file(filename, 'static')


@error(404)
def error404(err):
    del err
    return no_page()


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
        config.ROOT_URL,
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

    run(app=application, debug=True, reloader=config.DEVEL_MODE, **kwargs)


if __name__ == '__main__':
    serve(sys.argv[1:])
