# SPDX-License-Identifier: GPL-3.0-or-later
"""Package-manager abstraction.

Supported backends: apt (Debian/Ubuntu/Mint/Pop!_OS), dnf (Fedora/RHEL and
derivatives) and pacman (Arch/Manjaro/EndeavourOS).  Every backend exposes the
same, tiny surface: query whether a package is installed and build the argv
used by the privileged helper.
"""

import os
import platform
import shutil
import subprocess
from typing import List, Optional

JVM_DIR = "/usr/lib/jvm"


def arch() -> str:
    machine = platform.machine()
    if machine in ("x86_64", "amd64"):
        return "x64"
    if machine in ("aarch64", "arm64"):
        return "aarch64"
    return machine


def _os_release() -> dict:
    data = {}
    for path in ("/etc/os-release", "/usr/lib/os-release"):
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                data[key.strip()] = value.strip().strip('"')
        break
    return data


class Backend:
    id = ""
    name = ""

    # --- queries -------------------------------------------------------
    def is_installed(self, package: str) -> bool:
        raise NotImplementedError

    def package_exists(self, package: str) -> bool:
        raise NotImplementedError

    # --- privileged commands -------------------------------------------
    def install_cmd(self, packages: List[str]) -> List[str]:
        raise NotImplementedError

    def remove_cmd(self, packages: List[str]) -> List[str]:
        raise NotImplementedError

    def refresh_cmd(self) -> Optional[List[str]]:
        return None

    # --- alternatives ---------------------------------------------------
    def uses_archlinux_java(self) -> bool:
        return False


class AptBackend(Backend):
    id = "apt"
    name = "APT"

    def is_installed(self, package: str) -> bool:
        proc = subprocess.run(
            ["dpkg-query", "-W", "-f=${db:Status-Status}", package],
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0 and proc.stdout.strip() == "installed"

    def package_exists(self, package: str) -> bool:
        proc = subprocess.run(
            ["apt-cache", "policy", package], capture_output=True, text=True
        )
        return proc.returncode == 0 and package in proc.stdout

    def install_cmd(self, packages: List[str]) -> List[str]:
        # apt-get (not apt) keeps a stable, machine readable output
        return [
            "apt-get",
            "install",
            "-yq",
            "-o",
            "APT::Status-Fd=1",
            *packages,
        ]

    def remove_cmd(self, packages: List[str]) -> List[str]:
        return ["apt-get", "purge", "-yq", *packages]

    def refresh_cmd(self) -> Optional[List[str]]:
        return ["apt-get", "update", "-yq"]


class DnfBackend(Backend):
    id = "dnf"
    name = "DNF"

    def _bin(self) -> str:
        return "dnf5" if shutil.which("dnf5") else "dnf"

    def is_installed(self, package: str) -> bool:
        proc = subprocess.run(
            ["rpm", "-q", package], capture_output=True, text=True
        )
        return proc.returncode == 0

    def package_exists(self, package: str) -> bool:
        proc = subprocess.run(
            [self._bin(), "-q", "list", "--available", package],
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0

    def install_cmd(self, packages: List[str]) -> List[str]:
        return [self._bin(), "install", "-y", *packages]

    def remove_cmd(self, packages: List[str]) -> List[str]:
        return [self._bin(), "remove", "-y", *packages]


class PacmanBackend(Backend):
    id = "pacman"
    name = "pacman"

    def is_installed(self, package: str) -> bool:
        proc = subprocess.run(
            ["pacman", "-Qq", package], capture_output=True, text=True
        )
        return proc.returncode == 0

    def package_exists(self, package: str) -> bool:
        proc = subprocess.run(
            ["pacman", "-Ssq", f"^{package}$"], capture_output=True, text=True
        )
        return proc.returncode == 0 and bool(proc.stdout.strip())

    def install_cmd(self, packages: List[str]) -> List[str]:
        return ["pacman", "-S", "--needed", "--noconfirm", *packages]

    def remove_cmd(self, packages: List[str]) -> List[str]:
        return ["pacman", "-Rns", "--noconfirm", *packages]

    def refresh_cmd(self) -> Optional[List[str]]:
        return ["pacman", "-Sy", "--noconfirm"]

    def uses_archlinux_java(self) -> bool:
        return shutil.which("archlinux-java") is not None


BACKENDS = {
    "apt": AptBackend,
    "dnf": DnfBackend,
    "pacman": PacmanBackend,
}


def detect(backend_id: Optional[str] = None) -> Optional[Backend]:
    """Return the backend for this system (or the forced one)."""
    if backend_id:
        cls = BACKENDS.get(backend_id)
        return cls() if cls else None

    forced = os.environ.get("JAVA_INSTALLER_BACKEND")
    if forced in BACKENDS:
        return BACKENDS[forced]()

    for binary, cls in (
        ("apt-get", AptBackend),
        ("dnf5", DnfBackend),
        ("dnf", DnfBackend),
        ("pacman", PacmanBackend),
    ):
        if shutil.which(binary):
            return cls()
    return None


def distro_name() -> str:
    data = _os_release()
    return data.get("PRETTY_NAME") or data.get("NAME") or "Linux"
