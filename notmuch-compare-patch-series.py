#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# notmuch-filter-patch.py
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

import sys
import re
import notmuch_patch
import git
import gitdb
import unidiff

from itertools import zip_longest

# Repo to find upstream commit IDs in
REPO_PATH = "~/build/linux/"


def main(notmuch, *query):
    patches = notmuch_patch.get_patches(notmuch, query)

    repo = git.Repo(REPO_PATH)

    for p in patches:
        pl = p.get_payload(decode=True).decode("utf-8")
        sb = re.sub(r"\s+", " ", p['Subject'].strip())
        ps_ds = unidiff.PatchSet(pl)

        # Find a commit ID in message
        m = re.search(r"^commit ([0-9a-f]{40})", pl, re.MULTILINE)
        if m:
            try:
                # Find the commit in upstream and diff it
                commit_prefix = pl[:m.start()]
                c_sha = m.group(1)
                c = repo.commit(c_sha) # fails if no commit exists
                diff = repo.git.diff(c_sha + '~1', c_sha,
                                     ignore_blank_lines=True,
                                     ignore_space_at_eol=True)
                ps_us = unidiff.PatchSet(diff)

                diff_errs = []

                upstream_dict = {f.path: f for f in ps_us}
                downstream_dict = {f.path: f for f in ps_ds}

                # Find files in upstream but not in downstream
                for k in upstream_dict.keys():
                    if k not in downstream_dict:
                        diff_errs.append(f"Path {k} not found in downstream")

                # Loop through files in downstream patch
                for f1 in ps_ds:
                    if f1.path not in upstream_dict:
                        if not f1.is_removed_file:
                            diff_errs.append(f"Path {f1.path} not found in upstream")
                        continue

                    # File diff found in both patches, check if they are the same
                    f2 = upstream_dict[f1.path]
                    for i, (h1, h2) in enumerate(zip(f1, f2)):
                        h_diff = False
                        # Hunks are different if they have different lengths...
                        if h1.source_length != h2.source_length or \
                           h1.section_header != h2.section_header:
                            h_diff = True
                        else:
                            for l1, l2 in zip(h1, h2):
                                # ... or if the lines they add or remove are different
                                if l1.line_type in (unidiff.LINE_TYPE_ADDED,
                                                    unidiff.LINE_TYPE_REMOVED) and \
                                   (l1.line_type != l2.line_type or
                                    l1.value.strip() != l2.value.strip()):
                                    h_diff = True

                        if h_diff:
                            # If a hunk is different, print the two diffs side-by-side
                            diff_errs.append(f"Hunk difference in hunk {i} " +
                                             f"for file {f1.path}")
                            lines1 = [str(l).strip().replace("\t", "    ")
                                      for l in str(h1).splitlines()]
                            lines2 = [str(l).strip().replace("\t", "    ")
                                      for l in str(h2).splitlines()]

                            linelen = max([len(l) for l in lines1])

                            fmt = "{} {!s:<" + str(linelen+10) + "} {}"

                            diff_errs.append(fmt.format(" ", "Downstream", "Upstream"))

                            for l1, l2 in zip_longest(lines1, lines2):
                                l1 = l1.strip() if l1 else ""
                                l2 = l2.strip() if l2 else ""
                                mkr = " " if l1 == l2 or l1.startswith("@@") else ">"
                                diff_errs.append(fmt.format(mkr, l1, l2))
                            diff_errs.append("")

                if diff_errs:
                    print("{} (upstream {}):".format(sb, c_sha))
                    print("  " + "\n  ".join(diff_errs))
                    print("  " + commit_prefix.replace("\n", "\n  "))
                    print("\n")

            except gitdb.exc.BadName:
                print("{}:\n  Couldn't find upstream commit {}".format(sb, c_sha))
            except KeyboardInterrupt:
                print()
                return
        else:
            print("{}:\n  No upstream commit ID in message".format(sb))


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: {} <notmuch binary> <query>".format(sys.argv[0]),
              file=sys.stderr)
        sys.exit(1)
    main(*sys.argv[1:])
