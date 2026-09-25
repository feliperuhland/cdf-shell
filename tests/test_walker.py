from __future__ import annotations

import os
from pathlib import Path

import pytest

from cdf.errors import CdfError
from cdf.walker import FilesystemWalker

requires_non_root = pytest.mark.skipif(
    os.geteuid() == 0, reason="root ignores permission bits, so chmod 000 has no effect"
)


@pytest.fixture
def walker() -> FilesystemWalker:
    return FilesystemWalker()


def _make_repo(path: Path) -> None:
    path.mkdir(parents=True)
    (path / ".git").mkdir()


def test_git_only_finds_repo_roots(tmp_path: Path, walker: FilesystemWalker) -> None:
    _make_repo(tmp_path / "projects" / "alpha")
    (tmp_path / "projects" / "not-a-repo").mkdir(parents=True)

    result = set(walker.walk(tmp_path, git_only=True, include_hidden=False, ignore=()))

    assert result == {tmp_path / "projects" / "alpha"}


def test_git_only_stops_at_repo_boundary(tmp_path: Path, walker: FilesystemWalker) -> None:
    outer = tmp_path / "outer"
    _make_repo(outer)
    _make_repo(outer / "vendored" / "inner")

    result = set(walker.walk(tmp_path, git_only=True, include_hidden=False, ignore=()))

    assert result == {outer}


def test_git_only_skips_hidden_repo_by_default(tmp_path: Path, walker: FilesystemWalker) -> None:
    _make_repo(tmp_path / ".dotfiles")

    result = set(walker.walk(tmp_path, git_only=True, include_hidden=False, ignore=()))

    assert result == set()


def test_all_flag_includes_hidden_repo(tmp_path: Path, walker: FilesystemWalker) -> None:
    _make_repo(tmp_path / ".dotfiles")

    result = set(walker.walk(tmp_path, git_only=True, include_hidden=True, ignore=()))

    assert result == {tmp_path / ".dotfiles"}


def test_no_git_lists_every_directory(tmp_path: Path, walker: FilesystemWalker) -> None:
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "c").mkdir()

    result = set(walker.walk(tmp_path, git_only=False, include_hidden=False, ignore=()))

    assert result == {tmp_path / "a", tmp_path / "a" / "b", tmp_path / "c"}


def test_no_git_skips_hidden_dirs_by_default(tmp_path: Path, walker: FilesystemWalker) -> None:
    (tmp_path / ".hidden" / "inner").mkdir(parents=True)
    (tmp_path / "visible").mkdir()

    result = set(walker.walk(tmp_path, git_only=False, include_hidden=False, ignore=()))

    assert result == {tmp_path / "visible"}


def test_git_worktree_file_is_detected(tmp_path: Path, walker: FilesystemWalker) -> None:
    repo = tmp_path / "worktree-repo"
    repo.mkdir()
    (repo / ".git").write_text("gitdir: /elsewhere\n")

    result = set(walker.walk(tmp_path, git_only=True, include_hidden=False, ignore=()))

    assert result == {repo}


def test_never_descends_into_dot_git(tmp_path: Path, walker: FilesystemWalker) -> None:
    repo = tmp_path / "repo"
    (repo / ".git" / "objects" / "ab").mkdir(parents=True)

    result = set(walker.walk(tmp_path, git_only=False, include_hidden=True, ignore=()))

    assert result == {repo}


def test_ignore_patterns_prune_matching_dirs(tmp_path: Path, walker: FilesystemWalker) -> None:
    (tmp_path / "app" / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "build-output").mkdir()
    (tmp_path / "src").mkdir()

    result = set(
        walker.walk(
            tmp_path, git_only=False, include_hidden=False, ignore=("node_modules", "build-*")
        )
    )

    assert result == {tmp_path / "app", tmp_path / "src"}


def test_ignored_repo_is_not_listed(tmp_path: Path, walker: FilesystemWalker) -> None:
    _make_repo(tmp_path / "node_modules" / "dep")
    _make_repo(tmp_path / "mine")

    result = set(
        walker.walk(tmp_path, git_only=True, include_hidden=False, ignore=("node_modules",))
    )

    assert result == {tmp_path / "mine"}


def test_results_are_sorted_per_level(tmp_path: Path, walker: FilesystemWalker) -> None:
    for name in ("c", "a", "b"):
        (tmp_path / name).mkdir()

    result = list(walker.walk(tmp_path, git_only=False, include_hidden=False, ignore=()))

    assert result == [tmp_path / "a", tmp_path / "b", tmp_path / "c"]


@requires_non_root
def test_unreadable_root_raises(tmp_path: Path, walker: FilesystemWalker) -> None:
    root = tmp_path / "locked"
    _make_repo(root / "repo")
    root.chmod(0o000)

    try:
        with pytest.raises(CdfError, match="cannot read search root"):
            list(walker.walk(root, git_only=True, include_hidden=False, ignore=()))
    finally:
        root.chmod(0o755)


@requires_non_root
def test_unreadable_subdirectory_is_skipped(tmp_path: Path, walker: FilesystemWalker) -> None:
    locked = tmp_path / "locked"
    locked.mkdir()
    (tmp_path / "open").mkdir()
    locked.chmod(0o000)

    try:
        result = set(walker.walk(tmp_path, git_only=False, include_hidden=False, ignore=()))
    finally:
        locked.chmod(0o755)

    # It could not be cd'd into anyway (no search permission), so it is left out.
    assert result == {tmp_path / "open"}


def test_symlinked_directory_is_listed_but_not_entered(
    tmp_path: Path, walker: FilesystemWalker
) -> None:
    (tmp_path / "real" / "inner").mkdir(parents=True)
    root = tmp_path / "root"
    root.mkdir()
    (root / "linked").symlink_to(tmp_path / "real")

    result = set(walker.walk(root, git_only=False, include_hidden=False, ignore=()))

    assert result == {root / "linked"}


def test_symlinked_repo_is_listed_in_git_mode(tmp_path: Path, walker: FilesystemWalker) -> None:
    _make_repo(tmp_path / "real-repo")
    (tmp_path / "real-plain").mkdir()
    root = tmp_path / "root"
    root.mkdir()
    (root / "repo-link").symlink_to(tmp_path / "real-repo")
    (root / "plain-link").symlink_to(tmp_path / "real-plain")

    result = set(walker.walk(root, git_only=True, include_hidden=False, ignore=()))

    assert result == {root / "repo-link"}


def test_symlink_loop_is_listed_once(tmp_path: Path, walker: FilesystemWalker) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "back").symlink_to(tmp_path)

    result = list(walker.walk(tmp_path, git_only=False, include_hidden=False, ignore=()))

    assert result == [tmp_path / "sub", tmp_path / "sub" / "back"]


def test_symlinks_inside_a_repo_are_not_listed_in_git_mode(
    tmp_path: Path, walker: FilesystemWalker
) -> None:
    _make_repo(tmp_path / "other")
    repo = tmp_path / "repo"
    _make_repo(repo)
    (repo / "link").symlink_to(tmp_path / "other")

    result = set(walker.walk(tmp_path, git_only=True, include_hidden=False, ignore=()))

    assert result == {tmp_path / "other", repo}


def test_hidden_and_ignored_symlinks_are_pruned(tmp_path: Path, walker: FilesystemWalker) -> None:
    (tmp_path / "real").mkdir()
    root = tmp_path / "root"
    root.mkdir()
    (root / ".hidden-link").symlink_to(tmp_path / "real")
    (root / "node_modules").symlink_to(tmp_path / "real")

    result = set(walker.walk(root, git_only=False, include_hidden=False, ignore=("node_modules",)))

    assert result == set()


@requires_non_root
def test_symlink_into_unsearchable_directory_is_skipped(
    tmp_path: Path, walker: FilesystemWalker
) -> None:
    locked = tmp_path / "locked"
    (locked / "target").mkdir(parents=True)
    root = tmp_path / "root"
    (root / "ok").mkdir(parents=True)
    (root / "link").symlink_to(locked / "target")
    locked.chmod(0o000)

    try:
        result = set(walker.walk(root, git_only=False, include_hidden=False, ignore=()))
    finally:
        locked.chmod(0o755)

    assert result == {root / "ok"}


@requires_non_root
def test_git_mode_symlink_to_unsearchable_directory_is_skipped(
    tmp_path: Path, walker: FilesystemWalker
) -> None:
    # Like /usr/lib/ssl/private: the link target itself can be stat'ed, but
    # checking for a .git inside it raises PermissionError (Python 3.12+).
    private = tmp_path / "private"
    private.mkdir()
    root = tmp_path / "root"
    _make_repo(root / "repo")
    (root / "link").symlink_to(private)
    private.chmod(0o000)

    try:
        result = set(walker.walk(root, git_only=True, include_hidden=False, ignore=()))
    finally:
        private.chmod(0o755)

    assert result == {root / "repo"}
