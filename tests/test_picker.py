from __future__ import annotations

import os
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from cdf.errors import CdfError
from cdf.picker import FzfPicker

_FAKE_FZF = """#!/bin/sh
printf '%s\\n' "$@" > "$FAKE_FZF_DIR/args"
if [ -z "$FAKE_FZF_SKIP_STDIN" ]; then
  cat > "$FAKE_FZF_DIR/input"
fi
cat "$FAKE_FZF_DIR/output"
exit "$FAKE_FZF_CODE"
"""


class FakeFzf:
    def __init__(self, directory: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.directory = directory
        self._monkeypatch = monkeypatch
        self.respond(0, b"")

    def respond(self, code: int, output: bytes) -> None:
        (self.directory / "output").write_bytes(output)
        self._monkeypatch.setenv("FAKE_FZF_CODE", str(code))

    @property
    def args(self) -> list[str]:
        return (self.directory / "args").read_text().splitlines()

    @property
    def input(self) -> bytes:
        return (self.directory / "input").read_bytes()


@pytest.fixture
def fake_fzf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeFzf:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "fzf"
    script.write_text(_FAKE_FZF)
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_FZF_DIR", str(tmp_path))
    monkeypatch.delenv("FAKE_FZF_SKIP_STDIN", raising=False)
    return FakeFzf(tmp_path, monkeypatch)


def test_pick_returns_selected_path(tmp_path: Path, fake_fzf: FakeFzf) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    fake_fzf.respond(0, b"0\t" + os.fsencode(repo) + b"\0")

    result = FzfPicker().pick([repo], "my term")

    assert result == repo
    assert fake_fzf.args == [
        "--read0",
        "--print0",
        "--delimiter",
        "\t",
        "--with-nth",
        "2..",
        "--query",
        "my term",
    ]


def test_pick_streams_nul_delimited_input(tmp_path: Path, fake_fzf: FakeFzf) -> None:
    weird = tmp_path / "weird\nname"
    weird.mkdir()
    fake_fzf.respond(0, b"0\t" + os.fsencode(weird) + b"\0")

    result = FzfPicker().pick(iter([weird, Path("/normal")]), "")

    assert fake_fzf.input == b"0\t" + os.fsencode(weird) + b"\0" + b"1\t/normal\0"
    assert result == weird


def test_pick_handles_non_utf8_names(tmp_path: Path, fake_fzf: FakeFzf) -> None:
    raw_name = os.fsencode(tmp_path) + b"/bad\xff"
    os.mkdir(raw_name)
    undecodable = Path(os.fsdecode(raw_name))
    # Real fzf echoes the invalid byte back as U+FFFD; the index still maps it.
    mangled = os.fsencode(tmp_path) + b"/bad\xef\xbf\xbd"
    fake_fzf.respond(0, b"0\t" + mangled + b"\0")

    result = FzfPicker().pick([undecodable], "")

    assert fake_fzf.input == b"0\t" + raw_name + b"\0"
    assert result == undecodable


def test_pick_takes_last_entry_when_default_opts_add_query(
    tmp_path: Path, fake_fzf: FakeFzf
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    fake_fzf.respond(0, b"typed query\0" + b"0\t" + os.fsencode(repo) + b"\0")

    result = FzfPicker().pick([repo], "")

    assert result == repo


def test_pick_rejects_selection_that_no_longer_exists(fake_fzf: FakeFzf) -> None:
    fake_fzf.respond(0, b"0\t/definitely/not/here\0")

    with pytest.raises(CdfError, match="no longer exists"):
        FzfPicker().pick([Path("/definitely/not/here")], "")


@pytest.mark.parametrize("output", [b"garbage\0", b"7\t/x\0"])
def test_pick_rejects_unexpected_output(fake_fzf: FakeFzf, output: bytes) -> None:
    fake_fzf.respond(0, output)

    with pytest.raises(CdfError, match="unexpected output from fzf"):
        FzfPicker().pick([Path("/x")], "")


def test_pick_returns_none_on_empty_output(fake_fzf: FakeFzf) -> None:
    fake_fzf.respond(0, b"")

    assert FzfPicker().pick([Path("/x")], "") is None


@pytest.mark.parametrize("returncode", [1, 130])
def test_pick_returns_none_on_no_match_or_interrupt(fake_fzf: FakeFzf, returncode: int) -> None:
    fake_fzf.respond(returncode, b"")

    assert FzfPicker().pick([Path("/some/repo")], "term") is None


def test_pick_raises_on_fzf_error(fake_fzf: FakeFzf) -> None:
    fake_fzf.respond(2, b"")

    with pytest.raises(CdfError, match="status 2"):
        FzfPicker().pick([Path("/some/repo")], "term")


def test_pick_returns_without_waiting_for_the_walk(
    tmp_path: Path, fake_fzf: FakeFzf, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    fake_fzf.respond(0, b"0\t" + os.fsencode(repo) + b"\0")
    monkeypatch.setenv("FAKE_FZF_SKIP_STDIN", "1")
    release = threading.Event()

    def slow_walk() -> Iterator[Path]:
        yield repo
        release.wait(timeout=10)
        yield tmp_path / "late"

    try:
        result = FzfPicker().pick(slow_walk(), "")
    finally:
        release.set()

    assert result == repo


def test_pick_kills_fzf_when_interrupted(
    fake_fzf: FakeFzf, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_popen = subprocess.Popen
    started: list[subprocess.Popen[bytes]] = []

    class InterruptingStdout:
        def read(self) -> bytes:
            raise KeyboardInterrupt

    def popen(*args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
        process: subprocess.Popen[bytes] = real_popen(*args, **kwargs)
        assert process.stdout is not None
        process.stdout.close()
        process.stdout = InterruptingStdout()  # type: ignore[assignment]
        started.append(process)
        return process

    monkeypatch.setattr("cdf.picker.subprocess.Popen", popen)

    with pytest.raises(KeyboardInterrupt):
        FzfPicker().pick([Path("/x")], "")

    assert started[0].returncode is not None


def test_pick_raises_when_fzf_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cdf.picker.shutil.which", lambda name: None)

    with pytest.raises(CdfError, match="fzf"):
        FzfPicker().pick([Path("/some/repo")], "term")
