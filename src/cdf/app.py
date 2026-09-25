from __future__ import annotations

import itertools
from collections.abc import Collection
from pathlib import Path

from cdf.errors import NoCandidatesError
from cdf.picker import Picker
from cdf.walker import DirectoryWalker


def resolve(
    term: str,
    root: Path,
    *,
    git_only: bool,
    include_hidden: bool,
    ignore: Collection[str],
    walker: DirectoryWalker,
    picker: Picker,
) -> Path | None:
    candidates = walker.walk(root, git_only=git_only, include_hidden=include_hidden, ignore=ignore)
    # Peek at the first candidate so an empty tree gets a clear message instead
    # of an empty picker; the rest keeps streaming lazily into the picker.
    first = next(candidates, None)
    if first is None:
        raise NoCandidatesError(_no_candidates_message(root, git_only=git_only))
    return picker.pick(itertools.chain([first], candidates), term)


def _enclosing_repo(root: Path) -> Path | None:
    return next((path for path in (root, *root.parents) if (path / ".git").exists()), None)


def _no_candidates_message(root: Path, *, git_only: bool) -> str:
    if not git_only:
        return f"no directories found under {root}"
    # The walk skips the root itself, so running inside a repo only finds
    # repos nested in it; say so rather than implying there are none at all.
    repo = _enclosing_repo(root)
    if repo is not None:
        return (
            f"no nested git repositories found under {root}, which is inside the "
            f"repository {repo} (try --no-git)"
        )
    return f"no git repositories found under {root} (try --no-git)"
