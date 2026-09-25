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
  target="$(command cdf "$@")" && [ -n "$target" ] && cd -- "$target"
}
