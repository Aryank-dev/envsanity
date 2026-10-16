"""Extract environment variable usages from source files (text based)."""

from __future__ import annotations

from dataclasses import dataclass

from . import patterns

IGNORE_MARKER = "envsanity-ignore"


@dataclass
class Usage:
    """A single environment variable usage at a location."""

    name: str
    file: str
    line: int


@dataclass
class DynamicLookup:
    """A lookup whose variable name cannot be determined statically."""

    file: str
    line: int


def _split_top_level(text: str) -> list[str]:
    """Split on commas that are not inside quotes."""
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    for char in text:
        if quote:
            current.append(char)
            if char == quote:
                quote = None
        elif char in "\"'`":
            quote = char
            current.append(char)
        elif char == ",":
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return parts


def parse_destructuring(names_str: str) -> list[str]:
    """Parse the contents of ``const { ... } = process.env``.

    Handles aliases (``B: renamed``) and defaults (``C = 'x'``). The captured
    names are the *source* property names, i.e. the environment variable names.
    """
    names: list[str] = []
    for raw in _split_top_level(names_str):
        part = raw.strip()
        if not part:
            continue
        # Drop a default value.
        part = part.split("=", 1)[0].strip()
        # Drop an alias target, keeping the source key.
        part = part.split(":", 1)[0].strip()
        # Skip rest/spread elements; their names cannot be known statically.
        if part.startswith("."):
            continue
        # Quoted keys are not valid env names, but guard anyway.
        part = part.strip("\"'")
        if patterns.ENV_VAR_NAME.fullmatch(part):
            names.append(part)
    return names


def _dedupe(names: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for name in names:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def extract_usages(content: str, file_path: str) -> tuple[list[Usage], list[DynamicLookup]]:
    """Return ``(usages, dynamic_lookups)`` found in *content*.

    Every occurrence is kept (no deduplication across lines). Lines carrying
    the ``envsanity-ignore`` marker are skipped entirely.
    """
    usages: list[Usage] = []
    dynamic: list[DynamicLookup] = []

    for line_no, line in enumerate(content.splitlines(), start=1):
        if IGNORE_MARKER in line:
            continue

        for match in patterns.PROCESS_ENV_DOT.finditer(line):
            usages.append(Usage(match.group(1), file_path, line_no))

        for match in patterns.PROCESS_ENV_BRACKET.finditer(line):
            usages.append(Usage(match.group(1), file_path, line_no))

        for match in patterns.IMPORT_META_DOT.finditer(line):
            usages.append(Usage(match.group(1), file_path, line_no))

        for match in patterns.OS_GETENV.finditer(line):
            usages.append(Usage(match.group(1), file_path, line_no))

        for match in patterns.OS_ENVIRON_GET.finditer(line):
            usages.append(Usage(match.group(1), file_path, line_no))

        for match in patterns.OS_ENVIRON_BRACKET.finditer(line):
            usages.append(Usage(match.group(1), file_path, line_no))

        for match in patterns.PROCESS_ENV_DESTRUCTURE.finditer(line):
            for name in parse_destructuring(match.group(1)):
                usages.append(Usage(name, file_path, line_no))

        # Dynamic lookups: the variable name is not a string literal.
        is_dynamic = (
            patterns.PROCESS_ENV_DYNAMIC.search(line)
            or patterns.IMPORT_META_DYNAMIC.search(line)
            or patterns.OS_ENVIRON_DYNAMIC.search(line)
            or patterns.OS_GETENV_DYNAMIC.search(line)
            or patterns.OS_ENVIRON_GET_DYNAMIC.search(line)
        )
        if is_dynamic:
            dynamic.append(DynamicLookup(file_path, line_no))

    return usages, dynamic


def used_names(usages: list[Usage]) -> list[str]:
    """Return the distinct variable names, in first-seen order."""
    return _dedupe([usage.name for usage in usages])
