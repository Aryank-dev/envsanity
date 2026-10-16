"""Parse the example env file (``.env.example``)."""

from __future__ import annotations

import re
from pathlib import Path

KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Values that look like secrets. We only ever report the *key* name.
SUSPICIOUS_PATTERNS = (
    re.compile(r"sk_live_"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]+"),
)

# Fallback candidates, tried in order when --example is not given.
EXAMPLE_FILENAMES = (".env.example", ".env.sample", ".env.template", "example.env")


def find_example_file(root: Path) -> Path | None:
    """Return the first existing example file in *root*, or ``None``."""
    for name in EXAMPLE_FILENAMES:
        candidate = Path(root) / name
        if candidate.exists():
            return candidate
    return None


def _strip_inline_comment(value: str) -> str:
    """Remove a trailing ``# comment`` from an unquoted value."""
    match = re.search(r"\s#", value)
    if match:
        return value[: match.start()].strip()
    return value.strip()


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
        return value[1:-1]
    return value


def is_suspicious_value(value: str) -> bool:
    """Heuristically decide whether *value* looks like a committed secret."""
    if not value:
        return False
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern.search(value):
            return True
    # Long, dense, single-token strings are usually secrets.
    if len(value) >= 32 and re.fullmatch(r"[A-Za-z0-9+/=_\-\.]+", value):
        # Avoid flagging obvious placeholders.
        lowered = value.lower()
        return not any(
            word in lowered for word in ("example", "changeme", "placeholder", "your_")
        )
    return False


def parse_example_file(file_path: Path) -> tuple[list[tuple[str, int]], list[str]]:
    """Parse an example env file.

    Returns ``(keys, warnings)`` where *keys* is a list of ``(name, line)`` in
    file order (first occurrence wins) and *warnings* is a list of human
    readable warning strings. Invalid lines are ignored.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"example file not found: {path}")

    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot read example file {path}: {exc}") from exc

    # Normalise line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    keys: list[tuple[str, int]] = []
    warnings: list[str] = []
    seen: set[str] = set()

    for line_no, raw_line in enumerate(text.split("\n"), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export ") :].strip()

        if "=" not in line:
            continue

        raw_key, raw_value = line.split("=", 1)
        key = raw_key.strip()
        if not KEY_RE.fullmatch(key):
            continue

        value = _strip_inline_comment(raw_value)
        value = _unquote(value)

        if key in seen:
            warnings.append(f"duplicate key in example file: {key} (line {line_no})")
        else:
            seen.add(key)
            keys.append((key, line_no))

        if is_suspicious_value(value):
            warnings.append(f"possible committed secret for key: {key} (line {line_no})")

    return keys, warnings
