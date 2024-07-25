#!/usr/bin/env python3
# Copyright 2016 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Automates running sysroot-creator.sh for each supported arch.
"""

import json
import multiprocessing
import os
import sys

import sysroot_creator

DEFAULT_URL_PREFIX = "https://dev-cdn.electronjs.org/linux-sysroots"


def build_and_upload(key, arch, lock):
    script_dir = os.path.dirname(os.path.realpath(__file__))

    if "SKIP_SYSROOT_BUILD" not in os.environ:
        sysroot_creator.build_sysroot(arch)
    if "AZURE_STORAGE_SAS_TOKEN" in os.environ:
        sysroot_creator.upload_sysroot(arch)

    tarball = "%s_%s_%s_sysroot.tar.xz" % (
        sysroot_creator.DISTRO,
        sysroot_creator.RELEASE,
        arch.lower(),
    )
    tarxz_path = os.path.join(
        script_dir,
        "..",
        "..",
        "..",
        "out",
        "sysroot-build",
        sysroot_creator.RELEASE,
        tarball,
    )
    sha256sum = sysroot_creator.sha256sumfile(tarxz_path)
    sysroot_dir = "%s_%s_%s-sysroot" % (
        sysroot_creator.DISTRO,
        sysroot_creator.RELEASE,
        arch.lower(),
    )

    sysroot_metadata = {
        "Key": key,
        "Sha256Sum": sha256sum,
        "SysrootDir": sysroot_dir,
        "Tarball": tarball,
        "URL": DEFAULT_URL_PREFIX,
    }
    with lock:
        fname = os.path.join(script_dir, "sysroots.json")
        sysroots = json.load(open(fname))
        with open(fname, "w") as f:
            sysroots["%s_%s" % (sysroot_creator.RELEASE,
                                arch.lower())] = sysroot_metadata
            f.write(
                json.dumps(sysroots,
                           sort_keys=True,
                           indent=4,
                           separators=(",", ": ")))
            f.write("\n")


def main():
    key = "%s-%s" % (sysroot_creator.ARCHIVE_TIMESTAMP,
                     sysroot_creator.SYSROOT_RELEASE)

    procs = []
    lock = multiprocessing.Lock()
    for arch in sysroot_creator.TRIPLES:
        proc = multiprocessing.Process(
            target=build_and_upload,
            args=(key, arch, lock),
        )
        procs.append((
            "%s %s (%s)" %
            (sysroot_creator.DISTRO, sysroot_creator.RELEASE, arch),
            proc,
        ))
        proc.start()
    for _, proc in procs:
        proc.join()

    print("SYSROOT CREATION SUMMARY")
    failures = 0
    for name, proc in procs:
        if proc.exitcode:
            failures += 1
        status = "FAILURE" if proc.exitcode else "SUCCESS"
        print("%s sysroot creation\t%s" % (name, status))
    return failures


if __name__ == "__main__":
  sys.exit(main())
