"""
Internationalization (i18n) module for AuraMD.
Supports English and Spanish with runtime language switching.
"""

import locale
import os
from typing import Dict, Any, Optional

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # App Info
        "app_name": "AuraMD",
        "app_title": "Aura Markdown",
        "app_subtitle": "Modern, Minimalist Markdown Reader",
        "app_description": "A modern, minimalist, and distraction-free Markdown reader for Linux.",
        
        # Header / Navigation
        "toggle_sidebar": "Toggle Outline & Stats (F9)",
        "open_file": "Open File (Ctrl+O)",
        "recent_files": "Recent Files",
        "no_recent_files": "No recent documents",
        "clear_recent": "Clear Recent History",
        "search_placeholder": "Find in document... (Ctrl+F)",
        "search_tooltip": "Search in document (Ctrl+F)",
        "zen_mode": "Distraction-Free Zen Mode (F11)",
        "exit_zen_mode": "Exit Zen Mode (Esc or F11)",
        "view_options": "Appearance & Typography",
        "main_menu": "Main Menu",
        
        # View Options Popover
        "theme": "Theme",
        "theme_system": "System",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "font_family": "Font Family",
        "font_sans": "Modern Sans",
        "font_serif": "Serif",
        "font_mono": "Monospace",
        "reading_width": "Reading Width",
        "width_compact": "Compact",
        "width_standard": "Standard",
        "width_wide": "Wide",
        "width_full": "Full",
        "font_size": "Text Size",
        "zoom_in": "Zoom In (Ctrl++)",
        "zoom_out": "Zoom Out (Ctrl+-)",
        "zoom_reset": "Reset Zoom (Ctrl+0)",
        
        # Main Menu Actions
        "reload": "Reload Document (F5)",
        "open_in_editor": "Open in External Editor (Ctrl+E)",
        "copy_html": "Copy as HTML (Ctrl+Shift+C)",
        "copy_raw": "Copy Raw Markdown",
        "print_export_pdf": "Print / Export to PDF (Ctrl+P)",
        "language": "Language",
        "language_en": "English",
        "language_es": "Español (Spanish)",
        "keyboard_shortcuts": "Keyboard Shortcuts (Ctrl+?)",
        "about_auramd": "About AuraMD",
        "quit": "Quit (Ctrl+Q)",
        
        # Sidebar Tabs & Content
        "tab_outline": "Outline",
        "tab_stats": "Statistics",
        "outline_desc": "Table of Contents",
        "stats_desc": "Document Metrics",
        "outline_empty": "No headings found in this document",
        "outline_empty_desc": "Headings (H1 to H6) from your document will appear here for fast navigation.",
        "stats_empty_desc": "Reading time, words, and character metrics will appear here once a document is open.",
        "stats_words": "Words",
        "stats_characters": "Characters",
        "stats_reading_time": "Reading Time",
        "stats_lines": "Lines",
        "stats_headings": "Headings",
        "min_read": "min read",
        "less_than_minute": "< 1 min read",
        
        # Search Bar
        "search_prev": "Previous Match (Ctrl+Shift+G)",
        "search_next": "Next Match (Ctrl+G)",
        "match_counter": "{current} of {total}",
        "no_matches": "No matches",
        
        # Empty State
        "empty_title": "Welcome to AuraMD",
        "empty_subtitle": "Open a Markdown file to start reading, or drag and drop a file anywhere into this window.",
        "btn_open_document": "Open Document",
        "btn_open_sample": "Try Sample Document",
        "quick_shortcuts": "Quick Shortcuts",
        "shortcut_open": "Ctrl+O — Open file",
        "shortcut_zen": "F11 — Zen reading mode",
        "shortcut_search": "Ctrl+F — Search in document",
        "shortcut_print": "Ctrl+P — Print / Export PDF",
        
        # Notifications / Toasts
        "toast_reloaded": "Document reloaded from disk",
        "toast_copied_html": "HTML copied to clipboard",
        "toast_copied_raw": "Raw markdown copied to clipboard",
        "toast_copied_code": "Code copied to clipboard",
        "toast_lang_changed": "Language switched to English",
        "toast_file_error": "Could not open file: {error}",
        "toast_external_editor_error": "Could not open external editor: {error}",
        
        # In-Document / Webview
        "js_copy_code": "Copy",
        "js_copied": "Copied!",
        
        # Dialogs
        "dialog_open_title": "Open Markdown File",
        "dialog_filter_md": "Markdown Files (*.md, *.markdown, *.mdown, *.mkd)",
        "dialog_filter_all": "All Files (*.*)",
    },
    
    "es": {
        # App Info
        "app_name": "AuraMD",
        "app_title": "Aura Markdown",
        "app_subtitle": "Lector de Markdown moderno y minimalista",
        "app_description": "Un lector de Markdown moderno, minimalista y libre de distracciones para Linux.",
        
        # Header / Navigation
        "toggle_sidebar": "Alternar Índice y Estadísticas (F9)",
        "open_file": "Abrir archivo (Ctrl+O)",
        "recent_files": "Archivos recientes",
        "no_recent_files": "No hay documentos recientes",
        "clear_recent": "Limpiar historial reciente",
        "search_placeholder": "Buscar en el documento... (Ctrl+F)",
        "search_tooltip": "Buscar en el documento (Ctrl+F)",
        "zen_mode": "Modo Zen / Sin distracciones (F11)",
        "exit_zen_mode": "Salir del Modo Zen (Esc o F11)",
        "view_options": "Apariencia y tipografía",
        "main_menu": "Menú principal",
        
        # View Options Popover
        "theme": "Tema",
        "theme_system": "Sistema",
        "theme_light": "Claro",
        "theme_dark": "Oscuro",
        "font_family": "Tipografía",
        "font_sans": "Sans moderno",
        "font_serif": "Serif",
        "font_mono": "Monoespaciado",
        "reading_width": "Ancho de lectura",
        "width_compact": "Compacto",
        "width_standard": "Estándar",
        "width_wide": "Ancho",
        "width_full": "Completo",
        "font_size": "Tamaño del texto",
        "zoom_in": "Acercar (Ctrl++)",
        "zoom_out": "Alejar (Ctrl+-)",
        "zoom_reset": "Restablecer zoom (Ctrl+0)",
        
        # Main Menu Actions
        "reload": "Recargar documento (F5)",
        "open_in_editor": "Abrir en editor externo (Ctrl+E)",
        "copy_html": "Copiar como HTML (Ctrl+Shift+C)",
        "copy_raw": "Copiar Markdown original",
        "print_export_pdf": "Imprimir / Exportar a PDF (Ctrl+P)",
        "language": "Idioma",
        "language_en": "English (Inglés)",
        "language_es": "Español",
        "keyboard_shortcuts": "Atajos de teclado (Ctrl+?)",
        "about_auramd": "Acerca de AuraMD",
        "quit": "Salir (Ctrl+Q)",
        
        # Sidebar Tabs & Content
        "tab_outline": "Índice",
        "tab_stats": "Estadísticas",
        "outline_desc": "Tabla de contenidos",
        "stats_desc": "Métricas del documento",
        "outline_empty": "No se encontraron encabezados",
        "outline_empty_desc": "Los encabezados (H1 a H6) de tu documento aparecerán aquí para saltar rápidamente a cualquier sección.",
        "stats_empty_desc": "El tiempo de lectura, palabras y métricas aparecerán aquí una vez que abras un documento.",
        "stats_words": "Palabras",
        "stats_characters": "Caracteres",
        "stats_reading_time": "Tiempo de lectura",
        "stats_lines": "Líneas",
        "stats_headings": "Encabezados",
        "min_read": "min de lectura",
        "less_than_minute": "< 1 min de lectura",
        
        # Search Bar
        "search_prev": "Coincidencia anterior (Ctrl+Shift+G)",
        "search_next": "Coincidencia siguiente (Ctrl+G)",
        "match_counter": "{current} de {total}",
        "no_matches": "Sin coincidencias",
        
        # Empty State
        "empty_title": "Bienvenido a AuraMD",
        "empty_subtitle": "Abre un archivo Markdown para comenzar a leer, o arrastra y suelta un archivo en cualquier lugar de esta ventana.",
        "btn_open_document": "Abrir documento",
        "btn_open_sample": "Probar documento de ejemplo",
        "quick_shortcuts": "Atajos rápidos",
        "shortcut_open": "Ctrl+O — Abrir archivo",
        "shortcut_zen": "F11 — Modo de lectura Zen",
        "shortcut_search": "Ctrl+F — Buscar en el documento",
        "shortcut_print": "Ctrl+P — Imprimir / Exportar PDF",
        
        # Notifications / Toasts
        "toast_reloaded": "Documento recargado desde el disco",
        "toast_copied_html": "HTML copiado al portapapeles",
        "toast_copied_raw": "Markdown copiado al portapapeles",
        "toast_copied_code": "Código copiado al portapapeles",
        "toast_lang_changed": "Idioma cambiado a español",
        "toast_file_error": "No se pudo abrir el archivo: {error}",
        "toast_external_editor_error": "No se pudo abrir el editor externo: {error}",
        
        # In-Document / Webview
        "js_copy_code": "Copiar",
        "js_copied": "¡Copiado!",
        
        # Dialogs
        "dialog_open_title": "Abrir archivo Markdown",
        "dialog_filter_md": "Archivos Markdown (*.md, *.markdown, *.mdown, *.mkd)",
        "dialog_filter_all": "Todos los archivos (*.*)",
    }
}

_current_language: str = "es"

def detect_system_language() -> str:
    """Detects system language preference (en or es)."""
    try:
        lang, _ = locale.getdefaultlocale()
        if lang and lang.lower().startswith("es"):
            return "es"
    except Exception:
        pass
    
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var, "")
        if val.lower().startswith("es"):
            return "es"
            
    return "en"

def set_language(lang_code: str) -> None:
    """Sets current language code ('en' or 'es' or 'auto')."""
    global _current_language
    if lang_code == "auto":
        _current_language = detect_system_language()
    elif lang_code in TRANSLATIONS:
        _current_language = lang_code
    else:
        _current_language = "es"

def get_current_language() -> str:
    """Returns current active language code."""
    return _current_language

def t(key: str, **kwargs: Any) -> str:
    """
    Translates a key into current language with optional format kwargs.
    Falls back to English if translation is missing.
    """
    lang_dict = TRANSLATIONS.get(_current_language, TRANSLATIONS["en"])
    text = lang_dict.get(key)
    if text is None:
        text = TRANSLATIONS["en"].get(key, key)
    
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
