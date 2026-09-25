# cdf

`cdf` ("cd" + "find") interactively searches the directory tree below your
current working directory for a term, and `cd`s into the directory you
select.

- Search scope is always the current working directory downward — never the
  whole filesystem, never a cached/global index.
- By default it only matches git repository roots and stops descending once
  it finds one (pass `--no-git` to walk every directory instead).
- Selection is powered by [`fzf`](https://github.com/junegunn/fzf), which
  must be on `PATH`.

## Install

### From source

```sh
uv sync
```

This installs the `cdf` console script into `.venv/bin/`.

### Arch Linux

A `PKGBUILD` is provided at the repo root, sourcing the tarball from this
repo's own `v*.*.*` git tags:

```sh
makepkg -si
```

`cdf` (the binary) only *resolves* a path and prints it to stdout — a Python
process can't change its parent shell's working directory. Source the shell
wrapper so the `cdf` command actually `cd`s for you:

```sh
# ~/.bashrc / ~/.zshrc
source /path/to/cdf/shell/cdf.sh
```

This defines a shell function also named `cdf`, which takes priority over
the binary in your shell and calls it internally via `command cdf`. Make
sure the `cdf` binary itself is on `PATH` (e.g. via `uv tool install .`, or
by adding `.venv/bin` to `PATH`).

## Usage

```sh
cdf [term] [-p/--path ROOT] [--git/--no-git] [-a/--all|--no-all] [-c/--config FILE]
```

| Flag | Default | Meaning |
|---|---|---|
| `term` | `""` | initial fuzzy filter text passed to `fzf` |
| `-p, --path` | cwd | root to search from |
| `--git` / `--no-git` | `--git` | only match git repository roots |
| `-a, --all` / `--no-all` | `--no-all` | include hidden/dot directories |
| `-c, --config` | `$CDF_CONFIG_PATH`, else first existing default | config file path |

Run `cdf --help` for the full reference, or `cdf --version` (the shell
function special-cases `--help`/`-h`/`--version` to pass them straight
through instead of attempting to `cd` into their output).

### Exit codes

- `0` — a directory was selected
- `1` — nothing was selected (cancelled in `fzf`, or no candidates found)
- `2` — an error occurred (message on stderr) — e.g. `fzf` missing, or a bad
  config file

## Config file

The config file path is resolved in this order:

1. `-c/--config FILE` — must exist, or it's an error.
2. `$CDF_CONFIG_PATH` — must exist, or it's an error.
3. Otherwise, the first of these that exists (silently skipped if none do):
   `~/cdf.conf`, then `~/.config/cdf/cdf.conf`.

All keys are optional (TOML syntax, despite the `.conf` extension):

```toml
path = "~/projects"  # string, expanded with ~
git = true            # boolean
hidden = false        # boolean
```

Unknown keys, and values of the wrong type (e.g. `git = "false"` instead of
`git = false`), are rejected with an error, to catch typos early.

## Development

```sh
make run    # uv run python -m cdf
make test   # pytest + ruff + ruff-format + mypy (strict) + coverage, gated at 100%
make lint   # uv run ruff check .
```
