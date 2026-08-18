# SPDX-License-Identifier: GPL-3.0-or-later
"""Oracle JDK acquisition.

This project never redistributes Oracle binaries.  Archives are fetched from
Oracle's official download host over HTTPS, verified against the ``.sha256``
checksum published next to them by Oracle, and only installed after the user
explicitly accepts the applicable Oracle licence in the UI.
"""

import hashlib
import os
import re
import tarfile
import urllib.request
from typing import Callable, Optional, Tuple

from backends import JVM_DIR, arch
from runtimes import Runtime

BASE = "https://download.oracle.com/java"
USER_AGENT = "universal-java-installer/1.0 (+https://github.com/ruysabino/universal-java-installer)"


def download_url(runtime: Runtime, machine: Optional[str] = None) -> str:
    machine = machine or arch()
    if runtime.oracle_family == "archive" and runtime.oracle_version:
        return (
            f"{BASE}/{runtime.feature}/archive/"
            f"jdk-{runtime.oracle_version}_linux-{machine}_bin.tar.gz"
        )
    return (
        f"{BASE}/{runtime.feature}/latest/"
        f"jdk-{runtime.feature}_linux-{machine}_bin.tar.gz"
    )


def _open(url: str, timeout: int = 30):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=timeout)


def fetch_checksum(url: str) -> Optional[str]:
    """Oracle publishes ``<archive>.sha256`` next to every download."""
    try:
        with _open(url + ".sha256", timeout=20) as response:
            text = response.read().decode("utf-8", "replace").strip()
    except Exception:
        return None
    match = re.search(r"\b[0-9a-f]{64}\b", text)
    return match.group(0) if match else None


def download(
    url: str,
    destination: str,
    on_progress: Optional[Callable[[float], None]] = None,
    cancelled: Optional[Callable[[], bool]] = None,
) -> str:
    digest = hashlib.sha256()
    with _open(url, timeout=60) as response, open(destination, "wb") as handle:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while True:
            if cancelled and cancelled():
                raise InterruptedError("cancelled")
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            handle.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            if on_progress and total:
                on_progress(done * 100.0 / total)
    return digest.hexdigest()


def target_dir(runtime: Runtime, version: str) -> str:
    """Directory naming compatible with ``archlinux-java`` and alternatives."""
    return os.path.join(JVM_DIR, f"java-{runtime.feature}-oracle-{version}")


def probe_archive(path: str) -> Tuple[str, str]:
    """Return (root directory inside the archive, jdk version string)."""
    with tarfile.open(path, "r:gz") as archive:
        names = archive.getnames()
    roots = {name.split("/")[0] for name in names if "/" in name or name}
    if len(roots) != 1:
        raise ValueError("unexpected archive layout")
    root = roots.pop()
    version = root[4:] if root.startswith("jdk-") else root
    return root, version
