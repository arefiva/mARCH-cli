"""
Unit tests for FileTaskExecutor covering US-004 (multi-match edit rejection).
"""

import pytest

from mARCH.tasks.file_executor import FileTaskExecutor


@pytest.fixture
def executor():
    return FileTaskExecutor()


# ---------------------------------------------------------------------------
# US-004: Reject ambiguous multi-match file edits
# ---------------------------------------------------------------------------


def test_single_match_edit_succeeds(tmp_path, executor):
    """Editing a file where old_str appears exactly once must succeed."""
    f = tmp_path / "file.txt"
    f.write_text("line one\nline two\nline three\n")

    executor._edit_file_sync(str(f), "line two", "line 2")

    assert f.read_text() == "line one\nline 2\nline three\n"


def test_multi_match_edit_raises_with_count(tmp_path, executor):
    """Editing a file where old_str appears 3 times must raise ValueError with count."""
    f = tmp_path / "file.txt"
    f.write_text("foo\nfoo\nfoo\n")

    with pytest.raises(ValueError, match="3"):
        executor._edit_file_sync(str(f), "foo", "bar")


def test_absent_string_raises_value_error(tmp_path, executor):
    """Editing a file where old_str is absent must raise ValueError."""
    f = tmp_path / "file.txt"
    f.write_text("hello world\n")

    with pytest.raises(ValueError):
        executor._edit_file_sync(str(f), "not present", "replacement")


def test_substring_counted_independently(tmp_path, executor):
    """A substring of a longer repeated pattern must still be counted correctly."""
    f = tmp_path / "file.txt"
    # "foo" appears 3 times (once standalone, once as part of "foobar", once as "foo")
    f.write_text("foo\nfoobar\nfoo\n")

    with pytest.raises(ValueError, match="3"):
        executor._edit_file_sync(str(f), "foo", "baz")
