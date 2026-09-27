from __future__ import annotations

import os
from collections.abc import Collection, Iterable, Iterator
from pathlib import Path

import pytest

from cdf.app import resolve
from cdf.errors import NoCandidatesError


class FakeWalker:
    def __init__(self, candidates: list[Path]) -> None:
        self._candidates = candidates
        self.calls: list[tuple[Path, bool, bool, Collection[str]]] = []

    def walk(
        self, root: Path, *, git_only: bool, include_hidden: bool, ignore: Collection[str]
    ) -> Iterator[Path]:
        self.calls.append((root, git_only, include_hidden, ignore))
        yield from self._candidates


class FakePicker:
    def __init__(self, selection: Path | None) -> None:
        self._selection = selection
        self.calls: list[tuple[list[Path], str]] = []

    def pick(self, candidates: Iterable[Path], term: str) -> Path | None:
        self.calls.append((list(candidates), term))
        return self._selection


def test_resolve_wires_walker_and_picker(tmp_path: Path) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    walker = FakeWalker([first, second])
    picker = FakePicker(second)

    result = resolve(
        "term",
        tmp_path,
        git_only=True,
        include_hidden=False,
        ignore=("node_modules",),
        walker=walker,
        picker=picker,
    )

    assert result == second
    assert walker.calls == [(tmp_path, True, False, ("node_modules",))]
    assert picker.calls == [([first, second], "term")]


@pytest.mark.parametrize(
    ("git_only", "message"),
    [(True, r"no git repositories found .*\(try --no-git\)"), (False, "no directories found")],
)
def test_resolve_raises_on_no_candidates(tmp_path: Path, git_only: bool, message: str) -> None:
    picker = FakePicker(tmp_path)

    with pytest.raises(NoCandidatesError, match=message):
        resolve(
            "term",
            tmp_path,
            git_only=git_only,
            include_hidden=False,
            ignore=(),
            walker=FakeWalker([]),
            picker=picker,
        )

    assert picker.calls == []


def test_no_candidates_inside_a_repo_says_so(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / "src").mkdir()

    with pytest.raises(NoCandidatesError, match=r"inside the repository .*repo \(try --no-git\)"):
        resolve(
            "",
            repo / "src",
            git_only=True,
            include_hidden=False,
            ignore=(),
            walker=FakeWalker([]),
            picker=FakePicker(None),
        )


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores permission bits")
def test_no_candidates_under_unsearchable_ancestor_still_reports(tmp_path: Path) -> None:
    locked = tmp_path / "locked"
    root = locked / "sub"
    root.mkdir(parents=True)
    locked.chmod(0o000)

    try:
        with pytest.raises(NoCandidatesError, match="no git repositories found"):
            resolve(
                "",
                root,
                git_only=True,
                include_hidden=False,
                ignore=(),
                walker=FakeWalker([]),
                picker=FakePicker(None),
            )
    finally:
        locked.chmod(0o755)
