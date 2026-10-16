import json
from pathlib import Path

import pytest

from envsanity import cli

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PASSING = FIXTURES / "passing"
FAILING = FIXTURES / "failing"
MESSY = FIXTURES / "messy"


def run(argv):
    return cli.main(argv)


# --- fixtures ---------------------------------------------------------------


def test_passing_fixture_exit_zero(capsys):
    code = run([str(PASSING)])
    out = capsys.readouterr().out
    assert code == 0
    assert "documented in .env.example" in out


def test_failing_fixture_exit_one(capsys):
    code = run([str(FAILING)])
    out = capsys.readouterr().out
    assert code == 1
    assert "MISSING" in out
    assert "STRIPE_SECRET_KEY" in out
    assert "REDIS_URL" in out
    assert "OLD_API_KEY" in out


def test_messy_fixture(capsys):
    code = run([str(MESSY), "--no-color"])
    out = capsys.readouterr().out
    assert code == 1
    # node_modules is skipped
    assert "SHOULD_NOT_BE_SCANNED" not in out
    # ignore marker honoured
    assert "NOT_REAL" not in out
    # destructuring alias captures the source key
    assert "SECRET_TOKEN" not in out  # documented
    assert "VITE_API_URL" in out
    assert "dynamic lookups could not be checked" in out


# --- error paths (exit 2) ---------------------------------------------------


def test_path_not_found(capsys):
    code = run(["/no/such/path/xyz"])
    err = capsys.readouterr().err
    assert code == 2
    assert "path not found" in err
    assert "Traceback" not in err


def test_path_is_file(tmp_path, capsys):
    f = tmp_path / "file.txt"
    f.write_text("x")
    code = run([str(f)])
    assert code == 2
    assert "not a directory" in capsys.readouterr().err


def test_example_not_found(tmp_path, capsys):
    (tmp_path / "app.py").write_text("x = 1\n")
    code = run([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 2
    assert "example file not found" in err
    assert "Traceback" not in err


def test_explicit_example_not_found(tmp_path, capsys):
    (tmp_path / ".env.example").write_text("A=1\n")
    code = run([str(tmp_path), "--example", "nope.env"])
    assert code == 2
    assert "example file not found" in capsys.readouterr().err


def test_invalid_config_exit_two(tmp_path, capsys):
    (tmp_path / ".env.example").write_text("A=1\n")
    (tmp_path / ".envsanity.toml").write_text("this is = = not valid toml")
    code = run([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 2
    assert "invalid" in err.lower()
    assert "Traceback" not in err


# --- formats ----------------------------------------------------------------


def test_json_format(capsys):
    code = run([str(FAILING), "--format", "json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 1
    assert payload["ok"] is False
    assert {m["name"] for m in payload["missing"]} == {"REDIS_URL", "STRIPE_SECRET_KEY"}


def test_github_format(capsys):
    code = run([str(FAILING), "--format", "github"])
    out = capsys.readouterr().out
    assert code == 1
    assert "::error file=payments.js,line=1" in out
    assert "title=envsanity::STRIPE_SECRET_KEY" in out
    assert "::warning file=.env.example" in out


def test_github_summary_written(tmp_path, monkeypatch, capsys):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    run([str(FAILING), "--format", "github"])
    assert "| Variable | File | Line |" in summary.read_text()


# --- strict -----------------------------------------------------------------


def test_strict_fails_on_possibly_unused(tmp_path, capsys):
    (tmp_path / ".env.example").write_text("USED=1\nUNUSED=2\n")
    (tmp_path / "app.py").write_text('x = os.getenv("USED")\n')
    assert run([str(tmp_path)]) == 0
    assert run([str(tmp_path), "--strict"]) == 1


def test_strict_passes_when_clean(capsys):
    assert run([str(PASSING), "--strict"]) == 0


# --- fix --------------------------------------------------------------------


def test_fix_appends_without_touching_existing(tmp_path, capsys):
    example = tmp_path / ".env.example"
    original = "# comment\nAPI_KEY=abc\n\n# trailing note\n"
    example.write_text(original)
    (tmp_path / "app.py").write_text('a = os.getenv("API_KEY")\nb = os.getenv("NEW_VAR")\n')

    code = run([str(tmp_path), "--fix"])
    assert code == 1
    content = example.read_text()
    # Everything that existed is untouched and still in order.
    assert content.startswith(original)
    # New key appended at the very end.
    assert content.endswith("NEW_VAR=\n")
    assert content.count("API_KEY=") == 1


def test_fix_creates_file_when_missing(tmp_path, capsys):
    (tmp_path / "app.py").write_text('a = os.getenv("NEW_VAR")\n')
    code = run([str(tmp_path), "--example", ".env.example", "--fix"])
    assert code == 1
    example = tmp_path / ".env.example"
    assert example.exists()
    assert example.read_text() == "NEW_VAR=\n"


def test_fix_then_rerun_passes(tmp_path, capsys):
    (tmp_path / ".env.example").write_text("API_KEY=abc\n")
    (tmp_path / "app.py").write_text('a = os.getenv("API_KEY")\nb = os.getenv("NEW_VAR")\n')
    assert run([str(tmp_path), "--fix"]) == 1
    assert run([str(tmp_path)]) == 0
    assert run([str(tmp_path), "--fix"]) == 0


def test_fix_preserves_crlf_and_bom(tmp_path, capsys):
    example = tmp_path / ".env.example"
    example.write_bytes(b"\xef\xbb\xbfAPI_KEY=abc\r\n")
    (tmp_path / "app.py").write_text('a = os.getenv("NEW_VAR")\n')
    run([str(tmp_path), "--fix"])
    raw = example.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" in raw  # original CRLF preserved
    assert raw.endswith(b"NEW_VAR=\n")


# --- ignore / exclude -------------------------------------------------------


def test_ignore_flag(tmp_path, capsys):
    (tmp_path / ".env.example").write_text("")
    (tmp_path / "app.py").write_text('a = os.getenv("IGNORED_VAR")\n')
    assert run([str(tmp_path)]) == 1
    assert run([str(tmp_path), "--ignore", "IGNORED_VAR"]) == 0


def test_ignore_multiple(tmp_path, capsys):
    (tmp_path / ".env.example").write_text("")
    (tmp_path / "app.py").write_text('a = os.getenv("A")\nb = os.getenv("B")\n')
    assert run([str(tmp_path), "--ignore", "A,B"]) == 0


def test_exclude_flag(tmp_path, capsys):
    (tmp_path / ".env.example").write_text("")
    (tmp_path / "app.py").write_text('a = os.getenv("IGNORED_VAR")\n')
    assert run([str(tmp_path)]) == 1
    assert run([str(tmp_path), "--exclude", "app.py"]) == 0


# --- config -----------------------------------------------------------------


def test_config_ignore_applied(tmp_path, capsys):
    (tmp_path / ".env.example").write_text("")
    (tmp_path / ".envsanity.toml").write_text('ignore = ["IGNORED_VAR"]\n')
    (tmp_path / "app.py").write_text('a = os.getenv("IGNORED_VAR")\n')
    assert run([str(tmp_path)]) == 0


def test_config_strict_applied(tmp_path, capsys):
    (tmp_path / ".env.example").write_text("USED=1\nUNUSED=2\n")
    (tmp_path / ".envsanity.toml").write_text("strict = true\n")
    (tmp_path / "app.py").write_text('x = os.getenv("USED")\n')
    assert run([str(tmp_path)]) == 1


def test_cli_ignore_overrides_config(tmp_path, capsys):
    (tmp_path / ".env.example").write_text("")
    (tmp_path / ".envsanity.toml").write_text('ignore = ["A", "B"]\n')
    (tmp_path / "app.py").write_text('a = os.getenv("A")\nb = os.getenv("B")\n')
    # config ignores both -> pass
    assert run([str(tmp_path)]) == 0
    # CLI ignore replaces config -> only A ignored, B is missing
    assert run([str(tmp_path), "--ignore", "A"]) == 1


def test_config_example_file(tmp_path, capsys):
    (tmp_path / "custom.env").write_text("API_KEY=1\n")
    (tmp_path / ".envsanity.toml").write_text('example_file = "custom.env"\n')
    (tmp_path / "app.py").write_text('a = os.getenv("API_KEY")\n')
    assert run([str(tmp_path)]) == 0


def test_config_exclude_applied(tmp_path, capsys):
    (tmp_path / ".env.example").write_text("")
    (tmp_path / ".envsanity.toml").write_text('exclude = ["generated/**"]\n')
    (tmp_path / "generated").mkdir()
    (tmp_path / "generated" / "gen.py").write_text('a = os.getenv("IGNORED_VAR")\n')
    assert run([str(tmp_path)]) == 0


def test_cli_exclude_overrides_config(tmp_path, capsys):
    (tmp_path / ".env.example").write_text("")
    (tmp_path / ".envsanity.toml").write_text('exclude = ["a.py"]\n')
    (tmp_path / "a.py").write_text('x = os.getenv("A_VAR")\n')
    (tmp_path / "b.py").write_text('y = os.getenv("B_VAR")\n')
    # config excludes a.py -> B_VAR still missing -> fail
    assert run([str(tmp_path)]) == 1
    # CLI excludes b.py instead -> A_VAR still missing -> fail
    assert run([str(tmp_path), "--exclude", "b.py"]) == 1
    # CLI excludes both via repeated flag -> pass
    assert run([str(tmp_path), "--exclude", "a.py", "--exclude", "b.py"]) == 0


# --- secrecy ----------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["text", "json", "github"])
def test_secret_value_never_in_output(tmp_path, capsys, fmt):
    secret = "sk_live_SUPERSECRETDO NOTPRINT"
    (tmp_path / ".env.example").write_text(f"STRIPE_SECRET={secret}\n")
    (tmp_path / "app.py").write_text('a = os.getenv("MISSING_VAR")\n')
    run([str(tmp_path), "--format", fmt])
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert secret not in combined
    assert "SUPERSECRET" not in combined


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        run(["--version"])
    assert exc.value.code == 0
    assert "0.1.0" in capsys.readouterr().out
