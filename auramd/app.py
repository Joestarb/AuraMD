"""
Application class and lifecycle for AuraMD.
Handles startup, command-line arguments, window management, and global actions.
"""

import sys
from pathlib import Path
from typing import List, Optional

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('WebKit', '6.0')
from gi.repository import Gtk, Gio, Adw

from auramd.config import config
from auramd.i18n import set_language, t
from auramd.window import AuraMDWindow


class AuraMDApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id="io.github.auramd.AuraMD",
            flags=Gio.ApplicationFlags.HANDLES_OPEN
        )
        self.window: Optional[AuraMDWindow] = None

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        
        # Initialize language from user config
        saved_lang = config.get("language", "auto")
        set_language(saved_lang)

        # Setup global action accelerators
        self.set_accels_for_action("app.quit", ["<Control>q"])
        self.set_accels_for_action("app.open", ["<Control>o"])

        action_quit = Gio.SimpleAction.new("quit", None)
        action_quit.connect("activate", lambda *a: self.quit())
        self.add_action(action_quit)

    def do_activate(self) -> None:
        """Called when launched without file arguments."""
        if not self.window:
            self.window = AuraMDWindow(application=self)
        self.window.present()

    def do_open(self, files: List[Gio.File], n_files: int, hint: str) -> None:
        """Called when launched with one or more file arguments."""
        if not self.window:
            self.window = AuraMDWindow(application=self)

        if files:
            first_file = files[0]
            path_str = first_file.get_path()
            if path_str:
                self.window.open_file(Path(path_str))

        self.window.present()


def main() -> None:
    app = AuraMDApp()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
