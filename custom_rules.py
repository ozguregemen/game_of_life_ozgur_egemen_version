"""Safe, dimension-aware custom cellular-automaton rule definitions."""

from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
import warnings
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from app_metadata import APP_VERSION
from app_paths import APPLICATION_PATHS
from one_dimensional_ca import RuleSpec
from three_dimensional_ca import MOORE_NEIGHBORHOOD, VON_NEUMANN_NEIGHBORHOOD
from three_dimensional_generations import GenerationsRule3D
from three_dimensional_rules import LifeLikeRule3D

CUSTOM_RULE_SCHEMA = "cellular-automata-lab-custom-rule"
CUSTOM_RULE_VERSION = 1
CUSTOM_RULE_DIRECTORY = APPLICATION_PATHS.rules
CUSTOM_RULE_PACKAGE_SCHEMA = "cellular-automata-lab-rule-package"
CUSTOM_RULE_PACKAGE_VERSION = 1
CUSTOM_RULE_PACKAGE_DIRECTORY = APPLICATION_PATHS.rule_packages
CUSTOM_RULE_DIMENSIONS = ("1d", "2d", "3d")

KIND_ONE_DIMENSIONAL = "one_dimensional"
KIND_LIFE_LIKE = "life_like"
KIND_GENERATIONS = "generations"
CUSTOM_RULE_KINDS = (
    KIND_ONE_DIMENSIONAL,
    KIND_LIFE_LIKE,
    KIND_GENERATIONS,
)

NEIGHBORHOOD_MOORE = "moore"
NEIGHBORHOOD_FACE = "face"
NEIGHBORHOODS_3D = MappingProxyType(
    {
        NEIGHBORHOOD_MOORE: MOORE_NEIGHBORHOOD,
        NEIGHBORHOOD_FACE: VON_NEUMANN_NEIGHBORHOOD,
    }
)

MAX_CUSTOM_RULE_NAME = 80
MAX_CUSTOM_RULE_DESCRIPTION = 500
MAX_CUSTOM_RULE_FILES = 500
MAX_CUSTOM_RULE_BYTES = 64 * 1024
MAX_CUSTOM_RULE_PACKAGES = 500

_INVALID_FILENAME_CHARACTERS = re.compile(r'[\\/:*?"<>|]+')
_WHITESPACE = re.compile(r"\s+")
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def safe_custom_rule_filename(name: str) -> str:
    """Return a portable, traversal-safe filename stem."""

    if not isinstance(name, str):
        raise TypeError("Custom rule name must be text.")
    normalized = unicodedata.normalize("NFKC", name).strip()
    if not normalized:
        raise ValueError("Custom rule name cannot be empty.")
    if len(normalized) > MAX_CUSTOM_RULE_NAME:
        raise ValueError(
            f"Custom rule name cannot exceed {MAX_CUSTOM_RULE_NAME} characters."
        )
    stem = _INVALID_FILENAME_CHARACTERS.sub("_", normalized).replace("..", "_")
    stem = _WHITESPACE.sub("_", stem).strip(" ._")
    if not stem:
        raise ValueError("Custom rule name has no valid filename characters.")
    if stem.upper() in _WINDOWS_RESERVED_NAMES:
        stem = f"_{stem}"
    return stem.casefold()


def _count_expression(values: tuple[int, ...]) -> str:
    """Format counts without making values above nine ambiguous."""

    if not values:
        return ""
    if max(values) <= 9:
        return "".join(str(value) for value in values)
    return ",".join(str(value) for value in values)


def parse_neighbor_counts(expression: str, maximum: int) -> tuple[int, ...]:
    """Parse compact digits or comma-separated integers/ranges."""

    if not isinstance(expression, str):
        raise TypeError("Neighbor counts must be text.")
    text = expression.strip()
    if not text or text == "-":
        return ()
    values: set[int] = set()
    if re.fullmatch(r"\d+", text) and "," not in text and "-" not in text:
        compact_value = int(text)
        if compact_value <= maximum and len(text) > 1:
            values.add(compact_value)
        else:
            values.update(int(character) for character in text)
    else:
        for token in text.split(","):
            item = token.strip()
            if not item:
                raise ValueError("Neighbor count lists cannot contain empty items.")
            if "-" in item:
                bounds = item.split("-")
                if len(bounds) != 2 or not all(bound.isdigit() for bound in bounds):
                    raise ValueError(f"Invalid neighbor range: {item!r}.")
                start, end = (int(bound) for bound in bounds)
                if start > end:
                    raise ValueError(f"Neighbor range starts after it ends: {item!r}.")
                values.update(range(start, end + 1))
            elif item.isdigit():
                values.add(int(item))
            else:
                raise ValueError(f"Invalid neighbor count: {item!r}.")
    normalized = tuple(sorted(values))
    if any(value < 0 or value > maximum for value in normalized):
        raise ValueError(f"Neighbor counts must be between 0 and {maximum}.")
    return normalized


def parse_life_like_notation(
    notation: str,
    *,
    maximum: int,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Parse B.../S... notation and return birth, survival counts."""

    if not isinstance(notation, str):
        raise TypeError("Life-like notation must be text.")
    match = re.fullmatch(
        r"\s*B([^/]*)/S([^/]*)\s*",
        notation,
        flags=re.IGNORECASE,
    )
    if match is None:
        raise ValueError("Use Life-like notation such as B3/S23.")
    return (
        parse_neighbor_counts(match.group(1), maximum),
        parse_neighbor_counts(match.group(2), maximum),
    )


def parse_generations_notation(
    notation: str,
) -> tuple[tuple[int, ...], tuple[int, ...], int, str]:
    """Parse S/B/C/M-or-N Generations notation."""

    if not isinstance(notation, str):
        raise TypeError("Generations notation must be text.")
    parts = tuple(part.strip() for part in notation.split("/"))
    if len(parts) != 4:
        raise ValueError("Use Generations notation such as 4/4/5/M.")
    neighborhood_key = {
        "M": NEIGHBORHOOD_MOORE,
        "N": NEIGHBORHOOD_FACE,
    }.get(parts[3].upper())
    if neighborhood_key is None:
        raise ValueError("Generations neighborhood must be M (26) or N (6).")
    if not parts[2].isdigit():
        raise ValueError("Generations state count must be an integer.")
    state_count = int(parts[2])
    if not 2 <= state_count <= 256:
        raise ValueError("Generations state count must be between 2 and 256.")
    maximum = NEIGHBORHOODS_3D[neighborhood_key].size
    survival = parse_neighbor_counts(parts[0], maximum)
    birth = parse_neighbor_counts(parts[1], maximum)
    return survival, birth, state_count, neighborhood_key


@dataclass(frozen=True)
class CustomRuleDefinition:
    """Validated custom rule recipe for exactly one dimensional workspace."""

    key: str
    name: str
    dimension: str
    kind: str
    parameters: Mapping[str, Any]
    description: str = ""

    def __post_init__(self) -> None:
        if self.dimension not in CUSTOM_RULE_DIMENSIONS:
            raise ValueError(f"Unknown custom-rule dimension: {self.dimension!r}.")
        if self.kind not in CUSTOM_RULE_KINDS:
            raise ValueError(f"Unknown custom-rule kind: {self.kind!r}.")
        name = self.name.strip()
        safe_custom_rule_filename(name)
        expected_key = f"custom:{self.dimension}:{safe_custom_rule_filename(name)}"
        if self.key != expected_key:
            raise ValueError("Custom rule key must match its dimension and safe name.")
        if not isinstance(self.description, str):
            raise TypeError("Custom rule description must be text.")
        description = self.description.strip()
        if len(description) > MAX_CUSTOM_RULE_DESCRIPTION:
            raise ValueError("Custom rule description is too long.")
        if not isinstance(self.parameters, Mapping):
            raise TypeError("Custom rule parameters must be an object.")
        normalized = self._validate_parameters(dict(self.parameters))
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "parameters", MappingProxyType(normalized))

    def _validate_parameters(self, value: dict[str, Any]) -> dict[str, Any]:
        if self.dimension == "1d":
            if self.kind != KIND_ONE_DIMENSIONAL:
                raise ValueError("1D custom rules must use one_dimensional kind.")
            spec = RuleSpec.from_mapping(value)
            return spec.as_dict()
        if self.dimension == "2d":
            if self.kind != KIND_LIFE_LIKE:
                raise ValueError("2D custom rules currently support Life-like rules.")
            return {
                "birth": list(_validated_counts(value.get("birth"), 8, "birth")),
                "survival": list(
                    _validated_counts(value.get("survival"), 8, "survival")
                ),
            }
        if self.kind not in (KIND_LIFE_LIKE, KIND_GENERATIONS):
            raise ValueError("3D custom rules must be Life-like or Generations.")
        neighborhood_key = value.get("neighborhood")
        if not isinstance(neighborhood_key, str) or neighborhood_key not in NEIGHBORHOODS_3D:
            raise ValueError("3D custom-rule neighborhood must be moore or face.")
        maximum = NEIGHBORHOODS_3D[neighborhood_key].size
        normalized: dict[str, Any] = {
            "birth": list(_validated_counts(value.get("birth"), maximum, "birth")),
            "survival": list(
                _validated_counts(value.get("survival"), maximum, "survival")
            ),
            "neighborhood": neighborhood_key,
        }
        if self.kind == KIND_GENERATIONS:
            state_count = value.get("state_count")
            if (
                isinstance(state_count, bool)
                or not isinstance(state_count, int)
                or not 2 <= state_count <= 256
            ):
                raise ValueError("3D Generations state_count must be between 2 and 256.")
            seed_density = value.get("seed_density", 0.20)
            if isinstance(seed_density, bool) or not isinstance(seed_density, (int, float)):
                raise TypeError("3D Generations seed_density must be numeric.")
            if not 0.01 <= float(seed_density) <= 0.99:
                raise ValueError("3D Generations seed_density must be between 0.01 and 0.99.")
            normalized["state_count"] = state_count
            normalized["seed_density"] = float(seed_density)
        return normalized

    @property
    def notation(self) -> str:
        if self.dimension == "1d":
            spec = self.one_dimensional_spec()
            return f"{spec.definition.name} · code {spec.code} · k={spec.states} · r={spec.radius}"
        birth = tuple(self.parameters["birth"])
        survival = tuple(self.parameters["survival"])
        if self.kind == KIND_LIFE_LIKE:
            return f"B{_count_expression(birth)}/S{_count_expression(survival)}"
        neighborhood = "M" if self.parameters["neighborhood"] == NEIGHBORHOOD_MOORE else "N"
        return (
            f"{_count_expression(survival)}/{_count_expression(birth)}/"
            f"{self.parameters['state_count']}/{neighborhood}"
        )

    @property
    def summary(self) -> str:
        label = {
            KIND_ONE_DIMENSIONAL: "1D rule recipe",
            KIND_LIFE_LIKE: "Life-like birth/survival rule",
            KIND_GENERATIONS: "3D Generations rule",
        }[self.kind]
        return f"{label} · {self.notation}"

    def one_dimensional_spec(self) -> RuleSpec:
        if self.dimension != "1d":
            raise ValueError("This custom rule does not belong to the 1D workspace.")
        return RuleSpec.from_mapping(self.parameters)

    def life_like_2d(self) -> dict[str, Any]:
        if self.dimension != "2d":
            raise ValueError("This custom rule does not belong to the 2D workspace.")
        return {
            "name": self.name,
            "birth": list(self.parameters["birth"]),
            "survival": list(self.parameters["survival"]),
        }

    def three_dimensional_rule(self) -> LifeLikeRule3D | GenerationsRule3D:
        if self.dimension != "3d":
            raise ValueError("This custom rule does not belong to the 3D workspace.")
        neighborhood = NEIGHBORHOODS_3D[str(self.parameters["neighborhood"])]
        if self.kind == KIND_LIFE_LIKE:
            return LifeLikeRule3D(
                key=self.key,
                name=self.name,
                birth=tuple(self.parameters["birth"]),
                survival=tuple(self.parameters["survival"]),
                neighborhood=neighborhood,
                description=self.description or "User-defined 3D Life-like rule.",
            )
        return GenerationsRule3D(
            key=self.key,
            name=self.name,
            survival=tuple(self.parameters["survival"]),
            birth=tuple(self.parameters["birth"]),
            state_count=int(self.parameters["state_count"]),
            neighborhood=neighborhood,
            description=self.description or "User-defined 3D Generations rule.",
            seed_density=float(self.parameters["seed_density"]),
        )

    def as_document(self) -> dict[str, Any]:
        return {
            "schema": CUSTOM_RULE_SCHEMA,
            "version": CUSTOM_RULE_VERSION,
            "name": self.name,
            "dimension": self.dimension,
            "kind": self.kind,
            "parameters": dict(self.parameters),
            "description": self.description,
        }


@dataclass(frozen=True)
class CustomRulePackage:
    """One validated, shareable custom-rule document on disk."""

    path: Path
    rule: CustomRuleDefinition
    exported_at: str
    application_version: str

    @property
    def source_name(self) -> str:
        return self.path.name


def _validated_counts(value: Any, maximum: int, label: str) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"Custom rule {label} counts must be a list.")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise TypeError(f"Custom rule {label} counts must be integers.")
    normalized = tuple(sorted(set(value)))
    if any(item < 0 or item > maximum for item in normalized):
        raise ValueError(f"Custom rule {label} counts must be between 0 and {maximum}.")
    return normalized


def custom_rule_from_1d(name: str, spec: RuleSpec) -> CustomRuleDefinition:
    return CustomRuleDefinition(
        key=f"custom:1d:{safe_custom_rule_filename(name)}",
        name=name,
        dimension="1d",
        kind=KIND_ONE_DIMENSIONAL,
        parameters=spec.as_dict(),
        description="Named 1D experiment rule created in Custom Rule Studio.",
    )


def custom_rule_from_2d(
    name: str,
    notation: str,
) -> CustomRuleDefinition:
    birth, survival = parse_life_like_notation(notation, maximum=8)
    return CustomRuleDefinition(
        key=f"custom:2d:{safe_custom_rule_filename(name)}",
        name=name,
        dimension="2d",
        kind=KIND_LIFE_LIKE,
        parameters={"birth": birth, "survival": survival},
        description="User-defined two-dimensional Life-like rule.",
    )


def custom_rule_from_3d_life(
    name: str,
    notation: str,
    *,
    neighborhood: str = NEIGHBORHOOD_MOORE,
) -> CustomRuleDefinition:
    if neighborhood not in NEIGHBORHOODS_3D:
        raise ValueError("Unknown 3D neighborhood.")
    birth, survival = parse_life_like_notation(
        notation,
        maximum=NEIGHBORHOODS_3D[neighborhood].size,
    )
    return CustomRuleDefinition(
        key=f"custom:3d:{safe_custom_rule_filename(name)}",
        name=name,
        dimension="3d",
        kind=KIND_LIFE_LIKE,
        parameters={
            "birth": birth,
            "survival": survival,
            "neighborhood": neighborhood,
        },
        description="User-defined three-dimensional Life-like rule.",
    )


def custom_rule_from_3d_generations(
    name: str,
    notation: str,
) -> CustomRuleDefinition:
    survival, birth, state_count, neighborhood = parse_generations_notation(notation)
    return CustomRuleDefinition(
        key=f"custom:3d:{safe_custom_rule_filename(name)}",
        name=name,
        dimension="3d",
        kind=KIND_GENERATIONS,
        parameters={
            "birth": birth,
            "survival": survival,
            "state_count": state_count,
            "neighborhood": neighborhood,
            "seed_density": 0.20,
        },
        description="User-defined three-dimensional Generations rule.",
    )


def custom_rule_from_document(value: Any) -> CustomRuleDefinition:
    if not isinstance(value, Mapping):
        raise TypeError("Custom rule JSON must contain an object.")
    version = value["version"]
    if (
        value["schema"] != CUSTOM_RULE_SCHEMA
        or isinstance(version, bool)
        or not isinstance(version, int)
        or version != CUSTOM_RULE_VERSION
    ):
        raise ValueError("Unsupported custom rule schema or version.")
    name = value["name"]
    dimension = value["dimension"]
    kind = value["kind"]
    parameters = value["parameters"]
    description = value.get("description", "")
    if not isinstance(name, str) or not isinstance(dimension, str) or not isinstance(kind, str):
        raise TypeError("Custom rule identity fields must be text.")
    return CustomRuleDefinition(
        key=f"custom:{dimension}:{safe_custom_rule_filename(name)}",
        name=name,
        dimension=dimension,
        kind=kind,
        parameters=parameters,
        description=description,
    )


def _read_json_document(path: Path) -> Any:
    """Read one size-limited UTF-8 JSON document."""

    if path.stat().st_size > MAX_CUSTOM_RULE_BYTES:
        raise ValueError("Custom rule file is too large.")
    with path.open("r", encoding="utf-8") as rule_file:
        return json.load(rule_file)


def custom_rule_package_from_document(
    value: Any,
    *,
    path: Path,
) -> CustomRulePackage:
    """Validate a standalone package envelope and its embedded rule."""

    if not isinstance(value, Mapping):
        raise TypeError("Custom rule package JSON must contain an object.")
    version = value["version"]
    if (
        value["schema"] != CUSTOM_RULE_PACKAGE_SCHEMA
        or isinstance(version, bool)
        or not isinstance(version, int)
        or version != CUSTOM_RULE_PACKAGE_VERSION
    ):
        raise ValueError("Unsupported custom rule package schema or version.")
    exported_at = value["exported_at"]
    application_version = value["application_version"]
    if not isinstance(exported_at, str) or not exported_at.strip():
        raise TypeError("Custom rule package exported_at must be text.")
    if not isinstance(application_version, str) or not application_version.strip():
        raise TypeError("Custom rule package application_version must be text.")
    rule = custom_rule_from_document(value["rule"])
    return CustomRulePackage(
        path=Path(path),
        rule=rule,
        exported_at=exported_at.strip(),
        application_version=application_version.strip(),
    )


def read_custom_rule_package(path: Path) -> CustomRulePackage:
    """Read and validate one standalone rule package without mutating the catalog."""

    source = Path(path)
    return custom_rule_package_from_document(
        _read_json_document(source),
        path=source,
    )


_CUSTOM_RULE_CACHE: dict[str, CustomRuleDefinition] = {}
_CUSTOM_RULE_PACKAGE_CACHE: tuple[CustomRulePackage, ...] = ()


def refresh_custom_rule_cache() -> None:
    """Refresh custom rules only at startup and after save/delete mutations."""

    refreshed: dict[str, CustomRuleDefinition] = {}
    for dimension in CUSTOM_RULE_DIMENSIONS:
        directory = CUSTOM_RULE_DIRECTORY / dimension
        if not directory.is_dir():
            continue
        for index, path in enumerate(sorted(directory.glob("*.json"))):
            if index >= MAX_CUSTOM_RULE_FILES:
                warnings.warn(
                    f"Skipping excess custom rule files in '{dimension}'."
                )
                break
            try:
                rule = custom_rule_from_document(_read_json_document(path))
                if rule.dimension != dimension:
                    raise ValueError("Custom rule directory does not match its dimension.")
                if rule.key in refreshed:
                    raise ValueError("Duplicate custom rule key.")
                refreshed[rule.key] = rule
            except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as exc:
                warnings.warn(f"Skipping invalid custom rule file '{path.name}': {exc}")
    _CUSTOM_RULE_CACHE.clear()
    _CUSTOM_RULE_CACHE.update(refreshed)


def refresh_custom_rule_package_cache() -> None:
    """Refresh shareable packages when Studio opens or a package changes."""

    global _CUSTOM_RULE_PACKAGE_CACHE
    refreshed: list[CustomRulePackage] = []
    directory = CUSTOM_RULE_PACKAGE_DIRECTORY
    if directory.is_dir():
        for index, path in enumerate(sorted(directory.glob("*.rule.json"))):
            if index >= MAX_CUSTOM_RULE_PACKAGES:
                warnings.warn("Skipping excess custom rule packages.")
                break
            try:
                refreshed.append(read_custom_rule_package(path))
            except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as exc:
                warnings.warn(f"Skipping invalid custom rule package '{path.name}': {exc}")
    _CUSTOM_RULE_PACKAGE_CACHE = tuple(
        sorted(
            refreshed,
            key=lambda package: (
                package.rule.name.casefold(),
                package.source_name.casefold(),
            ),
        )
    )


def get_custom_rule_packages(
    dimension: str | None = None,
) -> tuple[CustomRulePackage, ...]:
    """Return cached shareable packages, optionally filtered by dimension."""

    if dimension is not None and dimension not in CUSTOM_RULE_DIMENSIONS:
        raise ValueError(f"Unknown custom-rule dimension: {dimension!r}.")
    return tuple(
        package
        for package in _CUSTOM_RULE_PACKAGE_CACHE
        if dimension is None or package.rule.dimension == dimension
    )


def _unique_package_path(rule: CustomRuleDefinition) -> Path:
    stem = f"{safe_custom_rule_filename(rule.name)}-{rule.dimension}"
    candidate = CUSTOM_RULE_PACKAGE_DIRECTORY / f"{stem}.rule.json"
    counter = 2
    while candidate.exists():
        candidate = CUSTOM_RULE_PACKAGE_DIRECTORY / f"{stem}-{counter}.rule.json"
        counter += 1
    return candidate


def export_custom_rule_package(rule: CustomRuleDefinition) -> Path:
    """Atomically export a validated rule to a versioned standalone package."""

    validated = custom_rule_from_document(rule.as_document())
    CUSTOM_RULE_PACKAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    path = _unique_package_path(validated)
    temporary = path.with_suffix(path.suffix + ".tmp")
    document = {
        "schema": CUSTOM_RULE_PACKAGE_SCHEMA,
        "version": CUSTOM_RULE_PACKAGE_VERSION,
        "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "application_version": APP_VERSION,
        "rule": validated.as_document(),
    }
    try:
        with temporary.open("x", encoding="utf-8") as package_file:
            json.dump(document, package_file, ensure_ascii=False, indent=2)
            package_file.flush()
        temporary.replace(path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    refresh_custom_rule_package_cache()
    return path


def import_custom_rule_package(package: CustomRulePackage) -> CustomRuleDefinition:
    """Revalidate a package from disk and add it without silent overwrite."""

    current = read_custom_rule_package(package.path)
    saved = save_custom_rule(current.rule)
    refresh_custom_rule_package_cache()
    return saved


def get_custom_rules(
    dimension: str | None = None,
    *,
    kind: str | None = None,
) -> tuple[CustomRuleDefinition, ...]:
    if dimension is not None and dimension not in CUSTOM_RULE_DIMENSIONS:
        raise ValueError(f"Unknown custom-rule dimension: {dimension!r}.")
    if kind is not None and kind not in CUSTOM_RULE_KINDS:
        raise ValueError(f"Unknown custom-rule kind: {kind!r}.")
    rules = tuple(
        rule
        for rule in _CUSTOM_RULE_CACHE.values()
        if (dimension is None or rule.dimension == dimension)
        and (kind is None or rule.kind == kind)
    )
    return tuple(sorted(rules, key=lambda rule: (rule.name.casefold(), rule.key)))


def get_custom_rule(key: str) -> CustomRuleDefinition | None:
    return _CUSTOM_RULE_CACHE.get(key)


def save_custom_rule(
    rule: CustomRuleDefinition,
    *,
    overwrite: bool = False,
) -> CustomRuleDefinition:
    """Atomically save one validated custom rule and refresh the cache."""

    validated = custom_rule_from_document(rule.as_document())
    directory = CUSTOM_RULE_DIRECTORY / validated.dimension
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{safe_custom_rule_filename(validated.name)}.json"
    temporary = path.with_suffix(".tmp")
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"A {validated.dimension.upper()} rule named '{validated.name}' already exists."
        )
    document = validated.as_document()
    document["saved_at"] = dt.datetime.now(dt.timezone.utc).isoformat(
        timespec="seconds"
    )
    try:
        with temporary.open("w", encoding="utf-8") as rule_file:
            json.dump(document, rule_file, ensure_ascii=False, indent=2)
            rule_file.flush()
        temporary.replace(path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    refresh_custom_rule_cache()
    return _CUSTOM_RULE_CACHE[validated.key]


def delete_custom_rule(key: str) -> bool:
    """Delete one custom rule file and refresh the shared cache."""

    rule = _CUSTOM_RULE_CACHE.get(key)
    if rule is None:
        return False
    path = (
        CUSTOM_RULE_DIRECTORY
        / rule.dimension
        / f"{safe_custom_rule_filename(rule.name)}.json"
    )
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    refresh_custom_rule_cache()
    return True


refresh_custom_rule_cache()
refresh_custom_rule_package_cache()
