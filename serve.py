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

from sys import argv, exit as sys_exit

from app import app
from settings import config

if __name__ == '__main__':
    if len(argv) < 2:
        app.run(debug=config.DEVEL_MODE)
    elif argv[1] == 'flup_socket':
        from flup.server.fcgi import WSGIServer
        WSGIServer(app).run()
    elif argv[1] == 'cgi':
        from wsgiref.handlers import CGIHandler
        CGIHandler().run(app)
    else:
        sys_exit(1)
