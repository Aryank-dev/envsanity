import json

from envsanity import report


def make_data(**overrides):
    defaults = {
        "files_scanned": 142,
        "used": ["API_KEY", "REDIS_URL", "STRIPE_SECRET_KEY"],
        "documented": [("API_KEY", 1), ("OLD_API_KEY", 7)],
        "missing": [
            report.MissingEntry(
                "STRIPE_SECRET_KEY",
                [
                    report.Location("src/payments.js", 14),
                    report.Location("src/webhooks.js", 3),
                ],
            ),
            report.MissingEntry("REDIS_URL", [report.Location("app/cache.py", 8)]),
        ],
        "possibly_unused": [report.UnusedEntry("OLD_API_KEY", 7)],
        "dynamic": [
            report.Location("src/config.js", 22),
            report.Location("src/other.js", 9),
        ],
    }
    defaults.update(overrides)
    return report.ReportData(**defaults)


def passing_data():
    return report.ReportData(
        files_scanned=3,
        used=["A", "B"],
        documented=[("A", 1), ("B", 2)],
        missing=[],
        possibly_unused=[],
        dynamic=[],
    )


def test_text_failing_contains_sections(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    out = report.format_text(make_data(), no_color=True)
    assert "envsanity v" in out
    assert "Scanned 142 files" in out
    assert "✖ MISSING from .env.example (2)" in out
    assert "STRIPE_SECRET_KEY" in out
    assert "src/payments.js:14" in out
    assert "src/webhooks.js:3" in out
    assert "REDIS_URL" in out
    assert "app/cache.py:8" in out
    assert "⚠ POSSIBLY UNUSED in .env.example (1)" in out
    assert "OLD_API_KEY" in out
    assert "2 dynamic lookups could not be checked" in out
    assert "src/config.js:22" in out
    assert "✖ FAILED: 2 missing variables" in out
    assert "  STRIPE_SECRET_KEY=" in out
    assert "Or run:  envsanity --fix" in out
    assert "\033[" not in out


def test_text_passing():
    out = report.format_text(passing_data(), no_color=True)
    assert "✔ All 2 variables used in code are documented in .env.example" in out
    assert "MISSING" not in out
    assert "FAILED" not in out


def test_text_uses_color_when_tty(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(report.sys.stdout, "isatty", lambda: True, raising=False)
    out = report.format_text(make_data(), no_color=False)
    assert "\033[" in out


def test_text_no_color_flag(monkeypatch):
    monkeypatch.setattr(report.sys.stdout, "isatty", lambda: True, raising=False)
    out = report.format_text(make_data(), no_color=True)
    assert "\033[" not in out


def test_text_respects_no_color_env(monkeypatch):
    monkeypatch.setattr(report.sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setenv("NO_COLOR", "1")
    out = report.format_text(make_data(), no_color=False)
    assert "\033[" not in out


def test_text_not_tty_has_no_color(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(report.sys.stdout, "isatty", lambda: False, raising=False)
    out = report.format_text(make_data(), no_color=False)
    assert "\033[" not in out


def test_json_format():
    payload = json.loads(report.format_json(make_data()))
    assert payload["version"]
    assert payload["files_scanned"] == 142
    assert payload["ok"] is False
    assert payload["dynamic_lookups"] == 2
    assert payload["unused"] == ["OLD_API_KEY"]
    assert payload["missing"][0]["name"] == "STRIPE_SECRET_KEY"
    assert payload["missing"][0]["locations"] == [
        {"file": "src/payments.js", "line": 14},
        {"file": "src/webhooks.js", "line": 3},
    ]
    assert payload["missing"][1] == {
        "name": "REDIS_URL",
        "locations": [{"file": "app/cache.py", "line": 8}],
    }
    names = {entry["name"] for entry in payload["missing"]}
    assert names == {"REDIS_URL", "STRIPE_SECRET_KEY"}


def test_json_passing():
    payload = json.loads(report.format_json(passing_data()))
    assert payload["ok"] is True
    assert payload["missing"] == []
    assert payload["unused"] == []


def test_github_format_errors_and_warnings():
    out = report.format_github(make_data())
    assert (
        "::error file=src/payments.js,line=14,title=envsanity::"
        "STRIPE_SECRET_KEY is used here but missing from .env.example" in out
    )
    assert "::error file=app/cache.py,line=8" in out
    assert "::warning file=.env.example,line=7,title=envsanity::OLD_API_KEY" in out


def test_github_summary_appended(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    report.format_github(make_data())
    text = summary.read_text()
    assert "| Variable | File | Line |" in text
    assert "| REDIS_URL | app/cache.py | 8 |" in text
    assert "Possibly unused" in text


def test_github_summary_passing(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    report.format_github(passing_data())
    assert "All variables used in code are documented" in summary.read_text()


def test_github_no_summary_env(monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    # Should not raise.
    assert report.format_github(passing_data()) == ""
