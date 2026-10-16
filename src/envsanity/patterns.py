"""Every regular expression used by envsanity lives here.

The scanner is text based (not an AST), so these patterns are intentionally
permissive. They only ever capture the *name* of a variable, never its value.
"""

from __future__ import annotations

import re

# A valid environment variable name.
ENV_VAR_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# --- JavaScript / TypeScript ------------------------------------------------

# process.env.NAME  # envsanity-ignore
PROCESS_ENV_DOT = re.compile(r"process\.env\.([A-Za-z_][A-Za-z0-9_]*)")

# process.env["NAME"] / process.env['NAME']  # envsanity-ignore
PROCESS_ENV_BRACKET = re.compile(
    r"process\.env\[\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']\s*\]"
)

# process.env[key]  (dynamic: the key is not a string literal)  # envsanity-ignore
PROCESS_ENV_DYNAMIC = re.compile(r"process\.env\[\s*(?![\"'])[^\]]")

# const { A, B: renamed, C = 'x' } = process.env  # envsanity-ignore
PROCESS_ENV_DESTRUCTURE = re.compile(
    r"(?:const|let|var)\s+\{([^}]+)\}\s*=\s*process\.env"
)

# import.meta.env.NAME  # envsanity-ignore
IMPORT_META_DOT = re.compile(r"import\.meta\.env\.([A-Za-z_][A-Za-z0-9_]*)")

# import.meta.env[key]  (dynamic)  # envsanity-ignore
IMPORT_META_DYNAMIC = re.compile(r"import\.meta\.env\[\s*(?![\"'])[^\]]")

# --- Python -----------------------------------------------------------------

# os.getenv("NAME") and os.getenv("NAME", default)  # envsanity-ignore
OS_GETENV = re.compile(
    r"os\.getenv\(\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']\s*(?:,[^)]*)?\)"
)

# os.environ.get("NAME") and os.environ.get("NAME", default)  # envsanity-ignore
OS_ENVIRON_GET = re.compile(
    r"os\.environ\.get\(\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']\s*(?:,[^)]*)?\)"
)

# os.environ["NAME"]  # envsanity-ignore
OS_ENVIRON_BRACKET = re.compile(
    r"os\.environ\[\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']\s*\]"
)

# os.environ[key]  (dynamic)  # envsanity-ignore
OS_ENVIRON_DYNAMIC = re.compile(r"os\.environ\[\s*(?![\"'])[^\]]")

# os.getenv(name)  (dynamic)  # envsanity-ignore
OS_GETENV_DYNAMIC = re.compile(r"os\.getenv\(\s*(?![\"'])[^)]")

# os.environ.get(name)  (dynamic)  # envsanity-ignore
OS_ENVIRON_GET_DYNAMIC = re.compile(r"os\.environ\.get\(\s*(?![\"'])[^)]")
