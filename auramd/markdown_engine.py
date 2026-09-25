"""
Markdown rendering engine and HTML generation for AuraMD.
Generates self-contained, responsive, and beautifully styled HTML
using bundled Marked.js, Highlight.js, KaTeX, and Mermaid.js.
"""

from pathlib import Path
import json
import re
from typing import Dict, Any
from auramd.i18n import t

ASSETS_DIR = Path(__file__).parent / "assets"
VENDOR_DIR = ASSETS_DIR / "vendor"
TEMPLATE_PATH = ASSETS_DIR / "template.html"

_TEMPLATE_CACHE: str = ""

def get_template_content() -> str:
    """Loads and caches the HTML viewer template."""
    global _TEMPLATE_CACHE
    if not _TEMPLATE_CACHE:
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            _TEMPLATE_CACHE = f.read()
    return _TEMPLATE_CACHE

def calculate_reading_stats(markdown_text: str) -> Dict[str, Any]:
    """Calculates statistics: words, characters, lines, headings, reading time."""
    lines = markdown_text.splitlines()
    line_count = len(lines)
    char_count = len(markdown_text)
    
    # Strip markdown formatting for accurate word count
    clean_text = re.sub(r'```[\s\S]*?```', '', markdown_text)
    clean_text = re.sub(r'#+\s*', '', clean_text)
    clean_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_text)
    clean_text = re.sub(r'[*_~`>|-]', ' ', clean_text)
    words = re.findall(r'\b\w+\b', clean_text)
    word_count = len(words)
    
    # Average adult reading speed: 200 words per minute
    reading_time_mins = max(1, round(word_count / 200)) if word_count >= 100 else 0
    
    # Count headings
    headings = re.findall(r'^(#{1,6})\s+(.+)$', markdown_text, re.MULTILINE)
    heading_count = len(headings)
    
    return {
        "words": word_count,
        "characters": char_count,
        "lines": line_count,
        "headings": heading_count,
        "reading_time_mins": reading_time_mins,
    }

def get_base_html(
    markdown_content: str,
    file_dir: str,
    theme: str = "system",
    font_family: str = "sans",
    font_size: int = 16,
    reading_width: str = "standard",
    preserve_scroll: float = 0.0,
    lang: str = "es"
) -> str:
    """Generates the full HTML page with the rendered Markdown and interactive features."""
    vendor_uri = VENDOR_DIR.as_uri()
    template = get_template_content()
    
    # Escape markdown content safely as JSON string for JS
    json_escaped_md = json.dumps(markdown_content)
    
    replacements = {
        "{{LANG}}": lang,
        "{{THEME}}": theme,
        "{{FONT_FAMILY}}": font_family,
        "{{READING_WIDTH}}": reading_width,
        "{{FONT_SIZE}}": str(font_size),
        "{{VENDOR_URI}}": vendor_uri,
        "{{RAW_MD_JSON}}": json_escaped_md,
        "{{COPY_LABEL}}": t("js_copy_code"),
        "{{COPIED_LABEL}}": t("js_copied"),
        "{{PRESERVE_SCROLL}}": str(preserve_scroll),
    }

    result = template
    for key, val in replacements.items():
        result = result.replace(key, val)

    return result
