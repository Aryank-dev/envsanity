"""Render results as text, JSON or GitHub Actions workflow commands."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field

from . import __version__

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
DIM = "\033[2m"


@dataclass
class Location:
    file: str
    line: int


@dataclass
class MissingEntry:
    name: str
    locations: list[Location] = field(default_factory=list)


@dataclass
class UnusedEntry:
    name: str
    line: int


@dataclass
class ReportData:
    files_scanned: int
    used: list[str]
    documented: list[tuple[str, int]]
    missing: list[MissingEntry]
    possibly_unused: list[UnusedEntry]
    dynamic: list[Location]

    @property
    def ok(self) -> bool:
        return not self.missing


def color_enabled(no_color: bool) -> bool:
    """Colour is used only for a TTY, and never when disabled."""
    if no_color:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    try:
        return bool(sys.stdout.isatty())
    except (AttributeError, ValueError):  # pragma: no cover - defensive
        return False


def _paint(text: str, code: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{code}{text}{RESET}"


def _pad(name: str, width: int = 20) -> str:
    """Left-align *name* in *width*, always leaving a separating space."""
    return name.ljust(width) if len(name) < width else name + " "


def format_text(data: ReportData, no_color: bool = False) -> str:
    use_color = color_enabled(no_color)

    def paint(text: str, code: str) -> str:
        return _paint(text, code, use_color)

    out: list[str] = []
    out.append(paint(f"envsanity v{__version__}", BOLD))
    out.append("")
    out.append(f"Scanned {data.files_scanned} files")
    out.append(
        f"Found {len(data.used)} variables in code · "
        f"{len(data.documented)} in .env.example"
    )
    out.append("")

    if data.missing:
        out.append(paint(f"✖ MISSING from .env.example ({len(data.missing)})", RED))
        for entry in data.missing:
            if entry.locations:
                first = entry.locations[0]
                out.append(f"  {_pad(entry.name)}{first.file}:{first.line}")
                for loc in entry.locations[1:]:
                    out.append(f"  {'':<20}{loc.file}:{loc.line}")
            else:  # pragma: no cover - defensive
                out.append(f"  {entry.name}")
        out.append("")

    if data.possibly_unused:
        out.append(
            paint(
                f"⚠ POSSIBLY UNUSED in .env.example ({len(data.possibly_unused)})",
                YELLOW,
            )
        )
        for entry in data.possibly_unused:
            out.append(f"  {_pad(entry.name)}.env.example:{entry.line}")
        out.append("  (may still be used by Docker or deploy scripts)")
        out.append("")

    if data.dynamic:
        out.append(
            paint(
                f"ℹ {len(data.dynamic)} dynamic lookups could not be checked",
                BLUE,
            )
        )
        for loc in data.dynamic:
            out.append(f"  {loc.file}:{loc.line}")
        out.append("")

    out.append("─" * 42)
    if data.missing:
        out.append(paint(f"✖ FAILED: {len(data.missing)} missing variables", RED))
        out.append("")
        out.append("To fix, add these to .env.example:")
        for entry in data.missing:
            out.append(f"  {entry.name}=")
        out.append("")
        out.append("Or run:  envsanity --fix")
    else:
        out.append(
            paint(
                f"✔ All {len(data.used)} variables used in code are documented in .env.example",
                GREEN,
            )
        )

    return "\n".join(out)


def format_json(data: ReportData) -> str:
    payload = {
        "version": __version__,
        "files_scanned": data.files_scanned,
        "missing": [
            {
                "name": entry.name,
                "locations": [
                    {"file": loc.file, "line": loc.line} for loc in entry.locations
                ],
            }
            for entry in data.missing
        ],
        "unused": [entry.name for entry in data.possibly_unused],
        "dynamic_lookups": len(data.dynamic),
        "ok": data.ok,
    }
    return json.dumps(payload)


def format_github(data: ReportData) -> str:
    lines: list[str] = []
    for entry in data.missing:
        for loc in entry.locations:
            lines.append(
                f"::error file={loc.file},line={loc.line},title=envsanity::"
                f"{entry.name} is used here but missing from .env.example"
            )
    for entry in data.possibly_unused:
        lines.append(
            f"::warning file=.env.example,line={entry.line},title=envsanity::"
            f"{entry.name} is possibly unused"
        )

    _append_step_summary(data)
    return "\n".join(lines)


def _append_step_summary(data: ReportData) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    rows: list[str] = ["# envsanity report", ""]
    if data.missing:
        rows.append("## Missing from .env.example")
        rows.append("")
        rows.append("| Variable | File | Line |")
        rows.append("| --- | --- | --- |")
        for entry in data.missing:
            for loc in entry.locations:
                rows.append(f"| {entry.name} | {loc.file} | {loc.line} |")
        rows.append("")
    if data.possibly_unused:
        rows.append("## Possibly unused in .env.example")
        rows.append("")
        rows.append("| Variable | Example file | Line |")
        rows.append("| --- | --- | --- |")
        for entry in data.possibly_unused:
            rows.append(f"| {entry.name} | .env.example | {entry.line} |")
        rows.append("")
    if not data.missing and not data.possibly_unused:
        rows.append("All variables used in code are documented. ✔")
        rows.append("")

    try:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(rows) + "\n")
    except OSError:  # pragma: no cover - best effort
        pass
