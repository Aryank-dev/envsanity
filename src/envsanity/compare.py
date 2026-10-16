"""Compare used variables against documented variables."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

# Environment variables set by the OS or shell that are never expected to be
# documented in an example env file.
BUILTIN_IGNORE: set[str] = {
    "PATH",
    "HOME",
    "USER",
    "LOGNAME",
    "PWD",
    "OLDPWD",
    "SHELL",
    "TERM",
    "LANG",
    "LC_ALL",
    "TZ",
    "CI",
    "NODE_ENV",
    "HOSTNAME",
    "TMPDIR",
    "TEMP",
    "TMP",
    "EDITOR",
    "DISPLAY",
    "SSH_AUTH_SOCK",
    "COMSPEC",
    "SYSTEMROOT",
}

# Namespaces owned by CI tooling, not by the project.
BUILTIN_PREFIXES: tuple[str, ...] = ("GITHUB_", "RUNNER_", "npm_", "YARN_")


def should_ignore(name: str, extra_ignores: Iterable[str] = ()) -> bool:
    """Return True when *name* should never be reported."""
    if name in BUILTIN_IGNORE:
        return True
    if any(name.startswith(prefix) for prefix in BUILTIN_PREFIXES):
        return True
    return name in set(extra_ignores)


def compare(
    used_names: Sequence[str],
    documented_names: Sequence[str],
    ignored_names: Sequence[str] = (),
) -> tuple[list[str], list[str]]:
    """Return ``(missing, possibly_unused)``.

    * ``missing`` = used in code - documented - ignored
    * ``possibly_unused`` = documented - used - ignored

    Results are sorted and de-duplicated.
    """
    extra = list(ignored_names)
    used: set[str] = {n for n in used_names if not should_ignore(n, extra)}
    documented: set[str] = {n for n in documented_names if not should_ignore(n, extra)}

    missing = sorted(used - documented)
    possibly_unused = sorted(documented - used)
    return missing, possibly_unused
