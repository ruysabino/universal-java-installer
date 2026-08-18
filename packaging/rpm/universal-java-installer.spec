Name:           universal-java-installer
Version:        1.0.0
Release:        1%{?dist}
Summary:        Install and manage OpenJDK and Oracle JDK versions
License:        GPL-3.0-or-later
URL:            https://github.com/ruysabino/universal-java-installer
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  meson ninja-build gettext python3-devel
Requires:       python3 python3-gobject gtk4 libadwaita polkit ca-certificates

%description
Graphical (GTK4/libadwaita) manager for OpenJDK and Oracle JDK runtimes.
OpenJDK is installed through dnf; Oracle JDK is downloaded directly from
Oracle after explicit licence acceptance and SHA-256 verification.

%prep
%autosetup

%build
%meson
%meson_build

%install
%meson_install

%files
%license LICENSE
%doc README.md NOTICE
%{_bindir}/universal-java-installer
%{_datadir}/universal-java-installer/
%{_datadir}/applications/io.github.ruysabino.JavaInstaller.desktop
%{_datadir}/metainfo/io.github.ruysabino.JavaInstaller.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/io.github.ruysabino.JavaInstaller.svg
%{_datadir}/polkit-1/actions/io.github.ruysabino.JavaInstaller.policy
%{_datadir}/locale/*/LC_MESSAGES/universal-java-installer.mo

%changelog
* Tue Aug 18 2026 Ruy Sabino Pereira <ruysabino@users.noreply.github.com> - 1.0.0-1
- Initial fork release.
