from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path

from cdf.app import resolve


class FakeWalker:
    def __init__(self, candidates: list[Path]) -> None:
        self._candidates = candidates
        self.calls: list[tuple[Path, bool, bool]] = []

    def walk(self, root: Path, *, git_only: bool, include_hidden: bool) -> Iterator[Path]:
        self.calls.append((root, git_only, include_hidden))
        yield from self._candidates


class FakePicker:
    def __init__(self, selection: Path | None) -> None:
        self._selection = selection
        self.calls: list[tuple[Sequence[Path], str]] = []

    def pick(self, candidates: Sequence[Path], term: str) -> Path | None:
        self.calls.append((candidates, term))
        return self._selection


def test_resolve_wires_walker_and_picker(tmp_path: Path) -> None:
    candidate = tmp_path / "repo"
    walker = FakeWalker([candidate])
    picker = FakePicker(candidate)

    result = resolve(
        "term",
        tmp_path,
        git_only=True,
        include_hidden=False,
        walker=walker,
        picker=picker,
    )

    assert result == candidate
    assert walker.calls == [(tmp_path, True, False)]
    assert picker.calls == [([candidate], "term")]


def test_resolve_short_circuits_on_no_candidates(tmp_path: Path) -> None:
    walker = FakeWalker([])
    picker = FakePicker(tmp_path)

    result = resolve(
        "term",
        tmp_path,
        git_only=True,
        include_hidden=False,
        walker=walker,
        picker=picker,
    )

    assert result is None
    assert picker.calls == []
