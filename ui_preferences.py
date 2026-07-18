"""Small, failure-tolerant persistence for user interface preferences."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

PREFERENCES_PATH = Path(__file__).resolve().with_name("ui_preferences.json")
PREFERENCES_SCHEMA = "cellular-automata-lab/ui-preferences"
PREFERENCES_VERSION = 1
MAX_RECENT_EXPERIMENTS = 5


@dataclass
class UIPreferences:
    """Failure-tolerant favorites, recents, and tutorial progress."""

    favorite_rules: set[int] = field(default_factory=set)
    recent_experiments: list[dict[str, str]] = field(default_factory=list)
    path: Path = PREFERENCES_PATH
    autosave: bool = True
    seen_tutorials: set[str] = field(default_factory=set)

    @classmethod
    def load(
        cls,
        path: Path = PREFERENCES_PATH,
        *,
        autosave: bool = True,
    ) -> "UIPreferences":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, Mapping):
                raise TypeError("preferences must be an object")
            if raw.get("schema") != PREFERENCES_SCHEMA:
                raise ValueError("unknown preferences schema")
            if raw.get("version") != PREFERENCES_VERSION:
                raise ValueError("unsupported preferences version")
            favorites_source = raw.get("favorite_rules", [])
            if not isinstance(favorites_source, list):
                raise TypeError("favorite_rules must be a list")
            favorites = {
                value
                for value in favorites_source
                if isinstance(value, int)
                and not isinstance(value, bool)
                and 0 <= value <= 255
            }
            recent_source = raw.get("recent_experiments", [])
            if not isinstance(recent_source, list):
                raise TypeError("recent_experiments must be a list")
            recent: list[dict[str, str]] = []
            for item in recent_source:
                if not isinstance(item, Mapping):
                    continue
                kind = item.get("kind")
                identifier = item.get("identifier")
                name = item.get("name")
                if (
                    kind in ("session", "profile")
                    and isinstance(identifier, str)
                    and identifier.strip()
                    and isinstance(name, str)
                    and name.strip()
                ):
                    recent.append(
                        {
                            "kind": kind,
                            "identifier": identifier.strip(),
                            "name": name.strip(),
                        }
                    )
            tutorials_source = raw.get("seen_tutorials", [])
            if not isinstance(tutorials_source, list):
                raise TypeError("seen_tutorials must be a list")
            tutorials = {
                value.strip()
                for value in tutorials_source
                if isinstance(value, str) and value.strip()
            }
            return cls(
                favorites,
                recent[:MAX_RECENT_EXPERIMENTS],
                path,
                autosave,
                tutorials,
            )
        except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError, ValueError):
            return cls(path=path, autosave=autosave)

    def save(self) -> None:
        if not self.autosave:
            return
        document: dict[str, Any] = {
            "schema": PREFERENCES_SCHEMA,
            "version": PREFERENCES_VERSION,
            "favorite_rules": sorted(self.favorite_rules),
            "recent_experiments": self.recent_experiments[:MAX_RECENT_EXPERIMENTS],
            "seen_tutorials": sorted(self.seen_tutorials),
        }
        temporary = self.path.with_suffix(".json.tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(
                json.dumps(document, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(self.path)
        except OSError:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def toggle_favorite_rule(self, rule: int) -> bool:
        if isinstance(rule, bool) or not isinstance(rule, int) or not 0 <= rule <= 255:
            raise ValueError("Favorite rule must be between 0 and 255.")
        if rule in self.favorite_rules:
            self.favorite_rules.remove(rule)
            selected = False
        else:
            self.favorite_rules.add(rule)
            selected = True
        self.save()
        return selected

    def record_recent(self, kind: str, identifier: str, name: str) -> None:
        if kind not in ("session", "profile"):
            raise ValueError("Recent experiment kind must be session or profile.")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("Recent experiment identifier cannot be empty.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Recent experiment name cannot be empty.")
        item = {
            "kind": kind,
            "identifier": identifier.strip(),
            "name": name.strip(),
        }
        self.recent_experiments = [
            existing
            for existing in self.recent_experiments
            if not (
                existing["kind"] == item["kind"]
                and existing["identifier"] == item["identifier"]
            )
        ]
        self.recent_experiments.insert(0, item)
        del self.recent_experiments[MAX_RECENT_EXPERIMENTS:]
        self.save()

    def recent(self) -> list[dict[str, str]]:
        return [dict(item) for item in self.recent_experiments]

    def has_seen_tutorial(self, tutorial: str) -> bool:
        """Return whether a named tutorial has already been presented."""
        return tutorial in self.seen_tutorials

    def mark_tutorial_seen(self, tutorial: str) -> None:
        """Persist first-run tutorial progress without failing the application."""
        if not isinstance(tutorial, str) or not tutorial.strip():
            raise ValueError("Tutorial identifier cannot be empty.")
        normalized = tutorial.strip()
        if normalized not in self.seen_tutorials:
            self.seen_tutorials.add(normalized)
            self.save()
