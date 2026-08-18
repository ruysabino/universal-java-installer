# SPDX-License-Identifier: GPL-3.0-or-later
"""Main window (GTK4 + libadwaita)."""

import os
import tempfile
import threading
from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

import alternatives  # noqa: E402
import backends  # noqa: E402
import oracle  # noqa: E402
import runtimes  # noqa: E402
from privileged import Privileged  # noqa: E402

APP_ID = "io.github.ruysabino.JavaInstaller"


class RuntimeRow(Adw.ActionRow):
    def __init__(self, runtime, window):
        super().__init__()
        self.runtime = runtime
        self.window = window

        self.set_title(runtime.name)
        self.installed = False
        self.is_default = False
        self.unavailable = False
        self.java_binary = None

        self.badge = Gtk.Label(label=_("Default"))
        self.badge.add_css_class("success")
        self.badge.add_css_class("caption-heading")
        self.badge.set_visible(False)

        self.default_button = Gtk.Button(label=_("Make default"))
        self.default_button.set_valign(Gtk.Align.CENTER)
        self.default_button.connect("clicked", self._on_default)

        self.action_button = Gtk.Button(label=_("Install"))
        self.action_button.set_valign(Gtk.Align.CENTER)
        self.action_button.add_css_class("suggested-action")
        self.action_button.connect("clicked", self._on_action)

        box = Gtk.Box(spacing=8)
        box.append(self.badge)
        box.append(self.default_button)
        box.append(self.action_button)
        self.add_suffix(box)

    def refresh(self, backend, default_path):
        runtime = self.runtime
        self.unavailable = False
        if runtime.is_oracle:
            candidates = alternatives.find_java_binaries(runtime.feature, "oracle")
            self.installed = bool(candidates)
            self.java_binary = candidates[0] if candidates else None
        else:
            packages = runtime.packages.get(backend.id, [])
            self.installed = (
                all(backend.is_installed(p) for p in packages) if packages else False
            )
            if not self.installed and not backend.package_exists(packages[0]):
                self.unavailable = True
            candidates = [
                b
                for b in alternatives.find_java_binaries(runtime.feature)
                if "oracle" not in b.lower()
            ]
            self.java_binary = candidates[0] if candidates else None

        self.is_default = bool(
            self.java_binary and default_path and os.path.realpath(self.java_binary)
            == os.path.realpath(default_path)
        )

        subtitle = [runtime.vendor]
        if runtime.lts:
            subtitle.append("LTS")
        if runtime.is_oracle:
            subtitle.append(_("downloaded from Oracle · licence acceptance required"))
        self.set_subtitle(" · ".join(subtitle))

        self.action_button.set_label(_("Remove") if self.installed else _("Install"))
        self.action_button.remove_css_class("suggested-action")
        self.action_button.remove_css_class("destructive-action")
        self.action_button.add_css_class(
            "destructive-action" if self.installed else "suggested-action"
        )
        if self.unavailable:
            self.set_subtitle(
                self.get_subtitle() + " · " + _("not available in your repositories")
            )
            self.action_button.set_sensitive(False)
        else:
            self.action_button.set_sensitive(not self.window.busy)
        self.default_button.set_visible(self.installed and not self.is_default)
        self.default_button.set_sensitive(bool(self.java_binary))
        self.badge.set_visible(self.is_default)

    def set_busy(self, busy):
        self.action_button.set_sensitive(not busy)
        self.default_button.set_sensitive(not busy)

    def _on_action(self, _button):
        if self.installed:
            self.window.remove_runtime(self.runtime, self.java_binary)
        else:
            self.window.install_runtime(self.runtime)

    def _on_default(self, _button):
        self.window.make_default(self.runtime, self.java_binary)


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, application, backend):
        super().__init__(application=application)
        self.backend = backend
        self.privileged = Privileged()
        self.rows = []
        self.busy = False
        self._cancel = False

        self.set_title(_("Java Installer"))
        self.set_default_size(680, 640)

        self.toasts = Adw.ToastOverlay()
        self.set_content(self.toasts)

        header = Adw.HeaderBar()
        menu = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu.set_menu_model(self._menu_model())
        header.pack_end(menu)

        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("dim-label")
        self.progress = Gtk.ProgressBar(show_text=False)
        self.progress.set_visible(False)

        self.list_box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("boxed-list")

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(18)
        content.set_margin_bottom(18)
        content.set_margin_start(18)
        content.set_margin_end(18)
        content.append(self.list_box)
        content.append(self.progress)
        content.append(self.status)

        scroller = Gtk.ScrolledWindow(vexpand=True)
        scroller.set_child(content)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.append(header)
        if backend is None:
            root.append(self._unsupported_page())
        else:
            root.append(scroller)
        self.toasts.set_child(root)

        if backend is not None:
            self._build_rows()
            self.reload()

    # --- ui helpers -----------------------------------------------------
    def _menu_model(self):
        from gi.repository import Gio

        menu = Gio.Menu()
        menu.append(_("Refresh"), "app.refresh")
        menu.append(_("About"), "app.about")
        return menu

    def _unsupported_page(self):
        page = Adw.StatusPage(
            icon_name="dialog-warning-symbolic",
            title=_("Unsupported system"),
            description=_(
                "No supported package manager (apt, dnf or pacman) was found on "
                "%s." % backends.distro_name()
            ),
        )
        page.set_vexpand(True)
        return page

    def _build_rows(self):
        for runtime in runtimes.available_for(self.backend.id, backends.arch()):
            row = RuntimeRow(runtime, self)
            self.rows.append(row)
            self.list_box.append(row)

    def toast(self, message):
        self.toasts.add_toast(Adw.Toast.new(message))

    def set_busy(self, busy, message=""):
        self.busy = busy
        for row in self.rows:
            row.set_busy(busy)
        self.progress.set_visible(busy)
        self.status.set_text(message)

    def reload(self):
        if self.backend is None:
            return
        default_path = alternatives.current_default()
        for row in self.rows:
            row.refresh(self.backend, default_path)
        self.status.set_text(
            _("%(distro)s · %(backend)s · %(arch)s")
            % {
                "distro": backends.distro_name(),
                "backend": self.backend.name,
                "arch": backends.arch(),
            }
        )

    # --- actions --------------------------------------------------------
    def install_runtime(self, runtime):
        if self.busy:
            return
        if runtime.is_oracle:
            self._confirm_oracle(runtime)
        else:
            self._run_privileged(
                ["install-package", runtime.id],
                _("Installing %s…") % runtime.name,
            )

    def remove_runtime(self, runtime, java_binary):
        if self.busy:
            return
        if runtime.is_oracle:
            if not java_binary:
                return
            home = alternatives.java_home_of(java_binary)
            self._run_privileged(
                ["remove-jvm", home], _("Removing %s…") % runtime.name
            )
        else:
            self._run_privileged(
                ["remove-package", runtime.id], _("Removing %s…") % runtime.name
            )

    def make_default(self, runtime, java_binary):
        if self.busy or not java_binary:
            return
        self._run_privileged(
            ["set-default", java_binary],
            _("Setting %s as default…") % runtime.name,
        )

    def _confirm_oracle(self, runtime):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_("Oracle licence agreement"),
            body=_(
                "%(name)s is downloaded directly from Oracle and is not "
                "redistributed by this application.\n\nBy continuing you accept "
                "the %(licence)s:\n%(url)s"
            )
            % {
                "name": runtime.name,
                "licence": runtime.license_id,
                "url": runtime.license_url,
            },
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("accept", _("I accept · Download"))
        dialog.set_response_appearance("accept", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("accept")
        dialog.connect(
            "response",
            lambda _d, response: self._download_oracle(runtime)
            if response == "accept"
            else None,
        )
        dialog.present()

    def _download_oracle(self, runtime):
        self._cancel = False
        self.set_busy(True, _("Downloading %s…") % runtime.name)
        self.progress.set_fraction(0.0)
        url = oracle.download_url(runtime)

        def worker():
            temp = tempfile.NamedTemporaryFile(
                prefix="oracle-jdk-", suffix=".tar.gz", delete=False
            )
            temp.close()
            try:
                expected = oracle.fetch_checksum(url)
                digest = oracle.download(
                    url,
                    temp.name,
                    on_progress=lambda pct: GLib.idle_add(
                        self.progress.set_fraction, pct / 100.0
                    ),
                    cancelled=lambda: self._cancel,
                )
                if expected and expected != digest:
                    raise ValueError(_("checksum published by Oracle does not match"))
                GLib.idle_add(self._install_archive, runtime, temp.name, digest)
            except Exception as error:  # noqa: BLE001
                os.unlink(temp.name)
                GLib.idle_add(self._finish, 1, str(error))

        threading.Thread(target=worker, daemon=True).start()

    def _install_archive(self, runtime, path, digest):
        self.set_busy(True, _("Installing %s…") % runtime.name)
        self.progress.pulse()
        self._run_privileged(
            ["install-archive", runtime.id, path, digest],
            _("Installing %s…") % runtime.name,
            cleanup=path,
        )
        return False

    def _run_privileged(self, argv, message, cleanup=None):
        self.set_busy(True, message)
        self.progress.set_fraction(0.0)

        def on_progress(fraction, text):
            self.progress.set_fraction(fraction / 100.0)
            if text:
                self.status.set_text(text)

        def on_finished(code, error):
            if cleanup and os.path.exists(cleanup):
                os.unlink(cleanup)
            self._finish(code, error)

        self.privileged.run(argv, on_progress, on_finished)

    def _finish(self, code, error=""):
        self.set_busy(False)
        self.reload()
        if code == 0:
            self.toast(_("Done"))
        elif code == 126 or code == 127:
            self.toast(_("Authentication cancelled"))
        else:
            self.toast(error or _("Operation failed (code %s)") % code)
        return False
