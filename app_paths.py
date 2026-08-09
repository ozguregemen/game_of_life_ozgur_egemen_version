"""Cross-platform locations and conservative migration for user-owned data."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from app_metadata import APP_SLUG

DATA_HOME_ENVIRONMENT = "CELLULAR_AUTOMATA_LAB_HOME"


@dataclass(frozen=True)
class ApplicationPaths:
    """Resolved directories used by persistent application features."""

    data: Path
    config: Path

    @property
    def sessions(self) -> Path:
        return self.data / "sessions"

    @property
    def profiles(self) -> Path:
        return self.sessions / "eca_profiles"

    @property
    def patterns(self) -> Path:
        return self.data / "patterns"

    @property
    def rules(self) -> Path:
        return self.data / "rules"

    @property
    def rule_packages(self) -> Path:
        """User-visible exchange folder for standalone custom-rule files."""

        return self.data / "rule_packages"

    @property
    def exports(self) -> Path:
        return self.data / "exports"

    @property
    def preferences(self) -> Path:
        return self.config / "ui_preferences.json"


def resolve_application_paths(
    environment: Mapping[str, str] | None = None,
    *,
    platform: str | None = None,
    home: Path | None = None,
) -> ApplicationPaths:
    """Return OS-native paths, with one portable/test override."""
    env = os.environ if environment is None else environment
    override = env.get(DATA_HOME_ENVIRONMENT, "").strip()
    if override:
        root = Path(override).expanduser()
        return ApplicationPaths(root, root / "config")

    platform_name = sys.platform if platform is None else platform
    user_home = Path.home() if home is None else Path(home)
    if platform_name == "win32":
        data_base = Path(env.get("LOCALAPPDATA", user_home / "AppData" / "Local"))
        config_base = Path(env.get("APPDATA", user_home / "AppData" / "Roaming"))
    elif platform_name == "darwin":
        data_base = user_home / "Library" / "Application Support"
        config_base = data_base
    else:
        data_base = Path(env.get("XDG_DATA_HOME", user_home / ".local" / "share"))
        config_base = Path(env.get("XDG_CONFIG_HOME", user_home / ".config"))
    return ApplicationPaths(data_base / APP_SLUG, config_base / APP_SLUG)


APPLICATION_PATHS = resolve_application_paths()
SOURCE_DIRECTORY = Path(__file__).resolve().parent
LEGACY_SESSION_DIRECTORY = SOURCE_DIRECTORY / "sessions"
LEGACY_PROFILE_DIRECTORY = LEGACY_SESSION_DIRECTORY / "eca_profiles"
LEGACY_PATTERN_DIRECTORY = SOURCE_DIRECTORY / "patterns"
LEGACY_PREFERENCES_PATH = SOURCE_DIRECTORY / "ui_preferences.json"


def _copy_missing_json_files(source: Path, target: Path) -> int:
    if not source.is_dir():
        return 0
    copied = 0
    target.mkdir(parents=True, exist_ok=True)
    for source_path in source.glob("*.json"):
        target_path = target / source_path.name
        if target_path.exists():
            continue
        shutil.copy2(source_path, target_path)
        copied += 1
    return copied


def migrate_legacy_user_data() -> dict[str, int]:
    """Copy source-adjacent user files once, never replacing newer files.

    Migration is deliberately best-effort. A read-only installation must still
    launch even when its old data cannot be copied.
    """
    result = {"sessions": 0, "profiles": 0, "patterns": 0, "preferences": 0}
    try:
        result["sessions"] = _copy_missing_json_files(
            LEGACY_SESSION_DIRECTORY,
            APPLICATION_PATHS.sessions,
        )
        result["profiles"] = _copy_missing_json_files(
            LEGACY_PROFILE_DIRECTORY,
            APPLICATION_PATHS.profiles,
        )
        result["patterns"] = _copy_missing_json_files(
            LEGACY_PATTERN_DIRECTORY,
            APPLICATION_PATHS.patterns,
        )
        if LEGACY_PREFERENCES_PATH.is_file() and not APPLICATION_PATHS.preferences.exists():
            APPLICATION_PATHS.preferences.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LEGACY_PREFERENCES_PATH, APPLICATION_PATHS.preferences)
            result["preferences"] = 1
    except OSError:
        # Persistence errors are reported by the feature that performs a save;
        # migration itself must never stop the application from opening.
        pass
    return result
