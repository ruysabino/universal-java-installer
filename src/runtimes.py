# SPDX-License-Identifier: GPL-3.0-or-later
"""Catalog of Java runtimes handled by the application.

Two kinds of entries exist:

* ``distro``  - installed through the native package manager of the running
  distribution (OpenJDK builds shipped by Debian/Ubuntu, Fedora, Arch ...).
* ``oracle``  - Oracle JDK builds. Oracle binaries are **not** redistributed by
  this project: they are downloaded straight from Oracle's own servers after
  the user accepts the Oracle No-Fee Terms and Conditions (NFTC) / BCL.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Runtime:
    id: str
    name: str
    vendor: str
    kind: str  # "distro" | "oracle"
    feature: int  # java feature release, e.g. 21
    # distro packages per backend id
    packages: Dict[str, List[str]] = field(default_factory=dict)
    # oracle download metadata
    oracle_family: Optional[str] = None  # "current" | "archive"
    oracle_version: Optional[str] = None  # full version for archive downloads
    license_id: Optional[str] = None
    license_url: Optional[str] = None
    architectures: List[str] = field(default_factory=lambda: ["x64", "aarch64"])
    lts: bool = False

    @property
    def is_oracle(self) -> bool:
        return self.kind == "oracle"


NFTC = "Oracle No-Fee Terms and Conditions (NFTC)"
NFTC_URL = "https://www.oracle.com/downloads/licenses/no-fee-license.html"
BCL = "Oracle Binary Code License / OTN License Agreement"
BCL_URL = "https://www.oracle.com/downloads/licenses/javase-license1.html"


def _openjdk(feature: int, lts: bool = False) -> Runtime:
    return Runtime(
        id=f"openjdk-{feature}",
        name=f"OpenJDK {feature}",
        vendor="OpenJDK (distribution build)",
        kind="distro",
        feature=feature,
        lts=lts,
        packages={
            "apt": [f"openjdk-{feature}-jdk"],
            "dnf": [f"java-{feature}-openjdk-devel"],
            "pacman": [f"jdk{feature}-openjdk"],
        },
    )


def _oracle(feature: int, version: Optional[str] = None, lts: bool = False) -> Runtime:
    archive = version is not None
    return Runtime(
        id=f"oracle-jdk-{feature}",
        name=f"Oracle JDK {feature}",
        vendor="Oracle",
        kind="oracle",
        feature=feature,
        lts=lts,
        oracle_family="archive" if archive else "current",
        oracle_version=version,
        license_id=NFTC,
        license_url=NFTC_URL,
    )


RUNTIMES: List[Runtime] = [
    _openjdk(25),
    _openjdk(21, lts=True),
    _openjdk(17, lts=True),
    _openjdk(11, lts=True),
    _openjdk(8, lts=True),
    _oracle(25),
    _oracle(21, lts=True),
    _oracle(17, version="17.0.12", lts=True),  # 17 moved to Oracle's archive area
]


def by_id(runtime_id: str) -> Optional[Runtime]:
    for runtime in RUNTIMES:
        if runtime.id == runtime_id:
            return runtime
    return None


def available_for(backend_id: str, arch: str) -> List[Runtime]:
    result = []
    for runtime in RUNTIMES:
        if arch not in runtime.architectures:
            continue
        if runtime.kind == "distro" and not runtime.packages.get(backend_id):
            continue
        result.append(runtime)
    return result
