# cdf shell integration for bash and zsh. Load it with:
#   eval "$(command cdf --init bash)"   # or: --init zsh
cdf() {
  # Look at each argument on its own (not "$*", which depends on IFS and would
  # also match a quoted search term like "foo -h bar"); stop at "--", after
  # which everything is search text.
  local arg
  for arg in "$@"; do
    case $arg in
      --) break ;;
      --help | -h | --version | --init | --init=*)
        command cdf "$@"
        return
        ;;
    esac
  done
  local target
  # $(...) strips *all* trailing newlines, including ones that are part of
  # the directory name, so append a "." and then remove it plus the single
  # newline cdf prints after the path.
  target="$(command cdf "$@" && printf .)" || return
  target="${target%.}"
  target="${target%?}"
  # Only ever cd into a real directory; anything else (e.g. help text from
  # combined short flags like -ah) is printed instead.
  if [ -d "$target" ]; then
    # \cd: bash/zsh expand aliases when this function is defined, so a plain
    # `cd` would run e.g. `alias cd=z`. A cd *function* (hooks) still applies.
    \cd -- "$target"
  elif [ -n "$target" ]; then
    printf '%s\n' "$target"
  fi
}
