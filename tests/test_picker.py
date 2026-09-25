from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cdf.errors import CdfError
from cdf.picker import FzfPicker


def _completed(
    returncode: int, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["fzf"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_pick_returns_selected_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cdf.picker.shutil.which", lambda name: "/usr/bin/fzf")
    monkeypatch.setattr(
        "cdf.picker.subprocess.run",
        lambda *args, **kwargs: _completed(0, stdout="/some/repo\0"),
    )

    result = FzfPicker().pick([Path("/some/repo")], "term")

    assert result == Path("/some/repo")


def test_pick_uses_nul_delimited_io(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cdf.picker.shutil.which", lambda name: "/usr/bin/fzf")
    captured_args: list[str] = []
    captured_input: list[str] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured_args.extend(args)
        captured_input.append(str(kwargs["input"]))
        return _completed(0, stdout="line\n1\0")

    monkeypatch.setattr("cdf.picker.subprocess.run", fake_run)

    result = FzfPicker().pick([Path("weird\nname"), Path("/normal")], "term")

    assert "--read0" in captured_args
    assert "--print0" in captured_args
    assert captured_input == ["weird\nname\0/normal"]
    assert result == Path("line\n1")


@pytest.mark.parametrize("returncode", [1, 130])
def test_pick_returns_none_on_no_match_or_interrupt(
    monkeypatch: pytest.MonkeyPatch, returncode: int
) -> None:
    monkeypatch.setattr("cdf.picker.shutil.which", lambda name: "/usr/bin/fzf")
    monkeypatch.setattr(
        "cdf.picker.subprocess.run",
        lambda *args, **kwargs: _completed(returncode),
    )

    result = FzfPicker().pick([Path("/some/repo")], "term")

    assert result is None


def test_pick_raises_on_fzf_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cdf.picker.shutil.which", lambda name: "/usr/bin/fzf")
    monkeypatch.setattr(
        "cdf.picker.subprocess.run",
        lambda *args, **kwargs: _completed(2, stderr="boom"),
    )

    with pytest.raises(CdfError, match="boom"):
        FzfPicker().pick([Path("/some/repo")], "term")


def test_pick_raises_when_fzf_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cdf.picker.shutil.which", lambda name: None)

    with pytest.raises(CdfError, match="fzf"):
        FzfPicker().pick([Path("/some/repo")], "term")
