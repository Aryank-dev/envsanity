"""Command line interface for envsanity."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from . import compare as compare_mod
from . import config as config_mod
from . import example as example_mod
from . import files as files_mod
from . import report as report_mod
from . import scanner as scanner_mod

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="envsanity",
        description=(
            "Fail when code uses an environment variable that is not "
            "documented in the example env file."
        ),
    )
    parser.add_argument("path", nargs="?", default=".", help="folder to scan (default: .)")
    parser.add_argument(
        "--example",
        metavar="FILE",
        help="path to the example env file (auto-detected when omitted)",
    )
    parser.add_argument(
        "--ignore",
        metavar="A,B,C",
        help="comma-separated variable names to ignore",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        metavar="GLOB",
        help="glob (relative to the scanned folder) to exclude; repeatable",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat possibly unused variables as failures",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "github"),
        default="text",
        help="output format (default: text)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="append missing keys to the example file (append only)",
    )
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    parser.add_argument(
        "--version", action="version", version=f"envsanity {__version__}"
    )
    return parser


def _split_ignore(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return []


def _resolve_example(
    root: Path, cli_example: str | None, config_example: object
) -> Path | None:
    chosen = cli_example if cli_example else config_example
    if chosen:
        path = Path(str(chosen))
        if not path.is_absolute():
            path = root / path
        return path
    return example_mod.find_example_file(root)


def _append_to_example(example_path: Path, keys: Sequence[str]) -> None:
    """Append ``KEY=`` lines, creating the file if needed. Append only."""
    existing = ""
    if example_path.exists():
        raw = example_path.read_bytes()
        existing = raw.decode("utf-8")

    if existing and not existing.endswith("\n"):
        existing += "\n"

    for key in keys:
        existing += f"{key}=\n"

    example_path.parent.mkdir(parents=True, exist_ok=True)
    example_path.write_bytes(existing.encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return _run(args)
    except config_mod.ConfigError as exc:
        print(f"envsanity: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as exc:  # noqa: BLE001 - the CLI must never show a traceback
        print(f"envsanity: error: {exc}", file=sys.stderr)
        return EXIT_ERROR


def _run(args: argparse.Namespace) -> int:
    root = Path(args.path)
    if not root.exists():
        print(f"envsanity: path not found: {args.path}", file=sys.stderr)
        return EXIT_ERROR
    if not root.is_dir():
        print(f"envsanity: not a directory: {args.path}", file=sys.stderr)
        return EXIT_ERROR
    root = root.resolve()

    try:
        config = config_mod.load_config(root)
    except config_mod.ConfigError as exc:
        print(f"envsanity: {exc}", file=sys.stderr)
        return EXIT_ERROR

    example_path = _resolve_example(root, args.example, config.get("example_file"))
    if example_path is None:
        print(
            "envsanity: example file not found "
            "(.env.example, .env.sample, .env.template, example.env)",
            file=sys.stderr,
        )
        return EXIT_ERROR
    if not example_path.exists() and not args.fix:
        print(f"envsanity: example file not found: {example_path}", file=sys.stderr)
        return EXIT_ERROR

    ignore = _split_ignore(args.ignore)
    if not ignore:
        ignore = _as_list(config.get("ignore"))
    exclude = list(args.exclude) if args.exclude else _as_list(config.get("exclude"))
    strict = bool(args.strict or config.get("strict", False))

    source_files = files_mod.find_files(
        root, exclude_patterns=exclude, example_file=example_path
    )

    usages: list[scanner_mod.Usage] = []
    dynamic: list[report_mod.Location] = []
    for path in source_files:
        rel = _relative(path, root)
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        file_usages, file_dynamic = scanner_mod.extract_usages(content, rel)
        usages.extend(file_usages)
        dynamic.extend(report_mod.Location(d.file, d.line) for d in file_dynamic)

    if not example_path.exists():
        documented: list = []
        example_warnings: list[str] = []
    else:
        documented, example_warnings = example_mod.parse_example_file(example_path)

    used = scanner_mod.used_names(usages)
    documented_names = [name for name, _ in documented]

    missing_names, unused_names = compare_mod.compare(used, documented_names, ignore)

    locations_by_name: dict[str, list[report_mod.Location]] = defaultdict(list)
    for usage in usages:
        location = report_mod.Location(usage.file, usage.line)
        if location not in locations_by_name[usage.name]:
            locations_by_name[usage.name].append(location)

    doc_line = dict(documented)

    data = report_mod.ReportData(
        files_scanned=len(source_files),
        used=used,
        documented=documented,
        missing=[
            report_mod.MissingEntry(name, locations_by_name.get(name, []))
            for name in missing_names
        ],
        possibly_unused=[
            report_mod.UnusedEntry(name, doc_line.get(name, 0)) for name in unused_names
        ],
        dynamic=dynamic,
    )

    if args.fix and missing_names:
        _append_to_example(example_path, missing_names)

    for warning in example_warnings:
        print(f"warning: {warning}", file=sys.stderr)

    if args.format == "json":
        print(report_mod.format_json(data))
    elif args.format == "github":
        print(report_mod.format_github(data))
    else:
        print(report_mod.format_text(data, no_color=args.no_color))

    if missing_names:
        return EXIT_FAILED
    if strict and unused_names:
        return EXIT_FAILED
    return EXIT_OK


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:  # pragma: no cover - defensive
        return str(path)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
