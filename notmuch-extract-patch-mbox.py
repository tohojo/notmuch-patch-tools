#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# notmuch-extract-patch.py
#
# Author:   Toke Høiland-Jørgensen (toke@toke.dk)
# Date:      6 June 2019
# Copyright (c) 2019, Toke Høiland-Jørgensen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import mailbox
import tempfile
import sys
import notmuch_patch


def main(notmuch, *query):
    patches = notmuch_patch.get_patches(notmuch, query)

    if not patches:
        return

    with tempfile.NamedTemporaryFile() as out_mb_file:
        out_mb = mailbox.mbox(out_mb_file.name)
        for m in patches:
            sys.stderr.write(m['subject']+"\n")
            out_mb.add(m)
        out_mb.flush()
        print(open(out_mb_file.name).read())


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: {} <notmuch binary> <query>".format(sys.argv[0]),
              file=sys.stderr)
        sys.exit(1)
    main(*sys.argv[1:])
