from pathlib import Path

import pytest

from envsanity import example


def write(tmp_path: Path, text: str, name: str = ".env.example", encoding: str = "utf-8"):
    path = tmp_path / name
    path.write_bytes(text.encode(encoding))
    return path


def test_basic_key_value(tmp_path):
    path = write(tmp_path, "API_KEY=abc\nPORT=3000\n")
    keys, warnings = example.parse_example_file(path)
    assert keys == [("API_KEY", 1), ("PORT", 2)]
    assert warnings == []


def test_empty_value(tmp_path):
    path = write(tmp_path, "EMPTY=\n")
    keys, _ = example.parse_example_file(path)
    assert keys == [("EMPTY", 1)]


def test_quoted_values(tmp_path):
    path = write(tmp_path, 'A="double"\nB=\'single\'\n')
    keys, _ = example.parse_example_file(path)
    assert keys == [("A", 1), ("B", 2)]


def test_export_prefix(tmp_path):
    path = write(tmp_path, "export API_KEY=abc\n")
    keys, _ = example.parse_example_file(path)
    assert keys == [("API_KEY", 1)]


def test_spaces_around_equals(tmp_path):
    path = write(tmp_path, "API_KEY = abc\n")
    keys, _ = example.parse_example_file(path)
    assert keys == [("API_KEY", 1)]


def test_inline_comment(tmp_path):
    path = write(tmp_path, "API_KEY=abc # the key\n")
    keys, _ = example.parse_example_file(path)
    assert keys == [("API_KEY", 1)]


def test_blank_and_comment_lines(tmp_path):
    path = write(tmp_path, "\n# a comment\n\nAPI_KEY=abc\n")
    keys, _ = example.parse_example_file(path)
    assert keys == [("API_KEY", 4)]


def test_crlf_line_endings(tmp_path):
    path = write(tmp_path, "A=1\r\nB=2\r\n")
    keys, _ = example.parse_example_file(path)
    assert keys == [("A", 1), ("B", 2)]


def test_utf8_bom(tmp_path):
    path = tmp_path / ".env.example"
    path.write_bytes(b"\xef\xbb\xbfA=1\nB=2\n")
    keys, _ = example.parse_example_file(path)
    assert keys == [("A", 1), ("B", 2)]


def test_duplicate_keys_warn_and_keep_first(tmp_path):
    path = write(tmp_path, "A=1\nA=2\n")
    keys, warnings = example.parse_example_file(path)
    assert keys == [("A", 1)]
    assert any("duplicate" in w.lower() for w in warnings)


def test_invalid_lines_ignored(tmp_path):
    path = write(tmp_path, "not a line\n=novalue\n123BAD=x\nGOOD=1\n")
    keys, _ = example.parse_example_file(path)
    assert keys == [("GOOD", 4)]


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        example.parse_example_file(tmp_path / "nope")


def test_find_example_file_order(tmp_path):
    (tmp_path / "example.env").write_text("A=1\n")
    assert example.find_example_file(tmp_path) == tmp_path / "example.env"
    (tmp_path / ".env.template").write_text("A=1\n")
    assert example.find_example_file(tmp_path) == tmp_path / ".env.template"
    (tmp_path / ".env.sample").write_text("A=1\n")
    assert example.find_example_file(tmp_path) == tmp_path / ".env.sample"
    (tmp_path / ".env.example").write_text("A=1\n")
    assert example.find_example_file(tmp_path) == tmp_path / ".env.example"


def test_find_example_file_none(tmp_path):
    assert example.find_example_file(tmp_path) is None


@pytest.mark.parametrize(
    "value",
    [
        "sk_live_abcdef123456",
        "AKIAIOSFODNN7EXAMPLE",
        "-----BEGIN RSA PRIVATE KEY-----",
    ],
)
def test_suspicious_values_warn(tmp_path, value):
    path = write(tmp_path, f"SECRET={value}\n")
    _, warnings = example.parse_example_file(path)
    assert any("secret" in w.lower() for w in warnings)


def test_long_high_entropy_value_warns(tmp_path):
    path = write(tmp_path, "TOKEN=" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6" + "\n")
    _, warnings = example.parse_example_file(path)
    assert any("secret" in w.lower() for w in warnings)


def test_placeholder_not_flagged(tmp_path):
    path = write(tmp_path, "TOKEN=your_example_token_here_1234567890\n")
    _, warnings = example.parse_example_file(path)
    assert warnings == []


def test_warning_never_contains_value(tmp_path):
    secret = "sk_live_SUPERSECRETVALUE123"
    path = write(tmp_path, f"KEY={secret}\n")
    _, warnings = example.parse_example_file(path)
    joined = "\n".join(warnings)
    assert secret not in joined
