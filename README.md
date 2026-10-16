# envsanity

Fails a pull request when code uses an environment variable that is not documented in `.env.example`.

## The Problem

Environment variables are easy to add in code but often forgotten in `.env.example` files. This causes confusion for new developers and broken local setups. Without documentation, teams waste time figuring out what configuration is needed. envsanity catches these issues early in CI.

## Installation

```bash
pip install .
```

## Usage

| Command | Description |
|---|---|
| `envsanity` | Scan current directory |
| `envsanity /path/to/project` | Scan specific path |
| `envsanity --example .env.example` | Specify example file |
| `envsanity --ignore A,B,C` | Ignore specific variables |
| `envsanity --exclude "tests/**"` | Exclude files by glob pattern |
| `envsanity --strict` | Also fail on possibly unused variables |
| `envsanity --format json` | Output JSON format |
| `envsanity --format github` | Output GitHub Actions workflow commands |
| `envsanity --fix` | Append missing keys to .env.example |
| `envsanity --no-color` | Disable colored output |

## Examples

### Failing run

```text
envsanity v0.1.0

Scanned 142 files
Found 12 variables in code · 11 in .env.example

✖ MISSING from .env.example (2)
  STRIPE_SECRET_KEY    src/payments.js:14
                       src/webhooks.js:3
  REDIS_URL            app/cache.py:8

⚠ POSSIBLY UNUSED in .env.example (1)
  OLD_API_KEY          .env.example:7
  (may still be used by Docker or deploy scripts)

ℹ 2 dynamic lookups could not be checked
  src/config.js:22

──────────────────────────────────────────
✖ FAILED: 2 missing variables

To fix, add these to .env.example:
  STRIPE_SECRET_KEY=
  REDIS_URL=

Or run:  envsanity --fix
```

### Passing run

```text
envsanity v0.1.0

Scanned 142 files
Found 12 variables in code · 12 in .env.example

──────────────────────────────────────────
✔ All 12 variables used in code are documented in .env.example
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | No missing variables |
| `1` | Missing variables found (or possibly unused variables in `--strict` mode) |
| `2` | Tool error (path not found, example file not found, invalid config) |

Exit code `2` prints a short message to stderr and never a Python traceback.

## GitHub Actions

This repository ships a composite action (root `action.yml`). Use it directly:

```yaml
- name: Check env vars
  uses: Aryank-dev/envsanity@v1
  with:
    path: '.'
    example-file: '.env.example'
    strict: 'false'
```

Or call the CLI directly in a workflow:

```yaml
- name: Check env vars
  run: |
    pip install .
    envsanity . --format github
```

## Configuration

Create `.envsanity.toml` in your project root:

```toml
example_file = ".env.example"
ignore = ["CUSTOM_VAR"]
exclude = ["tests/**", "docs/**"]
strict = false
```

Command-line flags override config values.

When `--example` is not given, envsanity looks for these files in order:
`.env.example`, `.env.sample`, `.env.template`, `example.env`.

To skip a single line, add the text `envsanity-ignore` anywhere on it:

```js
const legacy = process.env.NOT_DOCUMENTED; // envsanity-ignore
```

The text report respects the `NO_COLOR` environment variable and the
`--no-color` flag.

## How it works

1. Scans source files for environment variable usage patterns.
2. Parses the `.env.example` file to find documented variables.
3. Compares used vs documented variables.
4. Reports missing variables as errors and possibly unused as warnings.
5. Can automatically fix by appending missing keys.

## Known limitations

- Commented-out code still counts as usage.
- Dynamic lookups (e.g., `process.env[key]` with a variable key) cannot be resolved.
- Uses text matching instead of AST parsing.
- The tool only scans JavaScript/TypeScript and Python files.
