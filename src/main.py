#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Application entry point."""

import gettext
import locale
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

APPNAME = "universal-java-installer"
APP_ID = "io.github.ruysabino.JavaInstaller"
LOCALE_DIR = "/usr/share/locale"
VERSION = "1.0.0"

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass
locale.bindtextdomain(APPNAME, LOCALE_DIR)
locale.textdomain(APPNAME)
gettext.bindtextdomain(APPNAME, LOCALE_DIR)
gettext.textdomain(APPNAME)
_ = gettext.gettext

import backends  # noqa: E402
from window import MainWindow  # noqa: E402


class Application(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.window = None

    def do_activate(self):
        if self.window is None:
            self.window = MainWindow(self, backends.detect())
            self._add_action("refresh", lambda *_a: self.window.reload())
            self._add_action("about", lambda *_a: self._about())
        self.window.present()

    def _add_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)

    def _about(self):
        about = Adw.AboutWindow(
            transient_for=self.window,
            application_name=_("Java Installer"),
            application_icon=APP_ID,
            version=VERSION,
            developer_name="Ruy Sabino Pereira",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/ruysabino/universal-java-installer",
            issue_url="https://github.com/ruysabino/universal-java-installer/issues",
            comments=_(
                "Install and manage OpenJDK and Oracle JDK versions on Debian, "
                "Ubuntu, Fedora, Arch and derivatives.\n\n"
                "Fork of pardus-java-installer by Pardus (TÜBİTAK ULAKBİM), "
                "GPL-3.0-or-later. Not affiliated with Pardus or Oracle."
            ),
        )
        about.present()


def main():
    return Application().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
