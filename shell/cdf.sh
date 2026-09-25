cdf() {
  case " $* " in
    *" --help "* | *" -h "* | *" --version "*)
      command cdf "$@"
      return
      ;;
  esac
  local target
  target="$(command cdf "$@")" && [ -n "$target" ] && cd "$target"
}
