from __future__ import annotations

from pathlib import Path

import pytest

from cdf.walker import FilesystemWalker


@pytest.fixture
def walker() -> FilesystemWalker:
    return FilesystemWalker()


def _make_repo(path: Path) -> None:
    path.mkdir(parents=True)
    (path / ".git").mkdir()


def test_git_only_finds_repo_roots(tmp_path: Path, walker: FilesystemWalker) -> None:
    _make_repo(tmp_path / "projects" / "alpha")
    (tmp_path / "projects" / "not-a-repo").mkdir(parents=True)

    result = set(walker.walk(tmp_path, git_only=True, include_hidden=False))

    assert result == {tmp_path / "projects" / "alpha"}


def test_git_only_stops_at_repo_boundary(tmp_path: Path, walker: FilesystemWalker) -> None:
    outer = tmp_path / "outer"
    _make_repo(outer)
    _make_repo(outer / "vendored" / "inner")

    result = set(walker.walk(tmp_path, git_only=True, include_hidden=False))

    assert result == {outer}


def test_git_only_skips_hidden_repo_by_default(tmp_path: Path, walker: FilesystemWalker) -> None:
    _make_repo(tmp_path / ".dotfiles")

    result = set(walker.walk(tmp_path, git_only=True, include_hidden=False))

    assert result == set()


def test_all_flag_includes_hidden_repo(tmp_path: Path, walker: FilesystemWalker) -> None:
    _make_repo(tmp_path / ".dotfiles")

    result = set(walker.walk(tmp_path, git_only=True, include_hidden=True))

    assert result == {tmp_path / ".dotfiles"}


def test_no_git_lists_every_directory(tmp_path: Path, walker: FilesystemWalker) -> None:
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "c").mkdir()

    result = set(walker.walk(tmp_path, git_only=False, include_hidden=False))

    assert result == {tmp_path / "a", tmp_path / "a" / "b", tmp_path / "c"}


def test_no_git_skips_hidden_dirs_by_default(tmp_path: Path, walker: FilesystemWalker) -> None:
    (tmp_path / ".hidden" / "inner").mkdir(parents=True)
    (tmp_path / "visible").mkdir()

    result = set(walker.walk(tmp_path, git_only=False, include_hidden=False))

    assert result == {tmp_path / "visible"}


def test_git_worktree_file_is_detected(tmp_path: Path, walker: FilesystemWalker) -> None:
    repo = tmp_path / "worktree-repo"
    repo.mkdir()
    (repo / ".git").write_text("gitdir: /elsewhere\n")

    result = set(walker.walk(tmp_path, git_only=True, include_hidden=False))

    assert result == {repo}
