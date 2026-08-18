#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Privileged helper.

Runs as root through ``pkexec`` and performs exactly one operation per
invocation.  Every argument is validated against the catalog before use, so
the GUI cannot ask the helper to run an arbitrary command line.

Usage:
    helper.py install-package <runtime-id>
    helper.py remove-package  <runtime-id>
    helper.py install-archive <runtime-id> <archive> <sha256>
    helper.py remove-jvm      <java-home>
    helper.py set-default     <java-binary>
    helper.py kill            <pid>
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import alternatives  # noqa: E402
import backends  # noqa: E402
import oracle  # noqa: E402
import runtimes  # noqa: E402

JVM_DIR = backends.JVM_DIR


def fail(message: str, code: int = 1):
    print(f"error: {message}", file=sys.stderr, flush=True)
    sys.exit(code)


def run(cmd, check=True) -> int:
    print(f"+ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd)
    if check and proc.returncode != 0:
        fail(f"command failed ({proc.returncode}): {' '.join(cmd)}", proc.returncode)
    return proc.returncode


def _runtime_or_fail(runtime_id: str):
    runtime = runtimes.by_id(runtime_id)
    if runtime is None:
        fail(f"unknown runtime: {runtime_id}")
    return runtime


def _packages_or_fail(runtime, backend):
    packages = runtime.packages.get(backend.id) or []
    if not packages:
        fail(f"{runtime.id} has no package for backend {backend.id}")
    return packages


def _safe_jvm_path(path: str) -> str:
    real = os.path.realpath(path)
    if os.path.dirname(real) != os.path.realpath(JVM_DIR):
        fail(f"refusing to touch a path outside {JVM_DIR}: {real}")
    return real


def install_package(runtime_id: str):
    backend = backends.detect()
    if backend is None:
        fail("no supported package manager found")
    runtime = _runtime_or_fail(runtime_id)
    packages = _packages_or_fail(runtime, backend)
    refresh = backend.refresh_cmd()
    if refresh:
        run(refresh, check=False)
    run(backend.install_cmd(packages))


def remove_package(runtime_id: str):
    backend = backends.detect()
    if backend is None:
        fail("no supported package manager found")
    runtime = _runtime_or_fail(runtime_id)
    packages = _packages_or_fail(runtime, backend)
    run(backend.remove_cmd(packages))


def install_archive(runtime_id: str, archive: str, expected_sha: str):
    runtime = _runtime_or_fail(runtime_id)
    if not runtime.is_oracle:
        fail("archive installs are only used for Oracle builds")
    if not os.path.isfile(archive):
        fail("archive not found")
    if len(expected_sha) != 64 or not all(c in "0123456789abcdef" for c in expected_sha):
        fail("invalid sha256")

    digest = hashlib.sha256()
    with open(archive, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected_sha:
        fail("checksum mismatch - refusing to install")

    root, version = oracle.probe_archive(archive)
    destination = oracle.target_dir(runtime, version)

    os.makedirs(JVM_DIR, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=JVM_DIR) as staging:
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar.getmembers():
                target = os.path.realpath(os.path.join(staging, member.name))
                if not target.startswith(os.path.realpath(staging) + os.sep):
                    fail("archive contains unsafe paths")
                if member.issym() or member.islnk():
                    link = os.path.realpath(
                        os.path.join(os.path.dirname(target), member.linkname)
                    )
                    if not link.startswith(os.path.realpath(staging) + os.sep):
                        fail("archive contains unsafe links")
            tar.extractall(staging)
        extracted = os.path.join(staging, root)
        if not os.path.isdir(extracted):
            fail("archive root not found")
        if os.path.exists(destination):
            shutil.rmtree(destination)
        shutil.move(extracted, destination)

    for dirpath, dirnames, filenames in os.walk(destination):
        os.chown(dirpath, 0, 0)
        for name in dirnames + filenames:
            path = os.path.join(dirpath, name)
            if not os.path.islink(path):
                os.chown(path, 0, 0)
    print(f"installed: {destination}", flush=True)


def remove_jvm(java_home: str):
    real = _safe_jvm_path(java_home)
    for cmd in alternatives.unset_cmds(real):
        run(cmd, check=False)
    shutil.rmtree(real)
    print(f"removed: {real}", flush=True)


def set_default(java_binary: str):
    home = alternatives.java_home_of(java_binary)
    _safe_jvm_path(home)
    if not os.path.exists(java_binary):
        fail("java binary not found")
    commands = alternatives.set_default_cmds(java_binary)
    if not commands:
        fail("no alternatives mechanism available on this system")
    for cmd in commands:
        run(cmd, check=False)


def main(argv):
    if len(argv) < 2:
        fail(__doc__ or "missing operation")
    operation = argv[1]

    if operation == "kill" and len(argv) == 3:
        subprocess.run(["kill", "-2", argv[2]])
        return
    if operation == "install-package" and len(argv) == 3:
        return install_package(argv[2])
    if operation == "remove-package" and len(argv) == 3:
        return remove_package(argv[2])
    if operation == "install-archive" and len(argv) == 5:
        return install_archive(argv[2], argv[3], argv[4])
    if operation == "remove-jvm" and len(argv) == 3:
        return remove_jvm(argv[2])
    if operation == "set-default" and len(argv) == 3:
        return set_default(argv[2])
    fail(f"invalid invocation: {' '.join(argv[1:])}")


if __name__ == "__main__":
    main(sys.argv)
