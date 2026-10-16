from envsanity import scanner


def names(content: str, path: str = "app.js"):
    usages, _ = scanner.extract_usages(content, path)
    return [u.name for u in usages]


def test_process_env_dot():
    assert names("const a = process.env.API_KEY;") == ["API_KEY"]


def test_process_env_bracket_double():
    assert names('const a = process.env["API_KEY"];') == ["API_KEY"]


def test_process_env_bracket_single():
    assert names("const a = process.env['API_KEY'];") == ["API_KEY"]


def test_multiple_on_one_line():
    got = names("f(process.env.A, process.env.B)")
    assert got == ["A", "B"]


def test_port_number_captured_in_full():
    assert names("const p = process.env.PORT_NUMBER;") == ["PORT_NUMBER"]


def test_destructuring_plain():
    assert names("const { A, B } = process.env;") == ["A", "B"]


def test_destructuring_alias_and_default():
    content = "const { A, B: renamed, C = 'x' } = process.env;"
    assert names(content) == ["A", "B", "C"]


def test_destructuring_with_let_and_var():
    assert names("let { A } = process.env;") == ["A"]
    assert names("var { B } = process.env;") == ["B"]


def test_import_meta_env():
    assert names("const v = import.meta.env.VITE_API_URL;") == ["VITE_API_URL"]


def test_python_os_getenv():
    assert names('x = os.getenv("API_KEY")', "app.py") == ["API_KEY"]


def test_python_os_getenv_with_default():
    assert names('x = os.getenv("API_KEY", "fallback")', "app.py") == ["API_KEY"]


def test_python_os_environ_get():
    assert names('x = os.environ.get("API_KEY")', "app.py") == ["API_KEY"]


def test_python_os_environ_bracket():
    assert names('x = os.environ["API_KEY"]', "app.py") == ["API_KEY"]


def test_all_locations_kept():
    content = "a = process.env.X\nb = process.env.X\n"
    usages, _ = scanner.extract_usages(content, "app.js")
    assert [(u.name, u.line) for u in usages] == [("X", 1), ("X", 2)]


def test_empty_value_name_follows_regex():
    # A name must not start with a digit; nothing is captured.
    assert names("process.env.1BAD") == []


def test_ignore_marker_skips_line():
    content = "const a = process.env.REAL;\nconst b = process.env.NOPE; // envsanity-ignore\n"
    assert names(content) == ["REAL"]


def test_commented_code_still_counts():
    assert names("// const a = process.env.COMMENTED;") == ["COMMENTED"]


def test_dynamic_process_env():
    usages, dynamic = scanner.extract_usages("process.env[key]", "app.js")
    assert usages == []
    assert len(dynamic) == 1
    assert (dynamic[0].file, dynamic[0].line) == ("app.js", 1)


def test_dynamic_import_meta_env():
    _, dynamic = scanner.extract_usages("import.meta.env[key]", "app.js")
    assert len(dynamic) == 1


def test_dynamic_os_environ_bracket():
    _, dynamic = scanner.extract_usages("os.environ[name]", "app.py")
    assert len(dynamic) == 1


def test_dynamic_os_getenv_variable():
    _, dynamic = scanner.extract_usages("os.getenv(name)", "app.py")
    assert len(dynamic) == 1


def test_dynamic_os_environ_get_variable():
    _, dynamic = scanner.extract_usages("os.environ.get(name)", "app.py")
    assert len(dynamic) == 1


def test_string_bracket_is_not_dynamic():
    usages, dynamic = scanner.extract_usages('process.env["A"]', "app.js")
    assert [u.name for u in usages] == ["A"]
    assert dynamic == []


def test_dynamic_never_crashes():
    for content in ["process.env[", "process.env[]", "os.environ[", "os.getenv("]:
        scanner.extract_usages(content, "x")


def test_used_names_dedupes_preserving_order():
    content = "process.env.B\nprocess.env.A\nprocess.env.B\n"
    usages, _ = scanner.extract_usages(content, "app.js")
    assert scanner.used_names(usages) == ["B", "A"]


def test_parse_destructuring_units():
    assert scanner.parse_destructuring("A, B: renamed, C = 'x'") == ["A", "B", "C"]
    assert scanner.parse_destructuring("") == []
    assert scanner.parse_destructuring("...rest") == []
    assert scanner.parse_destructuring("A = 'a,b', B") == ["A", "B"]
