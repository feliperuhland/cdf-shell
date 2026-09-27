# cdf

`cdf` ("cd" + "find") interactively searches the directory tree below your
current working directory for a term, and `cd`s into the directory you
select.

- Search scope is always the current working directory downward — never the
  whole filesystem, never a cached/global index.
- By default it only matches git repository roots and stops descending once
  it finds one (pass `--no-git` to walk every directory instead).
- Symlinked directories are listed (in git mode, only if they point at a
  repository) but never descended into, so symlink loops can't hang the walk.
- Selection is powered by [`fzf`](https://github.com/junegunn/fzf) 0.44 or
  newer, which must be on `PATH`. Your `FZF_DEFAULT_OPTS` (theme, layout,
  `--print-query`, `--accept-nth`, ...) are respected.
- Directory names are shown with terminal control characters (escape
  sequences, newlines, tabs) replaced by `?`, so a hostile name in a cloned
  repo can't mess with your terminal; the directory you pick is still the
  exact one on disk.

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
process can't change its parent shell's working directory. Load the shell
integration so the `cdf` command actually `cd`s for you:

```sh
# ~/.bashrc
eval "$(command cdf --init bash)"
# ~/.zshrc
eval "$(command cdf --init zsh)"
```

```fish
# ~/.config/fish/config.fish
command cdf --init fish | source
```

This defines a shell function also named `cdf`, which takes priority over
the binary in your shell and calls it internally via `command cdf`. Make
sure the `cdf` binary itself is on `PATH` (e.g. via `uv tool install .`, or
by adding `.venv/bin` to `PATH`).

## Usage

```sh
cdf [term ...] [-p/--path ROOT] [--git/--no-git] [-a/--all|--no-all] [-c/--config FILE]
cdf --init {bash,zsh,fish}
```

| Flag | Default | Meaning |
|---|---|---|
| `term ...` | `""` | initial fuzzy filter text passed to `fzf` (several words are joined with spaces) |
| `-p, --path` | cwd | root to search from |
| `--git` / `--no-git` | `--git` | only match git repository roots |
| `-a, --all` / `--no-all` | `--no-all` | include hidden/dot directories |
| `-c, --config` | `$CDF_CONFIG_PATH`, else first existing default | config file path |
| `--init SHELL` | | print the shell integration for `bash`, `zsh` or `fish` and exit |

Run `cdf --help` for the full reference, or `cdf --version` (the shell
function special-cases `--help`/`-h`/`--version`/`--init` to pass them straight
through instead of attempting to `cd` into their output).

### Exit codes

- `0` — a directory was selected
- `1` — nothing was selected (cancelled in `fzf`, or no candidates found, in
  which case a hint is printed on stderr)
- `2` — an error occurred (message on stderr) — e.g. `fzf` missing, an
  unreadable search root, or a bad config file
- `130` — interrupted with Ctrl-C

## Config file

The config file path is resolved in this order:

1. `-c/--config FILE` — must exist, or it's an error.
2. `$CDF_CONFIG_PATH` — must exist, or it's an error.
3. Otherwise, the first of these that exists (silently skipped if none do):
   `$XDG_CONFIG_HOME/cdf/cdf.conf` (default `~/.config/cdf/cdf.conf`), then
   `~/cdf.conf`.

All keys are optional (TOML syntax, despite the `.conf` extension):

```toml
path = "~/projects"  # string, expanded with ~; relative paths are relative to this file
git = true            # boolean
hidden = false        # boolean
ignore = ["node_modules", "__pycache__", ".venv"]  # glob patterns of directory names to skip
```

`ignore` replaces the default list shown above (set `ignore = []` to skip
nothing). Patterns match one directory name at a time, so they can't contain
`/`. `.git` directories are never descended into regardless.

Unknown keys, and values of the wrong type (e.g. `git = "false"` instead of
`git = false`), are rejected with an error, to catch typos early.

## Development

```sh
make run    # uv run python -m cdf
make test   # pytest + ruff + ruff-format + mypy (strict) + coverage, gated at 100%
make lint   # uv run ruff check .
make build  # sdist + wheel, with the build backend pinned by hash (build-constraints.txt)
make build-constraints  # re-lock build-constraints.txt after editing build-constraints.in
```

Supported Python: 3.11 through 3.14; CI runs the full `make test` gate on
each, with the bash/zsh/fish wrapper tests running against pinned zsh 5.9
and fish 4.9.3.
