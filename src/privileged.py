# SPDX-License-Identifier: GPL-3.0-or-later
"""Spawns the privileged helper through pkexec and streams its output."""

import os
from gettext import gettext as _

from gi.repository import Gio, GLib

CWD = os.path.dirname(os.path.abspath(__file__))
HELPER = os.path.join(CWD, "helper.py")
PKEXEC = "/usr/bin/pkexec"


class Privileged:
    def __init__(self):
        self.process = None
        self.process_id = None

    def run(self, argv, on_progress, on_finished):
        params = [PKEXEC, HELPER, *argv]
        errors = []

        launcher = Gio.SubprocessLauncher.new(
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
        )
        process = launcher.spawnv(params)
        self.process = process
        self.process_id = process.get_identifier()

        stdout = Gio.DataInputStream.new(process.get_stdout_pipe())
        stderr = Gio.DataInputStream.new(process.get_stderr_pipe())

        def read(stream, callback):
            stream.read_line_async(GLib.PRIORITY_DEFAULT, None, callback)

        def stdout_cb(stream, result):
            try:
                line, _length = stream.read_line_finish_utf8(result)
            except GLib.Error:
                return
            if line is None:
                return
            print(line)
            parts = line.split(":")
            if "dlstatus" in parts:
                on_progress(float(parts[2]), _("Downloading"))
            elif "pmstatus" in parts:
                on_progress(float(parts[2]), parts[3].strip())
            read(stream, stdout_cb)

        def stderr_cb(stream, result):
            try:
                line, _length = stream.read_line_finish_utf8(result)
            except GLib.Error:
                return
            if line is None:
                return
            errors.append(line)
            print(line)
            read(stream, stderr_cb)

        def finished(proc, result):
            try:
                proc.wait_finish(result)
                code = proc.get_exit_status()
            except GLib.Error:
                code = 1
            self.process = None
            self.process_id = None
            message = errors[-1].replace("error: ", "") if errors else ""
            on_finished(code, message)

        read(stdout, stdout_cb)
        read(stderr, stderr_cb)
        process.wait_async(None, finished)

    def cancel(self):
        if self.process_id:
            Gio.Subprocess.new(
                [PKEXEC, HELPER, "kill", self.process_id],
                Gio.SubprocessFlags.STDOUT_PIPE,
            )
