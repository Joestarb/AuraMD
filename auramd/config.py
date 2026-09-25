"""
Configuration manager for AuraMD.
Persists user preferences in ~/.config/auramd/settings.json.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

CONFIG_DIR = Path.home() / ".config" / "auramd"
CONFIG_FILE = CONFIG_DIR / "settings.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "language": "auto",  # 'auto', 'en', 'es'
    "color_scheme": "system",  # 'system', 'light', 'dark'
    "font_family": "sans",  # 'sans', 'serif', 'mono'
    "font_size": 16,  # 12 to 26 px
    "reading_width": "standard",  # 'compact' (680px), 'standard' (820px), 'wide' (1060px), 'full' (100%)
    "zoom_level": 1.0,
    "show_sidebar": True,
    "sidebar_width": 260,
    "auto_reload": True,
    "recent_files": [],
    "window_width": 1050,
    "window_height": 720,
    "window_maximized": False,
}

class ConfigManager:
    def __init__(self) -> None:
        self.config: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self.load()

    def load(self) -> None:
        if not CONFIG_FILE.exists():
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self.config.update(data)
        except Exception as e:
            print(f"Warning: Failed to load config from {CONFIG_FILE}: {e}")

    def save(self) -> None:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save config to {CONFIG_FILE}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save()

    def add_recent_file(self, filepath: str) -> None:
        """Add a file path to the recent files list (max 10 items, no duplicates)."""
        recent = self.config.get("recent_files", [])
        if not isinstance(recent, list):
            recent = []
        
        # Normalize and remove if exists
        abs_path = str(Path(filepath).resolve())
        if abs_path in recent:
            recent.remove(abs_path)
            
        recent.insert(0, abs_path)
        # Keep maximum 10
        self.config["recent_files"] = recent[:10]
        self.save()

    def clear_recent_files(self) -> None:
        self.config["recent_files"] = []
        self.save()

# Global singleton
config = ConfigManager()
