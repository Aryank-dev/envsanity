"""Find source files to scan."""

from __future__ import annotations

import fnmatch
from collections.abc import Iterable
from pathlib import Path

# Directories that are never scanned.
SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        "dist",
        "build",
        ".next",
        ".idea",
        "vendor",
    }
)

# Extensions we understand.
EXTENSIONS = frozenset({".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py"})

MAX_SIZE_BYTES = 1024 * 1024  # 1 MB


def _is_excluded(rel_path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, pattern) for pattern in patterns)


def _has_skipped_part(rel_parts: tuple[str, ...]) -> bool:
    return any(part in SKIP_DIRS for part in rel_parts)


def find_files(
    root: Path,
    exclude_patterns: list[str] | None = None,
    example_file: Path | None = None,
) -> list[Path]:
    """Walk *root* and return the source files that should be scanned.

    * ``exclude_patterns`` are matched against paths relative to *root*.
    * *example_file* is never returned.
    """
    exclude_patterns = exclude_patterns or []
    root = Path(root).resolve()
    example_resolved = Path(example_file).resolve() if example_file else None

    results: list[Path] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        try:
            rel = path.relative_to(root)
        except ValueError:  # pragma: no cover - defensive
            continue

        if _has_skipped_part(rel.parts):
            continue

        if example_resolved is not None and path.resolve() == example_resolved:
            continue

        if path.suffix.lower() not in EXTENSIONS:
            continue

        if _is_excluded(str(rel), exclude_patterns):
            continue

        try:
            if path.stat().st_size > MAX_SIZE_BYTES:
                continue
        except OSError:
            continue

        if not _is_utf8(path):
            continue

        results.append(path)

    return results


def _is_utf8(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            data = handle.read()
    except OSError:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True
