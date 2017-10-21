#!/usr/bin/env python
# Copyright (c) 2017, Dimitris Karagkasidis <t.pagef.lt@gmail.com>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import time
import shutil
import argparse

# This utility determines which C source and header files were used during the
# compilation process of a source tree and, based on that information, generates
# a trimmed-down version of that tree.
#
# In order to make those deductions, we rely on the `relatime` mount option,
# which is commonly used on modern distributions. According to that, the access
# time of a file is only updated if the previous access time was earlier than the
# current modify or change time. With this thing in mind, this utility sets the
# modification time of all .c and .h files under a source tree to current time,
# and the access time to [current time - 48 hours]. This way, upon compilation,
# all used files will have their access times updated and set to timestamps
# older than their modification time. We collect all these files and copy them
# to the directory specified to contain the reduced source tree.
#
# This will not work on filesystems mounted with noatime/norelatime options.
#
# This project is hosted at https://github.com/pageflt/reduce-tree


def parent_copy(src, dst, root):
    # Copy the `src` file to the `dst` directory while preserving
    # directory structure from the start of `root`.
    # This mimics the --parent option of GNU cp(1).
    try:
        parent_dirs = os.path.split(os.path.relpath(src,root))[0]
        if parent_dirs:
            dst = "%s/%s" % (dst, parent_dirs)
            if not os.path.exists(dst):
                os.makedirs(dst, 0755)
        shutil.copy2(src, dst)
    except Exception as e:
        raise Exception("Could not copy %s: %s" % (src, str(e)))


def collect_tree(src, dst):
    # Find all C files with modification time older than access time
    # and copy them to the reduced source tree directory.
    try:
        src = os.path.abspath(src)
        dst = os.path.abspath(dst)
        for root, subdirs, files in os.walk(src):
            for f in files:
                if f.endswith((".c", ".h")):
                    path = "%s/%s" % (root, f)
                    if os.path.islink(path):
                        continue
                    if os.path.getatime(path) > os.path.getmtime(path):
                        parent_copy(path, dst, src)
    except Exception as e:
        raise e


def prepare_tree(src):
    # Set the modification time of all C source and header files to now, and
    # the access time to now-48h.
    try:
        m_time = time.time()
        a_time = m_time - (48 * 3600)

        for root, subdirs, files in os.walk(src):
            for f in files:
                if f.endswith((".c", ".h")):
                    path = "%s/%s" % (root, f)
                    if not os.path.islink(path):
                        os.utime(path, (a_time, m_time))
    except Exception as e:
        raise e


def parse_args():
    # Handle argument parsing.
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--prepare", dest="prepare", action="store_true",
                        help="prepare source tree for reduction (pre-build)")
    parser.add_argument("-c", "--collect", dest="collect", action="store_true",
                        help="collect files into a reduced source tree (post-build)")
    parser.add_argument("-s", "--src", dest="src",
                        help="source directory of the initial tree")
    parser.add_argument("-d", "--dst", dest="dst",
                        help="destination directory for the reduced tree")
    return parser.parse_args()


def main():
    # Parse arguments, ensure some basic sanity.
    args = parse_args()
    if (args.prepare and args.collect) or (not args.prepare and not args.collect):
        raise Exception("You must use either --collect or --prepare")
    if args.prepare and not args.src:
        raise Exception("You must use --src in conjunction with --prepare")
    if args.collect and (not args.src or not args.dst):
        raise Exception("You must use --src and --dst in conjunction with --collect")
    if not os.path.exists(args.src):
        raise Exception("Directory %s does not exist" % args.src)

    if args.prepare:
        # Prepare source tree for reduction.
        try:
            prepare_tree(args.src)
        except Exception as e:
            raise Exception("Could not prepare: %s" % str(e))
    else:
        # Collect source files into a reduced tree.
        try:
            collect_tree(args.src, args.dst)
        except Exception as e:
            raise Exception("Could not collect: %s" % str(e))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print "Error: %s" % str(e)

