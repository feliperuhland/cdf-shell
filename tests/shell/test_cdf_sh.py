from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from cdf.cli import shell_init_script

# cdf.sh is shared by bash and zsh, so every test runs under both.
_SHELLS = {"bash": ["bash", "--norc"], "zsh": ["zsh", "--no-rcs"]}

# Stands in for the real `cdf` binary: prints $FAKE_CDF_OUT, exits $FAKE_CDF_CODE.
_FAKE_CDF = """#!/bin/sh
printf '%s\\n' "$FAKE_CDF_OUT"
exit "${FAKE_CDF_CODE:-0}"
"""


@pytest.fixture(
    params=[
        pytest.param(
            name,
            marks=pytest.mark.skipif(shutil.which(name) is None, reason=f"{name} not installed"),
        )
        for name in _SHELLS
    ]
)
def shell(request: pytest.FixtureRequest) -> str:
    name: str = request.param
    return name


def _run_wrapper(
    shell: str, tmp_path: Path, args: str, *, out: str, code: int = 0
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    fake = bin_dir / "cdf"
    fake.write_text(_FAKE_CDF)
    fake.chmod(0o755)
    wrapper = tmp_path / "cdf.sh"
    wrapper.write_text(shell_init_script(shell))
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "FAKE_CDF_OUT": out,
        "FAKE_CDF_CODE": str(code),
        "CDPATH": str(tmp_path / "cdpath"),
    }
    script = f'source "{wrapper}"; cdf {args}; echo "status=$?"; pwd'
    return subprocess.run(
        [*_SHELLS[shell], "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )


def test_cds_into_selected_directory(shell: str, tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()

    result = _run_wrapper(shell, tmp_path, "term", out=str(target))

    assert result.stdout.splitlines() == ["status=0", str(target)]


def test_target_containing_newline_survives(shell: str, tmp_path: Path) -> None:
    target = tmp_path / "a\nb"
    target.mkdir()

    result = _run_wrapper(shell, tmp_path, "", out=str(target))

    assert result.stdout == f"status=0\n{target}\n"


def test_target_starting_with_dash_is_not_an_option(shell: str, tmp_path: Path) -> None:
    (tmp_path / "-L").mkdir()

    result = _run_wrapper(shell, tmp_path, "", out="-L")

    assert result.stdout.splitlines() == ["status=0", str(tmp_path / "-L")]


def test_stays_put_when_nothing_selected(shell: str, tmp_path: Path) -> None:
    result = _run_wrapper(shell, tmp_path, "", out="", code=1)

    assert result.stdout.splitlines() == ["status=1", str(tmp_path)]


@pytest.mark.parametrize("flag", ["--help", "-h", "--version", "--init bash", "--init=zsh"])
def test_informational_flags_pass_through(shell: str, tmp_path: Path, flag: str) -> None:
    result = _run_wrapper(shell, tmp_path, flag, out="some text\nmore text")

    assert result.stdout.splitlines() == ["some text", "more text", "status=0", str(tmp_path)]
    assert result.stderr == ""
