# Universal Java Installer

Install, remove and switch Java runtimes from a graphical app — on **any** major
Linux family, not only Pardus.

This is a fork of [`pardus/pardus-java-installer`](https://github.com/pardus/pardus-java-installer)
(GPL-3.0-or-later), rewritten for portability:

| | Upstream (Pardus) | This fork |
|---|---|---|
| Toolkit | GTK3 + Glade | **GTK4 + libadwaita** |
| Package manager | `apt` only | **apt · dnf · pacman** (auto-detected) |
| Default JVM | `update-alternatives` | `update-alternatives` **or `archlinux-java`** |
| Oracle JDK | repackaged `.deb` from the Pardus repo | **downloaded from Oracle**, licence shown and accepted in-app, SHA-256 verified |
| Distros | Pardus | Debian, Ubuntu, Mint, Pop!\_OS, Fedora, RHEL, Arch, Manjaro, EndeavourOS … |

## Supported runtimes

* **OpenJDK 8 / 11 / 17 / 21 / 25** — installed from your distribution's repositories
  (`openjdk-N-jdk`, `java-N-openjdk-devel`, `jdkN-openjdk`). Entries not present
  in your repos are shown as unavailable instead of failing.
* **Oracle JDK 17 / 21 / 25** — fetched from `download.oracle.com`, checked
  against the `.sha256` Oracle publishes next to each archive, then unpacked to
  `/usr/lib/jvm/java-<feature>-oracle-<version>` and registered as an
  alternative.

Architectures: `x86_64` and `aarch64`.

## Install

### Debian / Ubuntu / Mint / Pop!_OS

```sh
sudo apt install -y devscripts debhelper dh-python meson ninja-build gettext
dpkg-buildpackage -us -uc -b
sudo apt install ../universal-java-installer_*.deb
```

### Fedora / RHEL

```sh
sudo dnf install -y rpm-build meson ninja-build gettext python3-devel
rpmbuild -ba packaging/rpm/universal-java-installer.spec
sudo dnf install ~/rpmbuild/RPMS/noarch/universal-java-installer-*.rpm
```

### Arch / Manjaro / EndeavourOS

```sh
cd packaging/arch && makepkg -si
```

### Any distro (meson, from source)

```sh
sudo pacman -S --needed meson ninja gtk4 libadwaita python-gobject polkit   # or the apt/dnf equivalent
meson setup build --prefix=/usr
meson compile -C build
sudo meson install -C build
```

Runtime dependencies: `python3`, `python3-gi` (PyGObject), GTK 4, libadwaita 1,
polkit and `ca-certificates`.

## How privileges work

The GUI never runs as root. Every privileged operation goes through a single
helper (`src/helper.py`) launched by `pkexec` under the polkit action
`io.github.ruysabino.JavaInstaller.helper`. The helper:

* accepts a fixed set of operations and validates the runtime id against the
  in-tree catalog — the GUI cannot make it run an arbitrary command line;
* refuses to touch any path outside `/usr/lib/jvm`;
* re-verifies the SHA-256 of an Oracle archive as root before extracting it, and
  rejects archives containing traversal paths or unsafe links.

## Licensing and trademarks

* This project: **GPL-3.0-or-later** (inherited from upstream). See `LICENSE`.
* Attribution to Pardus, Oracle, OpenJDK and the GTK stack: see `NOTICE`.
* **No Oracle binary is redistributed.** Oracle archives are downloaded by the
  user, from Oracle, after accepting the
  [Oracle No-Fee Terms and Conditions](https://www.oracle.com/downloads/licenses/no-fee-license.html)
  shown in the app.
* Not affiliated with, endorsed by or sponsored by Pardus / TÜBİTAK ULAKBİM or
  Oracle. "Pardus", "Oracle" and "Java" are trademarks of their respective
  owners and are used only descriptively.

## Development

```sh
JAVA_INSTALLER_BACKEND=pacman python3 src/main.py   # force a backend while testing
python3 -m compileall -q src
ruff check src
```

Translations live in `po/` (English source, plus `pt`, `es`, `tr`). Add a
language by dropping `<lang>.po` there and listing it in `po/LINGUAS`.

## Credits

Original work by the Pardus team (Fatih Altun and contributors),
`dev@pardus.org.tr`. Thank you for releasing it under a free licence — this fork
only exists because of that.
