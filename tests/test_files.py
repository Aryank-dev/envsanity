from pathlib import Path

from envsanity import files


def rel(result, root):
    return sorted(p.relative_to(Path(root).resolve()).as_posix() for p in result)


def test_finds_supported_extensions(tmp_path):
    for name in ["a.py", "b.js", "c.jsx", "d.ts", "e.tsx", "f.mjs", "g.cjs"]:
        (tmp_path / name).write_text("x = 1\n")
    (tmp_path / "notes.txt").write_text("nope\n")
    (tmp_path / "data.json").write_text("{}\n")
    assert rel(files.find_files(tmp_path), tmp_path) == [
        "a.py",
        "b.js",
        "c.jsx",
        "d.ts",
        "e.tsx",
        "f.mjs",
        "g.cjs",
    ]


def test_skips_node_modules_and_git(tmp_path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.js").write_text("process.env.X\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "hook.py").write_text("x = 1\n")
    (tmp_path / "app.py").write_text("x = 1\n")
    assert rel(files.find_files(tmp_path), tmp_path) == ["app.py"]


def test_skips_other_directories(tmp_path):
    for name in ["dist", "build", ".venv", "venv", "__pycache__", ".next", ".idea", "vendor"]:
        d = tmp_path / name
        d.mkdir()
        (d / "file.py").write_text("x = 1\n")
    (tmp_path / "keep.py").write_text("x = 1\n")
    assert rel(files.find_files(tmp_path), tmp_path) == ["keep.py"]


def test_exclude_glob(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text("x = 1\n")
    (tmp_path / "app.py").write_text("x = 1\n")
    found = files.find_files(tmp_path, exclude_patterns=["tests/**"])
    assert rel(found, tmp_path) == ["app.py"]


def test_exclude_single_file_glob(tmp_path):
    (tmp_path / "generated.py").write_text("x = 1\n")
    (tmp_path / "app.py").write_text("x = 1\n")
    found = files.find_files(tmp_path, exclude_patterns=["generated.py"])
    assert rel(found, tmp_path) == ["app.py"]


def test_skips_large_files(tmp_path):
    big = tmp_path / "big.py"
    big.write_text("# " + "a" * (1024 * 1024 + 10))
    (tmp_path / "small.py").write_text("x = 1\n")
    assert rel(files.find_files(tmp_path), tmp_path) == ["small.py"]


def test_skips_non_utf8(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_bytes(b"\xff\xfe\x00\x00invalid")
    (tmp_path / "good.py").write_text("x = 1\n")
    assert rel(files.find_files(tmp_path), tmp_path) == ["good.py"]


def test_never_scans_example_file(tmp_path):
    example = tmp_path / ".env.example"
    example.write_text("A=1\n")
    # Pretend the example file has a scannable extension.
    weird = tmp_path / "custom.py"
    weird.write_text("A=1\n")
    found = files.find_files(tmp_path, example_file=weird)
    assert "custom.py" not in rel(found, tmp_path)


def test_empty_tree(tmp_path):
    assert files.find_files(tmp_path) == []
