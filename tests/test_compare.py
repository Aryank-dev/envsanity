from envsanity import compare


def test_missing_only():
    missing, unused = compare.compare(["A", "B"], ["A"], [])
    assert missing == ["B"]
    assert unused == []


def test_possibly_unused_only():
    missing, unused = compare.compare(["A"], ["A", "B"], [])
    assert missing == []
    assert unused == ["B"]


def test_both():
    missing, unused = compare.compare(["A", "C"], ["A", "B"], [])
    assert missing == ["C"]
    assert unused == ["B"]


def test_builtin_ignore():
    missing, _unused = compare.compare(["PATH", "HOME", "NEW_VAR"], ["PATH"], [])
    assert missing == ["NEW_VAR"]


def test_builtin_prefixes():
    used = ["GITHUB_TOKEN", "RUNNER_OS", "npm_config_x", "YARN_CACHE", "MY_VAR"]
    missing, _unused = compare.compare(used, [], [])
    assert missing == ["MY_VAR"]


def test_extra_ignores():
    missing, unused = compare.compare(["A", "B"], ["A"], ["B"])
    assert missing == []
    assert unused == []


def test_extra_ignore_on_documented_side():
    # A documented, ignored variable must not appear as possibly unused.
    _missing, unused = compare.compare([], ["IGNORED"], ["IGNORED"])
    assert unused == []


def test_results_sorted_and_unique():
    missing, unused = compare.compare(["B", "A", "B"], ["D", "C", "D"], [])
    assert missing == ["A", "B"]
    assert unused == ["C", "D"]


def test_should_ignore():
    assert compare.should_ignore("PATH") is True
    assert compare.should_ignore("GITHUB_SHA") is True
    assert compare.should_ignore("CUSTOM", ["CUSTOM"]) is True
    assert compare.should_ignore("CUSTOM", []) is False
