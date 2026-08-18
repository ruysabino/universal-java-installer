# SPDX-License-Identifier: GPL-3.0-or-later
"""Default-JVM handling across distributions.

Debian/Ubuntu and Fedora use ``update-alternatives``; Arch based systems use
``archlinux-java``.  Both are wrapped behind the same three calls.
"""

import glob
import os
import shutil
import subprocess
from typing import List, Optional

from backends import JVM_DIR

TOOLS = ("java", "javac", "jar", "javadoc", "jshell", "keytool", "javaws")
PRIORITY = 2000


def has_update_alternatives() -> bool:
    return shutil.which("update-alternatives") is not None


def has_archlinux_java() -> bool:
    return shutil.which("archlinux-java") is not None


def current_default() -> Optional[str]:
    """Absolute path of the java binary currently used as default."""
    if has_update_alternatives():
        proc = subprocess.run(
            ["update-alternatives", "--query", "java"],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                if line.startswith("Value:"):
                    return line.split(":", 1)[1].strip()
    if has_archlinux_java():
        proc = subprocess.run(
            ["archlinux-java", "get"], capture_output=True, text=True
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return os.path.join(JVM_DIR, proc.stdout.strip(), "bin", "java")
    resolved = shutil.which("java")
    return os.path.realpath(resolved) if resolved else None


def java_home_of(path: str) -> str:
    """/usr/lib/jvm/<home>/bin/java -> /usr/lib/jvm/<home>"""
    return os.path.dirname(os.path.dirname(path))


def find_java_binaries(feature: int, vendor: str = "") -> List[str]:
    """Locate installed JVMs matching a feature release."""
    matches = []
    for home in sorted(glob.glob(os.path.join(JVM_DIR, "*"))):
        binary = os.path.join(home, "bin", "java")
        if not os.path.exists(binary):
            binary = os.path.join(home, "jre", "bin", "java")
            if not os.path.exists(binary):
                continue
        base = os.path.basename(home).lower()
        if vendor and vendor.lower() not in base:
            continue
        if _feature_of(base) == feature:
            matches.append(binary)
    return matches


def _feature_of(name: str) -> Optional[int]:
    digits = ""
    for part in name.replace("-", " ").replace("_", " ").split():
        stripped = part.lstrip("java").lstrip("jdk").lstrip("openjdk").strip(".")
        candidate = ""
        for char in stripped:
            if char.isdigit():
                candidate += char
            else:
                break
        if candidate:
            digits = candidate
            break
    if not digits:
        return None
    value = int(digits)
    if value == 1:  # java-1.8.0-openjdk
        return 8
    return value


# --- privileged operations (executed by the helper) ---------------------


def set_default_cmds(java_path: str) -> List[List[str]]:
    home = java_home_of(java_path)
    commands: List[List[str]] = []

    if has_archlinux_java() and os.path.dirname(home) == JVM_DIR:
        commands.append(["archlinux-java", "set", os.path.basename(home)])
        return commands

    for tool in TOOLS:
        binary = os.path.join(home, "bin", tool)
        if not os.path.exists(binary):
            continue
        commands.append(
            ["update-alternatives", "--install", f"/usr/bin/{tool}", tool, binary, str(PRIORITY)]
        )
        commands.append(["update-alternatives", "--set", tool, binary])
    return commands


def unset_cmds(java_home: str) -> List[List[str]]:
    commands: List[List[str]] = []
    if has_archlinux_java() and os.path.dirname(java_home) == JVM_DIR:
        commands.append(["archlinux-java", "unset"])
        return commands
    for tool in TOOLS:
        binary = os.path.join(java_home, "bin", tool)
        commands.append(["update-alternatives", "--remove", tool, binary])
    return commands
