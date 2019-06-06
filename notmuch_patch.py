# -*- coding: utf-8 -*-
#
# notmuch_patch.py
#
# Author:   Toke Høiland-Jørgensen (toke@toke.dk)
# Copyright (c) 2017 Aurelien Aptel <aurelien.aptel@gmail.com>
# Copyright (c) 2018-2019, Toke Høiland-Jørgensen
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
import email
import tempfile
import subprocess
import re


def get_body(message):
    body = None
    charset = 'utf-8'
    if message.is_multipart():
        for part in message.walk():
            if part.is_multipart():
                for subpart in part.walk():
                    if subpart.get_content_type() == 'text/plain':
                        body = subpart.get_payload(decode=True)
                        charset = subpart.get_content_charset(charset)
            elif part.get_content_type() == 'text/plain':
                body = part.get_payload(decode=True)
                charset = subpart.get_content_charset(charset)
    elif message.get_content_type() == 'text/plain':
        body = message.get_payload(decode=True)
        charset = message.get_content_charset(charset)

    if isinstance(body, bytes):
        try:
            body = body.decode(charset)
        except UnicodeDecodeError:
            return ""
    return body


def is_git_patch(msg):
    # we want to skip cover letters, hence why we look for @@
    body = get_body(msg)
    match = re.search(r'''\n@@ [0-9 +,-]+ @@''', body)
    # return ("git-send-email" in msg['x-mailer'] and match)
    return match


def patch_num(m):
    subject = m['subject']
    match_num = re.search(r"([0-9]+)/[0-9]+\]", subject)
    match_ver = re.search(r"^\[.*v([0-9]+)\]", subject)
    num = int(match_num.group(1)) if match_num else 0
    ver = int(match_ver.group(1)) if match_ver else 1
    return (ver, num)


def ver_filter(version):
    def filt(p):
        ver, num, m = p
        if ver == version:
            return m

    return filt


def get_patches(notmuch, query):
    with tempfile.NamedTemporaryFile() as in_mb_file:
        out = subprocess.check_output([notmuch, 'show', '--format=mbox']+list(query))
        in_mb_file.write(out)
        in_mb_file.flush()

        cs = email.charset.Charset("utf-8")
        cs.body_encoding = email.charset.QP

        in_mb = mailbox.mbox(in_mb_file.name)
        patches = []
        for m in in_mb:
            if is_git_patch(m):
                ver, num = patch_num(m)

                # Recode to quoted-printable; git am tends to choke on
                # base64-encoded patches
                pl = m.get_payload(decode=True)
                del m['Content-Transfer-Encoding']
                m.set_payload(pl, cs)

                patches.append((ver, num, m))
        patches.sort(key=lambda x: x[:2])

        if not patches:
            return

        ver = patches[-1][0]
        patches = [m for v, n, m in patches if v == ver]

        return patches
