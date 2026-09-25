# cdf shell integration for bash and zsh. Load it with:
#   eval "$(command cdf --init bash)"   # or: --init zsh
cdf() {
  case " $* " in
    *" --help "* | *" -h "* | *" --version "* | *" --init "* | *" --init="*)
      command cdf "$@"
      return
      ;;
  esac
  local target
  target="$(command cdf "$@")" || return
  # Only ever cd into a real directory; anything else (e.g. help text from
  # combined short flags like -ah) is printed instead.
  if [ -d "$target" ]; then
    cd -- "$target"
  elif [ -n "$target" ]; then
    printf '%s\n' "$target"
  fi
}
