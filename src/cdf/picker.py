from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import threading
from collections.abc import Iterable
from pathlib import Path
from typing import IO, Protocol

from cdf.errors import CdfError

_EXIT_MATCHED = 0
_EXIT_NO_MATCH = 1
_EXIT_INTERRUPTED = 130


class Picker(Protocol):
    def pick(self, candidates: Iterable[Path], term: str) -> Path | None: ...


def _feed(stdin: IO[bytes], candidates: Iterable[Path], seen: list[Path]) -> None:
    # Each entry is "<index>\t<path>". fzf only shows/matches the path (see
    # --with-nth) but echoes the whole entry back, so the index maps the pick to
    # the exact original Path even when fzf can't round-trip its bytes (fzf
    # replaces non-UTF-8 bytes in names). fzf closes its end as soon as the
    # user picks something; a still-running walk then hits a broken pipe,
    # which just means "stop feeding".
    with stdin, contextlib.suppress(BrokenPipeError):
        for candidate in candidates:
            seen.append(candidate)
            stdin.write(b"%d\t%s\0" % (len(seen) - 1, os.fsencode(candidate)))


def _parse_selection(output: bytes, seen: list[Path]) -> Path | None:
    # FZF_DEFAULT_OPTS may add --print-query/--expect/--multi, which put extra
    # NUL-delimited entries in the output. The selection is the last entry.
    entries = [entry for entry in output.split(b"\0") if entry]
    if not entries:
        return None
    index, _, _ = entries[-1].partition(b"\t")
    try:
        selected = seen[int(index)]
    except (ValueError, IndexError) as exc:
        raise CdfError(f"unexpected output from fzf: {entries[-1]!r}") from exc
    if not selected.is_dir():
        raise CdfError(f"selected directory no longer exists: {selected}")
    return selected


class FzfPicker:
    def pick(self, candidates: Iterable[Path], term: str) -> Path | None:
        if shutil.which("fzf") is None:
            raise CdfError("fzf not found on PATH. Install it: https://github.com/junegunn/fzf")

        # Unbuffered stdin so each candidate reaches fzf as soon as the walker
        # finds it; stderr is inherited so fzf's own error messages show up.
        process = subprocess.Popen(
            [
                "fzf",
                "--read0",
                "--print0",
                "--delimiter",
                "\t",
                "--with-nth",
                "2..",
                "--query",
                term,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            bufsize=0,
        )
        assert process.stdin is not None and process.stdout is not None
        seen: list[Path] = []
        # Daemon thread: once fzf exits we return without waiting for the walk.
        feeder = threading.Thread(target=_feed, args=(process.stdin, candidates, seen), daemon=True)
        feeder.start()

        try:
            output = process.stdout.read()
            returncode = process.wait()
        except BaseException:
            process.kill()
            process.wait()
            raise

        if returncode == _EXIT_MATCHED:
            return _parse_selection(output, seen)
        if returncode in (_EXIT_NO_MATCH, _EXIT_INTERRUPTED):
            return None
        raise CdfError(f"fzf exited with status {returncode}")
