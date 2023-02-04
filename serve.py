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

# pylint: disable=invalid-name,used-before-assignment

from sys import argv, exit as sys_exit, stderr

from app import app
from settings import config

if __name__ == '__main__':
    if len(argv) < 2:
        app.run(debug=config.DEVEL_MODE)
    elif argv[1] == 'flup_socket':
        from flup.server.fcgi import WSGIServer
        WSGIServer(app).run()
    elif argv[1] == 'flup_bind':
        from flup.server.fcgi import WSGIServer
        if len(argv) == 4:
            address = (argv[2], int(argv[3]))
        elif len(argv) == 3:
            address = argv[2]
        else:
            print('pass unix socket path or interface and port', file=stderr)
            sys_exit(1)
        WSGIServer(app, bindAddress=address).run()
    elif argv[1] == 'cgi':
        from wsgiref.handlers import CGIHandler
        CGIHandler().run(app)
    else:
        sys_exit(1)
