"""
Main application window for AuraMD.
Modern Libadwaita interface with collapsible outline sidebar,
document statistics, live file watching, in-document search,
typography/theme controls, drag-and-drop, and full English/Spanish i18n.
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('WebKit', '6.0')
from gi.repository import Gtk, Gdk, Gio, GLib, Pango, Adw, WebKit

from auramd.config import config
from auramd.i18n import t, set_language, get_current_language
from auramd.markdown_engine import get_base_html, calculate_reading_stats, VENDOR_DIR


class AuraMDWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        
        self.current_file: Optional[Path] = None
        self.current_content: str = ""
        self.file_monitor: Optional[Gio.FileMonitor] = None
        self.monitor_handler_id: Optional[int] = None
        self.current_scroll_y: float = 0.0
        self.zen_mode_active: bool = False
        self.headings: List[Dict[str, Any]] = []
        self.active_heading_id: Optional[str] = None
        self.shortcut_rows: List[Tuple[Adw.ActionRow, str]] = []
        
        # Load geometry from settings
        self.set_default_size(
            config.get("window_width", 1050),
            config.get("window_height", 720)
        )
        if config.get("window_maximized", False):
            self.maximize()
            
        self.setup_ui()
        self.apply_theme(config.get("color_scheme", "system"))
        self.setup_drop_target()
        self.setup_key_controllers()

    def setup_ui(self) -> None:
        """Constructs the Libadwaita modern user interface."""
        # Top-level Toast Overlay
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Split View (collapsible sidebar + reader)
        self.split_view = Adw.OverlaySplitView()
        # When no file is open, start with sidebar hidden to keep welcome screen minimalist
        self.split_view.set_show_sidebar(False)
        self.split_view.set_min_sidebar_width(240)
        self.split_view.set_max_sidebar_width(380)
        self.split_view.set_sidebar_width_fraction(0.26)
        self.toast_overlay.set_child(self.split_view)

        # Build Sidebar & Main Content
        self.build_sidebar()
        self.build_main_view()
        self.update_ui_strings()

    def build_sidebar(self) -> None:
        """Constructs the sidebar with Outline and Statistics."""
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.sidebar_box.add_css_class("background")
        
        # Sidebar Header Bar
        self.sidebar_header = Adw.HeaderBar()
        self.sidebar_header.set_show_end_title_buttons(False)
        self.sidebar_header.set_show_start_title_buttons(False)
        
        # View switcher for Outline / Statistics
        self.sidebar_stack = Gtk.Stack()
        self.sidebar_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        
        # Stack Switcher in Sidebar Header
        self.stack_switcher = Gtk.StackSwitcher()
        self.stack_switcher.set_stack(self.sidebar_stack)
        self.sidebar_header.set_title_widget(self.stack_switcher)
        self.sidebar_box.append(self.sidebar_header)

        # --- Tab 1: Outline ---
        self.outline_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.outline_box.set_margin_top(8)
        self.outline_box.set_margin_bottom(8)
        self.outline_box.set_margin_start(8)
        self.outline_box.set_margin_end(8)

        # Subtle explanation header
        self.outline_header_lbl = Gtk.Label()
        self.outline_header_lbl.add_css_class("caption")
        self.outline_header_lbl.add_css_class("dim-label")
        self.outline_header_lbl.set_halign(Gtk.Align.START)
        self.outline_header_lbl.set_margin_start(6)
        self.outline_header_lbl.set_margin_bottom(4)
        self.outline_box.append(self.outline_header_lbl)

        self.outline_scrolled = Gtk.ScrolledWindow()
        self.outline_scrolled.set_vexpand(True)
        self.outline_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.outline_listbox = Gtk.ListBox()
        self.outline_listbox.add_css_class("navigation-sidebar")
        self.outline_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.outline_listbox.connect("row-activated", self.on_outline_row_activated)
        self.outline_scrolled.set_child(self.outline_listbox)
        self.outline_box.append(self.outline_scrolled)

        # Empty Outline Placeholder
        self.outline_empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.outline_empty_box.set_valign(Gtk.Align.CENTER)
        self.outline_empty_box.set_vexpand(True)
        self.outline_empty_box.set_margin_start(16)
        self.outline_empty_box.set_margin_end(16)

        self.outline_empty_label = Gtk.Label()
        self.outline_empty_label.add_css_class("heading")
        self.outline_empty_label.set_wrap(True)
        self.outline_empty_label.set_justify(Gtk.Justification.CENTER)
        self.outline_empty_box.append(self.outline_empty_label)

        self.outline_empty_sublabel = Gtk.Label()
        self.outline_empty_sublabel.add_css_class("dim-label")
        self.outline_empty_sublabel.set_wrap(True)
        self.outline_empty_sublabel.set_justify(Gtk.Justification.CENTER)
        self.outline_empty_box.append(self.outline_empty_sublabel)

        self.outline_box.append(self.outline_empty_box)

        # --- Tab 2: Statistics ---
        self.stats_scrolled = Gtk.ScrolledWindow()
        self.stats_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.stats_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.stats_box.set_margin_top(14)
        self.stats_box.set_margin_bottom(14)
        self.stats_box.set_margin_start(10)
        self.stats_box.set_margin_end(10)

        # Stats Header Label
        self.stats_header_lbl = Gtk.Label()
        self.stats_header_lbl.add_css_class("caption")
        self.stats_header_lbl.add_css_class("dim-label")
        self.stats_header_lbl.set_halign(Gtk.Align.START)
        self.stats_header_lbl.set_margin_start(6)
        self.stats_box.append(self.stats_header_lbl)

        # Stats Card (Boxed list)
        self.stats_listbox = Gtk.ListBox()
        self.stats_listbox.add_css_class("boxed-list")
        self.stats_listbox.set_selection_mode(Gtk.SelectionMode.NONE)

        # Stat rows
        self.stat_row_read_time = Adw.ActionRow(icon_name="alarm-symbolic")
        self.stat_row_words = Adw.ActionRow(icon_name="format-text-symbolic")
        self.stat_row_chars = Adw.ActionRow(icon_name="insert-text-symbolic")
        self.stat_row_headings = Adw.ActionRow(icon_name="view-list-bullet-symbolic")
        self.stat_row_lines = Adw.ActionRow(icon_name="document-properties-symbolic")

        self.stats_listbox.append(self.stat_row_read_time)
        self.stats_listbox.append(self.stat_row_words)
        self.stats_listbox.append(self.stat_row_chars)
        self.stats_listbox.append(self.stat_row_headings)
        self.stats_listbox.append(self.stat_row_lines)

        self.stats_box.append(self.stats_listbox)
        self.stats_scrolled.set_child(self.stats_box)

        # Add pages to stack
        self.page_outline = self.sidebar_stack.add_titled(self.outline_box, "outline", t("tab_outline"))
        self.page_stats = self.sidebar_stack.add_titled(self.stats_scrolled, "stats", t("tab_stats"))
        self.sidebar_stack.set_vexpand(True)
        self.sidebar_box.append(self.sidebar_stack)

        self.split_view.set_sidebar(self.sidebar_box)

    def build_main_view(self) -> None:
        """Constructs the main ToolbarView with HeaderBar, SearchBar, and WebKit."""
        self.toolbar_view = Adw.ToolbarView()
        self.split_view.set_content(self.toolbar_view)

        # --- Header Bar ---
        self.header_bar = Adw.HeaderBar()
        self.header_bar.set_show_title(True)

        # Left / Start Buttons
        self.btn_toggle_sidebar = Gtk.Button(icon_name="sidebar-show-symbolic")
        self.btn_toggle_sidebar.connect("clicked", self.on_toggle_sidebar_clicked)
        self.header_bar.pack_start(self.btn_toggle_sidebar)

        self.btn_open = Gtk.Button(icon_name="document-open-symbolic")
        self.btn_open.connect("clicked", self.on_open_clicked)
        self.header_bar.pack_start(self.btn_open)

        self.btn_recent = Gtk.MenuButton(icon_name="document-open-recent-symbolic")
        self.header_bar.pack_start(self.btn_recent)
        self.build_recent_popover()

        # Center Title
        self.window_title = Adw.WindowTitle()
        self.window_title.set_title(t("app_title"))
        self.window_title.set_subtitle(t("app_subtitle"))
        self.header_bar.set_title_widget(self.window_title)

        # Right / End Buttons
        self.btn_search = Gtk.ToggleButton(icon_name="edit-find-symbolic")
        self.btn_search.connect("toggled", self.on_search_toggled)
        self.header_bar.pack_end(self.btn_search)

        self.btn_zen = Gtk.Button(icon_name="view-fullscreen-symbolic")
        self.btn_zen.connect("clicked", self.on_toggle_zen_mode)
        self.header_bar.pack_end(self.btn_zen)

        # Appearance Popover Button
        self.btn_appearance = Gtk.MenuButton(icon_name="font-select-symbolic")
        self.build_appearance_popover()
        self.header_bar.pack_end(self.btn_appearance)

        # Main App Menu Button
        self.btn_menu = Gtk.MenuButton(icon_name="open-menu-symbolic")
        self.build_main_menu_popover()
        self.header_bar.pack_end(self.btn_menu)

        self.toolbar_view.add_top_bar(self.header_bar)

        # --- In-Page Search Bar ---
        self.search_bar = Gtk.SearchBar()
        self.search_bar.set_show_close_button(True)
        self.search_bar.connect("notify::search-mode-enabled", self.on_search_bar_mode_changed)

        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_box.set_halign(Gtk.Align.CENTER)
        search_box.set_margin_top(6)
        search_box.set_margin_bottom(6)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_hexpand(True)
        self.search_entry.set_size_request(280, -1)
        self.search_entry.connect("search-changed", self.on_search_text_changed)
        self.search_entry.connect("activate", self.on_search_next_clicked)
        search_box.append(self.search_entry)

        self.search_count_label = Gtk.Label()
        self.search_count_label.add_css_class("dim-label")
        self.search_count_label.set_margin_start(4)
        self.search_count_label.set_margin_end(4)
        search_box.append(self.search_count_label)

        self.btn_search_prev = Gtk.Button(icon_name="go-up-symbolic")
        self.btn_search_prev.connect("clicked", self.on_search_prev_clicked)
        search_box.append(self.btn_search_prev)

        self.btn_search_next = Gtk.Button(icon_name="go-down-symbolic")
        self.btn_search_next.connect("clicked", self.on_search_next_clicked)
        search_box.append(self.btn_search_next)

        self.search_bar.set_child(search_box)
        self.search_bar.connect_entry(self.search_entry)
        self.toolbar_view.add_top_bar(self.search_bar)

        # --- Main Content Stack (Empty State vs Reader WebView) ---
        self.main_stack = Gtk.Stack()
        self.main_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        # Page 1: Empty Status Page
        self.status_page = Adw.StatusPage()
        self.status_page.set_icon_name("text-x-generic-symbolic")
        self.status_page.set_title(t("empty_title"))
        self.status_page.set_description(t("empty_subtitle"))

        # Buttons Box
        buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        buttons_box.set_halign(Gtk.Align.CENTER)

        self.btn_open_large = Gtk.Button()
        self.btn_open_large.set_label(t("btn_open_document"))
        self.btn_open_large.add_css_class("pill")
        self.btn_open_large.add_css_class("suggested-action")
        self.btn_open_large.connect("clicked", self.on_open_clicked)
        buttons_box.append(self.btn_open_large)

        self.btn_open_sample = Gtk.Button()
        self.btn_open_sample.set_label(t("btn_open_sample"))
        self.btn_open_sample.add_css_class("pill")
        self.btn_open_sample.connect("clicked", self.on_open_sample_clicked)
        buttons_box.append(self.btn_open_sample)

        # Quick Shortcuts Card inside Empty Status Page
        empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        empty_box.append(buttons_box)

        self.shortcuts_title_lbl = Gtk.Label(label=t("quick_shortcuts"))
        self.shortcuts_title_lbl.add_css_class("heading")
        self.shortcuts_title_lbl.set_margin_top(12)
        empty_box.append(self.shortcuts_title_lbl)

        shortcuts_card = Gtk.ListBox()
        shortcuts_card.add_css_class("boxed-list")
        shortcuts_card.set_selection_mode(Gtk.SelectionMode.NONE)
        shortcuts_card.set_size_request(360, -1)
        shortcuts_card.set_halign(Gtk.Align.CENTER)

        shortcut_items = [
            ("shortcut_open", "Ctrl+O"),
            ("shortcut_zen", "F11"),
            ("shortcut_search", "Ctrl+F"),
            ("shortcut_print", "Ctrl+P"),
        ]

        self.shortcut_rows = []
        for s_key, s_badge in shortcut_items:
            row = Adw.ActionRow(title=t(s_key))
            badge = Gtk.Label(label=s_badge)
            badge.add_css_class("dim-label")
            row.add_suffix(badge)
            shortcuts_card.append(row)
            self.shortcut_rows.append((row, s_key))

        empty_box.append(shortcuts_card)
        self.status_page.set_child(empty_box)
        self.main_stack.add_named(self.status_page, "empty")

        # Page 2: WebKit WebView
        self.build_webview()
        self.main_stack.add_named(self.webview, "reader")

        self.toolbar_view.set_content(self.main_stack)
        self.main_stack.set_visible_child_name("empty")

    def build_webview(self) -> None:
        """Constructs WebKit WebView with bi-directional JavaScript bridge."""
        ucm = WebKit.UserContentManager()
        ucm.register_script_message_handler("app")
        ucm.connect("script-message-received::app", self.on_js_message_received)

        self.webview = WebKit.WebView(user_content_manager=ucm)
        self.webview.set_hexpand(True)
        self.webview.set_vexpand(True)

        settings = self.webview.get_settings()
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_allow_universal_access_from_file_urls(True)
        settings.set_enable_developer_extras(True)
        
        # Find Controller
        self.find_controller = self.webview.get_find_controller()
        self.find_controller.connect("counted-matches", self.on_find_counted_matches)
        self.find_controller.connect("failed-to-find-text", self.on_find_failed)

        # Zoom level
        self.webview.set_zoom_level(config.get("zoom_level", 1.0))

    def setup_drop_target(self) -> None:
        """Enables drag-and-drop of Markdown files into the application."""
        target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        target.connect("drop", self.on_file_dropped)
        self.add_controller(target)

    def setup_key_controllers(self) -> None:
        """Configures keyboard shortcuts."""
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)

    def on_key_pressed(self, controller: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> bool:
        """Handles global key events."""
        is_ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)

        # F11: Zen Mode
        if keyval == Gdk.KEY_F11:
            self.on_toggle_zen_mode(None)
            return True

        # Esc: Exit Zen Mode or close search
        if keyval == Gdk.KEY_Escape:
            if self.zen_mode_active:
                self.on_toggle_zen_mode(None)
                return True
            if self.search_bar.get_search_mode():
                self.search_bar.set_search_mode(False)
                return True

        # F9: Toggle Sidebar
        if keyval == Gdk.KEY_F9:
            self.on_toggle_sidebar_clicked(None)
            return True

        # F5 or Ctrl+R: Reload
        if keyval == Gdk.KEY_F5 or (is_ctrl and keyval in (Gdk.KEY_r, Gdk.KEY_R)):
            self.reload_file()
            return True

        # Ctrl+O: Open
        if is_ctrl and keyval in (Gdk.KEY_o, Gdk.KEY_O):
            self.on_open_clicked(None)
            return True

        # Ctrl+F: Search
        if is_ctrl and keyval in (Gdk.KEY_f, Gdk.KEY_F):
            self.btn_search.set_active(True)
            self.search_entry.grab_focus()
            return True

        # Ctrl+P: Print / Export PDF
        if is_ctrl and keyval in (Gdk.KEY_p, Gdk.KEY_P):
            self.on_print_clicked(None)
            return True

        # Ctrl+E: Open in Editor
        if is_ctrl and keyval in (Gdk.KEY_e, Gdk.KEY_E):
            self.on_open_in_editor(None)
            return True

        # Ctrl++: Zoom In
        if is_ctrl and keyval in (Gdk.KEY_plus, Gdk.KEY_equal, Gdk.KEY_KP_Add):
            self.adjust_zoom(0.1)
            return True

        # Ctrl+-: Zoom Out
        if is_ctrl and keyval in (Gdk.KEY_minus, Gdk.KEY_KP_Subtract):
            self.adjust_zoom(-0.1)
            return True

        # Ctrl+0: Reset Zoom
        if is_ctrl and keyval in (Gdk.KEY_0, Gdk.KEY_KP_0):
            self.reset_zoom()
            return True

        return False

    def build_recent_popover(self) -> None:
        """Constructs the Recent Documents dropdown popover."""
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        recent_files = config.get("recent_files", [])
        if not recent_files:
            empty_lbl = Gtk.Label(label=t("no_recent_files"))
            empty_lbl.add_css_class("dim-label")
            empty_lbl.set_margin_top(12)
            empty_lbl.set_margin_bottom(12)
            box.append(empty_lbl)
        else:
            listbox = Gtk.ListBox()
            listbox.add_css_class("boxed-list")
            listbox.set_selection_mode(Gtk.SelectionMode.NONE)

            for path_str in recent_files:
                p = Path(path_str)
                row = Adw.ActionRow()
                row.set_title(p.name)
                row.set_subtitle(str(p.parent))
                row.set_activatable(True)
                
                # Click handler
                def make_click_handler(target_p: Path):
                    return lambda *args: (popover.popdown(), self.open_file(target_p))
                
                click_gesture = Gtk.GestureClick()
                click_gesture.connect("released", make_click_handler(p))
                row.add_controller(click_gesture)
                listbox.append(row)

            box.append(listbox)

            # Clear button
            btn_clear = Gtk.Button(label=t("clear_recent"))
            btn_clear.add_css_class("flat")
            btn_clear.set_margin_top(6)
            def on_clear(*args):
                config.clear_recent_files()
                popover.popdown()
                self.build_recent_popover()
            btn_clear.connect("clicked", on_clear)
            box.append(btn_clear)

        popover.set_child(box)
        self.btn_recent.set_popover(popover)

    def build_appearance_popover(self) -> None:
        """Constructs Appearance and Typography settings popover."""
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_size_request(260, -1)

        # 1. Theme Selection
        theme_lbl = Gtk.Label(label=t("theme"))
        theme_lbl.add_css_class("heading")
        theme_lbl.set_halign(Gtk.Align.START)
        box.append(theme_lbl)

        theme_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        theme_box.set_homogeneous(True)

        current_theme = config.get("color_scheme", "system")
        for mode, label, icon in [
            ("system", t("theme_system"), "preferences-system-symbolic"),
            ("light", t("theme_light"), "weather-clear-symbolic"),
            ("dark", t("theme_dark"), "weather-clear-night-symbolic"),
        ]:
            btn = Gtk.ToggleButton(label=label, icon_name=icon)
            if current_theme == mode:
                btn.set_active(True)
            def on_theme_toggle(b, m=mode):
                if b.get_active():
                    self.set_color_scheme(m)
                    self.build_appearance_popover()
            btn.connect("toggled", on_theme_toggle)
            theme_box.append(btn)
        box.append(theme_box)

        # 2. Font Family
        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        font_lbl = Gtk.Label(label=t("font_family"))
        font_lbl.add_css_class("heading")
        font_lbl.set_halign(Gtk.Align.START)
        box.append(font_lbl)

        font_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        font_box.set_homogeneous(True)
        current_font = config.get("font_family", "sans")
        for f_key, f_name in [
            ("sans", t("font_sans")),
            ("serif", t("font_serif")),
            ("mono", t("font_mono")),
        ]:
            f_btn = Gtk.ToggleButton(label=f_name)
            if current_font == f_key:
                f_btn.set_active(True)
            def on_font_toggle(b, f=f_key):
                if b.get_active():
                    self.set_font_family(f)
                    self.build_appearance_popover()
            f_btn.connect("toggled", on_font_toggle)
            font_box.append(f_btn)
        box.append(font_box)

        # 3. Reading Width
        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        width_lbl = Gtk.Label(label=t("reading_width"))
        width_lbl.add_css_class("heading")
        width_lbl.set_halign(Gtk.Align.START)
        box.append(width_lbl)

        width_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        width_box.set_homogeneous(True)
        current_width = config.get("reading_width", "standard")
        for w_key, w_name in [
            ("compact", t("width_compact")),
            ("standard", t("width_standard")),
            ("wide", t("width_wide")),
            ("full", t("width_full")),
        ]:
            w_btn = Gtk.ToggleButton(label=w_name)
            if current_width == w_key:
                w_btn.set_active(True)
            def on_width_toggle(b, w=w_key):
                if b.get_active():
                    self.set_reading_width(w)
                    self.build_appearance_popover()
            w_btn.connect("toggled", on_width_toggle)
            width_box.append(w_btn)
        box.append(width_box)

        # 4. Text Size Control
        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        size_lbl = Gtk.Label(label=t("font_size"))
        size_lbl.add_css_class("heading")
        size_lbl.set_halign(Gtk.Align.START)
        box.append(size_lbl)

        size_ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        size_ctrl_box.set_halign(Gtk.Align.FILL)

        btn_size_down = Gtk.Button(label="A-")
        btn_size_down.connect("clicked", lambda *a: self.adjust_font_size(-1))
        size_ctrl_box.append(btn_size_down)

        self.size_val_label = Gtk.Label(label=f"{config.get('font_size', 16)}px")
        self.size_val_label.set_hexpand(True)
        size_ctrl_box.append(self.size_val_label)

        btn_size_up = Gtk.Button(label="A+")
        btn_size_up.connect("clicked", lambda *a: self.adjust_font_size(1))
        size_ctrl_box.append(btn_size_up)

        box.append(size_ctrl_box)

        popover.set_child(box)
        self.btn_appearance.set_popover(popover)

    def build_main_menu_popover(self) -> None:
        """Constructs Main Menu popover."""
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_size_request(240, -1)

        menu_items = [
            (t("reload"), "view-refresh-symbolic", lambda: (popover.popdown(), self.reload_file())),
            (t("open_in_editor"), "accessories-text-editor-symbolic", lambda: (popover.popdown(), self.on_open_in_editor(None))),
            (t("copy_html"), "edit-copy-symbolic", lambda: (popover.popdown(), self.copy_as_html())),
            (t("copy_raw"), "edit-copy-symbolic", lambda: (popover.popdown(), self.copy_raw_markdown())),
            (t("print_export_pdf"), "printer-symbolic", lambda: (popover.popdown(), self.on_print_clicked(None))),
        ]

        for label, icon, callback in menu_items:
            btn = Gtk.Button()
            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            btn_box.append(Gtk.Image.new_from_icon_name(icon))
            btn_box.append(Gtk.Label(label=label))
            btn.set_child(btn_box)
            btn.add_css_class("flat")
            btn.connect("clicked", lambda b, cb=callback: cb())
            box.append(btn)

        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Language Toggle Row (English / Español)
        lang_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lang_box.set_margin_top(4)
        lang_box.set_margin_bottom(4)

        cur_lang = get_current_language()
        btn_es = Gtk.ToggleButton(label="Español")
        btn_en = Gtk.ToggleButton(label="English")
        btn_es.set_active(cur_lang == "es")
        btn_en.set_active(cur_lang == "en")

        def switch_to_es(*args):
            if btn_es.get_active() and cur_lang != "es":
                popover.popdown()
                self.switch_language("es")

        def switch_to_en(*args):
            if btn_en.get_active() and cur_lang != "en":
                popover.popdown()
                self.switch_language("en")

        btn_es.connect("toggled", switch_to_es)
        btn_en.connect("toggled", switch_to_en)
        lang_box.append(btn_es)
        lang_box.append(btn_en)
        box.append(lang_box)

        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Shortcuts & About
        btn_shortcuts = Gtk.Button()
        b_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        b_box.append(Gtk.Image.new_from_icon_name("input-keyboard-symbolic"))
        b_box.append(Gtk.Label(label=t("keyboard_shortcuts")))
        btn_shortcuts.set_child(b_box)
        btn_shortcuts.add_css_class("flat")
        btn_shortcuts.connect("clicked", lambda b: (popover.popdown(), self.show_shortcuts_window()))
        box.append(btn_shortcuts)

        btn_about = Gtk.Button()
        a_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        a_box.append(Gtk.Image.new_from_icon_name("help-about-symbolic"))
        a_box.append(Gtk.Label(label=t("about_auramd")))
        btn_about.set_child(a_box)
        btn_about.add_css_class("flat")
        btn_about.connect("clicked", lambda b: (popover.popdown(), self.show_about_dialog()))
        box.append(btn_about)

        popover.set_child(box)
        self.btn_menu.set_popover(popover)

    def update_ui_strings(self) -> None:
        """Updates all UI text for runtime i18n switching."""
        self.set_title(t("app_name"))
        if not self.current_file:
            self.window_title.set_title(t("app_title"))
            self.window_title.set_subtitle(t("app_subtitle"))

        # Tooltips
        self.btn_toggle_sidebar.set_tooltip_text(t("toggle_sidebar"))
        self.btn_open.set_tooltip_text(t("open_file"))
        self.btn_recent.set_tooltip_text(t("recent_files"))
        self.btn_search.set_tooltip_text(t("search_tooltip"))
        self.btn_zen.set_tooltip_text(t("zen_mode"))
        self.btn_appearance.set_tooltip_text(t("view_options"))
        self.btn_menu.set_tooltip_text(t("main_menu"))

        # Search Bar
        self.search_entry.set_placeholder_text(t("search_placeholder"))
        self.btn_search_prev.set_tooltip_text(t("search_prev"))
        self.btn_search_next.set_tooltip_text(t("search_next"))

        # Sidebar Stack Tab Titles
        if hasattr(self, "page_outline") and self.page_outline:
            self.page_outline.set_title(t("tab_outline"))
        if hasattr(self, "page_stats") and self.page_stats:
            self.page_stats.set_title(t("tab_stats"))

        # Sidebar Content
        self.outline_header_lbl.set_label(t("outline_desc"))
        self.outline_empty_label.set_label(t("outline_empty"))
        self.outline_empty_sublabel.set_label(t("outline_empty_desc"))

        self.stats_header_lbl.set_label(t("stats_desc"))
        self.stat_row_read_time.set_title(t("stats_reading_time"))
        self.stat_row_words.set_title(t("stats_words"))
        self.stat_row_chars.set_title(t("stats_characters"))
        self.stat_row_headings.set_title(t("stats_headings"))
        self.stat_row_lines.set_title(t("stats_lines"))

        # Empty Status Page
        self.status_page.set_title(t("empty_title"))
        self.status_page.set_description(t("empty_subtitle"))
        self.btn_open_large.set_label(t("btn_open_document"))
        self.btn_open_sample.set_label(t("btn_open_sample"))
        self.shortcuts_title_lbl.set_label(t("quick_shortcuts"))

        # Shortcuts list items
        for row, key in self.shortcut_rows:
            row.set_title(t(key))

        # Rebuild popovers to reflect new translations
        self.build_recent_popover()
        self.build_appearance_popover()
        self.build_main_menu_popover()

    def switch_language(self, lang_code: str) -> None:
        """Switches UI language runtime."""
        set_language(lang_code)
        config.set("language", lang_code)
        self.update_ui_strings()
        self.show_toast(t("toast_lang_changed"))
        # Re-render file if open
        if self.current_file:
            self.render_current_document()

    def show_toast(self, text: str) -> None:
        """Displays floating toast notification."""
        toast = Adw.Toast.new(text)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)

    def on_toggle_sidebar_clicked(self, button: Optional[Gtk.Button]) -> None:
        """Toggles the outline and stats sidebar."""
        is_visible = self.split_view.get_show_sidebar()
        self.split_view.set_show_sidebar(not is_visible)
        config.set("show_sidebar", not is_visible)

    def on_toggle_zen_mode(self, button: Optional[Gtk.Button]) -> None:
        """Toggles Zen / Distraction-free reading mode."""
        self.zen_mode_active = not self.zen_mode_active
        if self.zen_mode_active:
            self.fullscreen()
            self.header_bar.set_visible(False)
            self.split_view.set_show_sidebar(False)
            self.show_toast(t("exit_zen_mode"))
        else:
            self.unfullscreen()
            self.header_bar.set_visible(True)
            if self.current_file:
                self.split_view.set_show_sidebar(config.get("show_sidebar", True))

    def on_open_clicked(self, button: Optional[Gtk.Button]) -> None:
        """Opens file dialog to choose a markdown file."""
        dialog = Gtk.FileDialog.new()
        dialog.set_title(t("dialog_open_title"))

        filter_md = Gtk.FileFilter.new()
        filter_md.set_name(t("dialog_filter_md"))
        for ext in ("*.md", "*.markdown", "*.mdown", "*.mkd"):
            filter_md.add_pattern(ext)

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_md)
        dialog.set_filters(filters)

        def on_open_finish(dlg, result):
            try:
                gfile = dlg.open_finish(result)
                if gfile:
                    path = gfile.get_path()
                    if path:
                        self.open_file(Path(path))
            except Exception as e:
                # Cancelled or error
                pass

        dialog.open(self, None, on_open_finish)

    def on_open_sample_clicked(self, *args: Any) -> None:
        """Opens sample demo document based on active language."""
        lang = get_current_language()
        sample_path = Path("/home/arbey/development/auramd") / (f"demo_{lang}.md" if lang in ("en", "es") else "demo_en.md")
        if sample_path.exists():
            self.open_file(sample_path)

    def on_file_dropped(self, target: Gtk.DropTarget, value: Any, x: float, y: float) -> bool:
        """Handles dropped markdown files."""
        if isinstance(value, Gio.File):
            path = value.get_path()
            if path:
                self.open_file(Path(path))
                return True
        return False

    def open_file(self, filepath: Path) -> None:
        """Opens and renders a markdown file from disk."""
        filepath = filepath.resolve()
        if not filepath.exists() or not filepath.is_file():
            self.show_toast(t("toast_file_error", error="File not found"))
            return

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                self.current_content = f.read()
            self.current_file = filepath
            config.add_recent_file(str(filepath))
            self.build_recent_popover()
            self.setup_file_monitor()
            self.render_current_document()
            self.main_stack.set_visible_child_name("reader")
            # Automatically show sidebar if configured
            if config.get("show_sidebar", True):
                self.split_view.set_show_sidebar(True)
        except Exception as e:
            self.show_toast(t("toast_file_error", error=str(e)))

    def render_current_document(self) -> None:
        """Compiles markdown to HTML and loads into WebView."""
        if not self.current_file:
            return

        file_dir = str(self.current_file.parent)
        stats = calculate_reading_stats(self.current_content)
        
        # Update Window Header
        mins = stats["reading_time_mins"]
        mins_str = t("min_read") if mins > 0 else t("less_than_minute")
        time_text = f"{mins} {mins_str}" if mins > 0 else mins_str
        subtitle = f"{time_text} • {stats['words']} {t('stats_words').lower()}"
        
        self.window_title.set_title(self.current_file.name)
        self.window_title.set_subtitle(subtitle)

        # Update Sidebar Stats
        self.stat_row_read_time.set_subtitle(time_text)
        self.stat_row_words.set_subtitle(f"{stats['words']:,}")
        self.stat_row_chars.set_subtitle(f"{stats['characters']:,}")
        self.stat_row_headings.set_subtitle(str(stats["headings"]))
        self.stat_row_lines.set_subtitle(f"{stats['lines']:,}")

        # Generate HTML
        html = get_base_html(
            markdown_content=self.current_content,
            file_dir=file_dir,
            theme=config.get("color_scheme", "system"),
            font_family=config.get("font_family", "sans"),
            font_size=config.get("font_size", 16),
            reading_width=config.get("reading_width", "standard"),
            preserve_scroll=self.current_scroll_y,
            lang=get_current_language()
        )

        base_uri = self.current_file.parent.as_uri() + "/"
        self.webview.load_html(html, base_uri)

    def reload_file(self) -> None:
        """Reloads current document from disk while preserving reading position."""
        if not self.current_file or not self.current_file.exists():
            return
        try:
            with open(self.current_file, "r", encoding="utf-8", errors="replace") as f:
                self.current_content = f.read()
            self.render_current_document()
            self.show_toast(t("toast_reloaded"))
        except Exception as e:
            self.show_toast(t("toast_file_error", error=str(e)))

    def setup_file_monitor(self) -> None:
        """Watches the current file on disk for external edits."""
        if self.file_monitor:
            if self.monitor_handler_id:
                self.file_monitor.disconnect(self.monitor_handler_id)
            self.file_monitor.cancel()
            self.file_monitor = None

        if not self.current_file or not config.get("auto_reload", True):
            return

        gfile = Gio.File.new_for_path(str(self.current_file))
        self.file_monitor = gfile.monitor_file(Gio.FileMonitorFlags.NONE, None)
        
        self._reload_timer_id = None
        def on_changed(monitor, file, other_file, event_type):
            if event_type in (Gio.FileMonitorEvent.CHANGES_DONE_HINT, Gio.FileMonitorEvent.CHANGED):
                if self._reload_timer_id:
                    GLib.source_remove(self._reload_timer_id)
                self._reload_timer_id = GLib.timeout_add(300, self._do_auto_reload)

        self.monitor_handler_id = self.file_monitor.connect("changed", on_changed)

    def _do_auto_reload(self) -> bool:
        self._reload_timer_id = None
        self.reload_file()
        return False

    def on_js_message_received(self, manager: WebKit.UserContentManager, js_result: Any) -> None:
        """Receives events from the WebView JavaScript layer."""
        try:
            msg_str = js_result.to_string()
            data = json.loads(msg_str)
            msg_type = data.get("type")

            if msg_type == "outline":
                self.populate_outline(data.get("headings", []))
            elif msg_type == "active_heading":
                self.highlight_active_heading(data.get("id"))
            elif msg_type == "scroll_pos":
                self.current_scroll_y = float(data.get("pos", 0.0))
            elif msg_type == "open_external":
                url = data.get("url")
                if url:
                    Gio.AppInfo.launch_default_for_uri_async(url, None, None, None)
            elif msg_type == "toast":
                msg = data.get("message")
                if msg == "copied_code":
                    self.show_toast(t("toast_copied_code"))
        except Exception as e:
            print(f"Error handling JS message: {e}")

    def populate_outline(self, headings: List[Dict[str, Any]]) -> None:
        """Populates the outline sidebar listbox from detected headings."""
        self.headings = headings
        # Clear existing rows
        while True:
            row = self.outline_listbox.get_row_at_index(0)
            if not row:
                break
            self.outline_listbox.remove(row)

        if not headings:
            self.outline_scrolled.set_visible(False)
            self.outline_empty_box.set_visible(True)
            return

        self.outline_empty_box.set_visible(False)
        self.outline_scrolled.set_visible(True)

        for h in headings:
            row = Gtk.ListBoxRow()
            row.set_selectable(True)
            row.set_activatable(True)
            row.heading_id = h.get("id")

            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            level = h.get("level", 1)
            # Indent based on heading depth
            indent = max(0, (level - 1) * 14)
            box.set_margin_start(indent + 8)
            box.set_margin_end(8)
            box.set_margin_top(4)
            box.set_margin_bottom(4)

            # Prefix tag
            tag = Gtk.Label(label=f"H{level}")
            tag.add_css_class("dim-label")
            tag.add_css_class("caption")
            box.append(tag)

            label = Gtk.Label(label=h.get("text", ""))
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_halign(Gtk.Align.START)
            label.set_hexpand(True)
            if level == 1:
                label.add_css_class("heading")
            box.append(label)

            row.set_child(box)
            self.outline_listbox.append(row)

    def on_outline_row_activated(self, listbox: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        """Jumps to the heading in the document when an outline row is clicked."""
        if hasattr(row, "heading_id") and row.heading_id:
            script = f'window.scrollToHeading("{row.heading_id}");'
            self.webview.evaluate_javascript(script, -1, None, None, None, None)

    def highlight_active_heading(self, heading_id: Optional[str]) -> None:
        """Highlights the heading row in the outline corresponding to viewport position."""
        if not heading_id or heading_id == self.active_heading_id:
            return
        self.active_heading_id = heading_id

        idx = 0
        while True:
            row = self.outline_listbox.get_row_at_index(idx)
            if not row:
                break
            if hasattr(row, "heading_id") and row.heading_id == heading_id:
                self.outline_listbox.select_row(row)
                break
            idx += 1

    # --- Search Bar Handling ---
    def on_search_toggled(self, button: Gtk.ToggleButton) -> None:
        active = button.get_active()
        self.search_bar.set_search_mode(active)
        if active:
            self.search_entry.grab_focus()
        else:
            self.find_controller.search_finish()

    def on_search_bar_mode_changed(self, bar: Gtk.SearchBar, param: Any) -> None:
        if not bar.get_search_mode():
            self.btn_search.set_active(False)
            self.find_controller.search_finish()

    def on_search_text_changed(self, entry: Gtk.SearchEntry) -> None:
        text = entry.get_text()
        if not text:
            self.find_controller.search_finish()
            self.search_count_label.set_label("")
            return

        options = WebKit.FindOptions.CASE_INSENSITIVE | WebKit.FindOptions.WRAP_AROUND
        self.find_controller.search(text, options, 1000)
        self.find_controller.count_matches(text, options, 1000)

    def on_search_next_clicked(self, *args: Any) -> None:
        self.find_controller.search_next()

    def on_search_prev_clicked(self, *args: Any) -> None:
        self.find_controller.search_previous()

    def on_find_counted_matches(self, controller: WebKit.FindController, count: int) -> None:
        if count == 0:
            self.search_count_label.set_label(t("no_matches"))
        else:
            self.search_count_label.set_label(f"{count}")

    def on_find_failed(self, controller: WebKit.FindController) -> None:
        self.search_count_label.set_label(t("no_matches"))

    # --- Appearance Settings Handlers ---
    def set_color_scheme(self, scheme: str) -> None:
        config.set("color_scheme", scheme)
        self.apply_theme(scheme)
        if hasattr(self, "webview"):
            self.webview.evaluate_javascript(f'window.setAppTheme("{scheme}")', -1, None, None, None, None)

    def apply_theme(self, scheme: str) -> None:
        style_manager = Adw.StyleManager.get_default()
        if scheme == "light":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif scheme == "dark":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def set_font_family(self, font: str) -> None:
        config.set("font_family", font)
        if hasattr(self, "webview"):
            self.webview.evaluate_javascript(f'window.setAppFont("{font}")', -1, None, None, None, None)

    def set_reading_width(self, width: str) -> None:
        config.set("reading_width", width)
        if hasattr(self, "webview"):
            self.webview.evaluate_javascript(f'window.setAppWidth("{width}")', -1, None, None, None, None)

    def adjust_font_size(self, delta: int) -> None:
        cur_size = config.get("font_size", 16)
        new_size = max(12, min(28, cur_size + delta))
        config.set("font_size", new_size)
        if hasattr(self, "size_val_label"):
            self.size_val_label.set_label(f"{new_size}px")
        if hasattr(self, "webview"):
            self.webview.evaluate_javascript(f'window.setAppFontSize({new_size})', -1, None, None, None, None)

    def adjust_zoom(self, delta: float) -> None:
        cur = self.webview.get_zoom_level()
        new_zoom = max(0.5, min(2.5, cur + delta))
        self.webview.set_zoom_level(new_zoom)
        config.set("zoom_level", new_zoom)

    def reset_zoom(self) -> None:
        self.webview.set_zoom_level(1.0)
        config.set("zoom_level", 1.0)

    # --- Actions ---
    def copy_as_html(self) -> None:
        """Copies rendered document HTML to system clipboard."""
        if not self.current_content:
            return
        def on_eval(view, res):
            try:
                js_val = view.evaluate_javascript_finish(res)
                html_str = js_val.to_string()
                clip = Gdk.Display.get_default().get_clipboard()
                clip.set(html_str)
                self.show_toast(t("toast_copied_html"))
            except Exception as e:
                self.show_toast(str(e))

        self.webview.evaluate_javascript('document.getElementById("content").innerHTML', -1, None, None, None, on_eval)

    def copy_raw_markdown(self) -> None:
        """Copies raw markdown source to clipboard."""
        if self.current_content:
            clip = Gdk.Display.get_default().get_clipboard()
            clip.set(self.current_content)
            self.show_toast(t("toast_copied_raw"))

    def on_print_clicked(self, button: Optional[Gtk.Button]) -> None:
        """Prints or exports document to PDF."""
        print_op = WebKit.PrintOperation.new(self.webview)
        print_op.run_dialog(self)

    def on_open_in_editor(self, button: Optional[Gtk.Button]) -> None:
        """Opens current file in external editor."""
        if self.current_file and self.current_file.exists():
            uri = self.current_file.as_uri()
            try:
                Gio.AppInfo.launch_default_for_uri_async(uri, None, None, None)
            except Exception as e:
                self.show_toast(t("toast_external_editor_error", error=str(e)))

    def show_shortcuts_window(self) -> None:
        """Displays keyboard shortcuts dialog."""
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <object class="GtkShortcutsWindow" id="shortcuts_window">
    <property name="modal">True</property>
    <child>
      <object class="GtkShortcutsSection">
        <property name="visible">True</property>
        <child>
          <object class="GtkShortcutsGroup">
            <property name="title">Document</property>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">{t("open_file")}</property>
                <property name="accelerator">&lt;Control&gt;o</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">{t("reload")}</property>
                <property name="accelerator">&lt;Control&gt;r</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">{t("print_export_pdf")}</property>
                <property name="accelerator">&lt;Control&gt;p</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">{t("open_in_editor")}</property>
                <property name="accelerator">&lt;Control&gt;e</property>
              </object>
            </child>
          </object>
        </child>
        <child>
          <object class="GtkShortcutsGroup">
            <property name="title">Navigation &amp; View</property>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">{t("zen_mode")}</property>
                <property name="accelerator">F11</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">{t("toggle_sidebar")}</property>
                <property name="accelerator">F9</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">{t("search_tooltip")}</property>
                <property name="accelerator">&lt;Control&gt;f</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">{t("zoom_in")}</property>
                <property name="accelerator">&lt;Control&gt;plus</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">{t("zoom_out")}</property>
                <property name="accelerator">&lt;Control&gt;minus</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">{t("zoom_reset")}</property>
                <property name="accelerator">&lt;Control&gt;0</property>
              </object>
            </child>
          </object>
        </child>
      </object>
    </child>
  </object>
</interface>"""
        try:
            builder = Gtk.Builder.new_from_string(xml, -1)
            dialog = builder.get_object("shortcuts_window")
            dialog.set_transient_for(self)
            dialog.present()
        except Exception as e:
            print(f"Error opening shortcuts window: {e}")

    def show_about_dialog(self) -> None:
        """Displays About AuraMD dialog."""
        dialog = Adw.AboutDialog()
        dialog.set_application_name("AuraMD")
        dialog.set_application_icon("io.github.auramd.AuraMD")
        dialog.set_version("1.0.0")
        dialog.set_developer_name("AuraMD Team")
        dialog.set_comments(t("app_description"))
        dialog.set_website("https://github.com/auramd/auramd")
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.set_translator_credits("English & Español: Built-in")
        dialog.present(self)
