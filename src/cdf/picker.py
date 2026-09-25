from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from cdf.errors import CdfError

_EXIT_MATCHED = 0
_EXIT_NO_MATCH = 1
_EXIT_INTERRUPTED = 130


class Picker(Protocol):
    def pick(self, candidates: Sequence[Path], term: str) -> Path | None: ...


class FzfPicker:
    def pick(self, candidates: Sequence[Path], term: str) -> Path | None:
        if shutil.which("fzf") is None:
            raise CdfError("fzf not found on PATH. Install it: https://github.com/junegunn/fzf")

        result = subprocess.run(
            ["fzf", "--read0", "--print0", "--query", term],
            input="\0".join(str(candidate) for candidate in candidates),
            capture_output=True,
            text=True,
        )

        if result.returncode == _EXIT_MATCHED:
            return Path(result.stdout.rstrip("\0"))
        if result.returncode in (_EXIT_NO_MATCH, _EXIT_INTERRUPTED):
            return None
        raise CdfError(result.stderr.strip() or f"fzf exited with status {result.returncode}")
