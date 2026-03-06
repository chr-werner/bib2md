import os
import textwrap
import pytest
import yaml

from bib2md import (
    clean_yaml,
    find_md_files,
    remove_curly_braces,
    remove_file,
    update,
    update_md,
)


# ---------------------------------------------------------------------------
# remove_curly_braces
# ---------------------------------------------------------------------------

class TestRemoveCurlyBraces:
    def test_plain_string(self):
        assert remove_curly_braces("hello") == "hello"

    def test_string_with_braces(self):
        assert remove_curly_braces("{hello}") == "hello"

    def test_nested_braces(self):
        assert remove_curly_braces("{{nested}}") == "nested"

    def test_dict(self):
        result = remove_curly_braces({"title": "{Some Title}", "year": "2024"})
        assert result == {"title": "Some Title", "year": "2024"}

    def test_list(self):
        result = remove_curly_braces(["{a}", "b", "{c}"])
        assert result == ["a", "b", "c"]

    def test_nested_dict(self):
        data = {"entries": {"key": {"title": "{Deep {Title}}"}}}
        result = remove_curly_braces(data)
        assert result["entries"]["key"]["title"] == "Deep Title"

    def test_non_string_passthrough(self):
        assert remove_curly_braces(42) == 42
        assert remove_curly_braces(None) is None


# ---------------------------------------------------------------------------
# clean_yaml
# ---------------------------------------------------------------------------

def _write_yaml(tmp_path, data) -> str:
    path = str(tmp_path / "test.yaml")
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    return path


def _sample_data(extra_keys: dict | None = None) -> dict:
    entry = {
        "title": "{Some Title}",
        "author": [
            {"first": "Jane", "last": "Doe"},
            {"last": "Smith"},
        ],
        "groups": "tag1, tag2",
        "keywords": "kw1, kw2",
        "comment": "irrelevant",
        "file": "/path/to/file.pdf",
        "readstatus": "read",
        "priority": "high",
        "type": "article",
    }
    if extra_keys:
        entry.update(extra_keys)
    return {"entries": {"doe2024": entry}}


class TestCleanYaml:
    def test_removes_unwanted_keys(self, tmp_path):
        path = _write_yaml(tmp_path, _sample_data())
        clean_yaml(path)
        data = yaml.safe_load(open(path))
        entry = data["entries"]["doe2024"]
        for key in ("comment", "file", "readstatus", "priority", "type"):
            assert key not in entry, f"Expected '{key}' to be removed"

    def test_author_converted_to_authors(self, tmp_path):
        path = _write_yaml(tmp_path, _sample_data())
        clean_yaml(path)
        data = yaml.safe_load(open(path))
        entry = data["entries"]["doe2024"]
        assert "author" not in entry
        assert entry["authors"] == ["[[Jane Doe]]", "[[Smith]]"]

    def test_author_without_first_name(self, tmp_path):
        data = {"entries": {"x": {"author": [{"last": "Einstein"}]}}}
        path = _write_yaml(tmp_path, data)
        clean_yaml(path)
        result = yaml.safe_load(open(path))
        assert result["entries"]["x"]["authors"] == ["[[Einstein]]"]

    def test_groups_to_tags(self, tmp_path):
        path = _write_yaml(tmp_path, _sample_data())
        clean_yaml(path)
        data = yaml.safe_load(open(path))
        assert data["entries"]["doe2024"]["tags"] == ["tag1", "tag2"]

    def test_keywords_to_list(self, tmp_path):
        path = _write_yaml(tmp_path, _sample_data())
        clean_yaml(path)
        data = yaml.safe_load(open(path))
        assert data["entries"]["doe2024"]["keywords"] == ["kw1", "kw2"]

    def test_keywords_strips_whitespace(self, tmp_path):
        data = {"entries": {"x": {"keywords": "foo,  bar ,baz"}}}
        path = _write_yaml(tmp_path, data)
        clean_yaml(path)
        result = yaml.safe_load(open(path))
        assert result["entries"]["x"]["keywords"] == ["foo", "bar", "baz"]

    def test_curly_braces_removed(self, tmp_path):
        path = _write_yaml(tmp_path, _sample_data())
        clean_yaml(path)
        data = yaml.safe_load(open(path))
        assert data["entries"]["doe2024"]["title"] == "Some Title"

    def test_entry_without_optional_fields(self, tmp_path):
        data = {"entries": {"x": {"title": "Minimal"}}}
        path = _write_yaml(tmp_path, data)
        clean_yaml(path)
        result = yaml.safe_load(open(path))
        assert result["entries"]["x"]["title"] == "Minimal"


# ---------------------------------------------------------------------------
# update_md
# ---------------------------------------------------------------------------

def _make_md(tmp_path, name: str, frontmatter: str = "", body: str = "") -> str:
    path = str(tmp_path / name)
    content = f"---\n{frontmatter}\n---\n{body}" if frontmatter else f"---\n---\n{body}"
    with open(path, "w") as f:
        f.write(content)
    return path


class TestUpdateMd:
    def test_writes_new_keys(self, tmp_path):
        path = _make_md(tmp_path, "paper.md")
        update_md(path, {"title": "My Paper", "year": 2024})
        content = open(path).read()
        assert "title: My Paper" in content
        assert "year: 2024" in content

    def test_overwrites_scalar(self, tmp_path):
        path = _make_md(tmp_path, "paper.md", "title: Old Title\n")
        update_md(path, {"title": "New Title"})
        content = open(path).read()
        assert "New Title" in content
        assert "Old Title" not in content

    def test_appends_unique_list_entries(self, tmp_path):
        path = _make_md(tmp_path, "paper.md", "tags:\n- existing\n")
        update_md(path, {"tags": ["existing", "new"]})
        content = open(path).read()
        assert content.count("existing") == 1
        assert "new" in content

    def test_does_not_duplicate_list_entries(self, tmp_path):
        path = _make_md(tmp_path, "paper.md", "tags:\n- foo\n- bar\n")
        update_md(path, {"tags": ["foo", "bar"]})
        content = open(path).read()
        assert content.count("foo") == 1

    def test_body_preserved(self, tmp_path):
        path = _make_md(tmp_path, "paper.md", "title: t\n", body="Some body text.\n")
        update_md(path, {"year": 2020})
        content = open(path).read()
        assert "Some body text." in content

    def test_invalid_file_does_not_raise(self, tmp_path):
        path = str(tmp_path / "bad.md")
        with open(path, "w") as f:
            f.write("not valid frontmatter at all {{{{")
        # Should not raise — errors are caught and printed
        update_md(path, {"title": "x"})


# ---------------------------------------------------------------------------
# find_md_files
# ---------------------------------------------------------------------------

class TestFindMdFiles:
    def test_finds_md_files(self, tmp_path):
        (tmp_path / "a.md").write_text("")
        (tmp_path / "b.txt").write_text("")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "c.md").write_text("")
        result = find_md_files(str(tmp_path))
        names = {os.path.basename(p) for p in result}
        assert names == {"a.md", "c.md"}

    def test_ignores_non_md(self, tmp_path):
        (tmp_path / "notes.txt").write_text("")
        (tmp_path / "data.yaml").write_text("")
        assert find_md_files(str(tmp_path)) == []

    def test_empty_directory(self, tmp_path):
        assert find_md_files(str(tmp_path)) == []


# ---------------------------------------------------------------------------
# update (integration)
# ---------------------------------------------------------------------------

class TestUpdate:
    def test_updates_matching_file(self, tmp_path):
        path = _make_md(tmp_path, "@doe2024.md")
        yaml_data = {"entries": {"doe2024": {"title": "Great Paper"}}}
        update([path], yaml_data)
        assert "Great Paper" in open(path).read()

    def test_strips_at_prefix_and_lowercases(self, tmp_path):
        path = _make_md(tmp_path, "@Doe2024.md")
        yaml_data = {"entries": {"doe2024": {"title": "Great Paper"}}}
        update([path], yaml_data)
        assert "Great Paper" in open(path).read()

    def test_skips_unmatched_file(self, tmp_path):
        path = _make_md(tmp_path, "unknown.md", "title: original\n")
        yaml_data = {"entries": {"doe2024": {"title": "Other"}}}
        update([path], yaml_data)
        # File should be unchanged
        assert "original" in open(path).read()


# ---------------------------------------------------------------------------
# remove_file
# ---------------------------------------------------------------------------

class TestRemoveFile:
    def test_removes_existing_file(self, tmp_path):
        path = str(tmp_path / "temp.yaml")
        open(path, "w").close()
        remove_file(path)
        assert not os.path.exists(path)

    def test_handles_missing_file_gracefully(self, tmp_path):
        path = str(tmp_path / "nonexistent.yaml")
        remove_file(path)  # Should not raise
