# cdf shell integration for fish. Load it with:
#   command cdf --init fish | source
function cdf --description 'Interactively find a directory below here and cd into it'
    for arg in $argv
        switch $arg
            case --help -h --version --init '--init=*'
                command cdf $argv
                return
        end
    end
    set -l lines (command cdf $argv)
    or return
    # Command substitution splits on newlines; rejoin so a name containing one survives.
    set -l target (string join \n -- $lines | string collect)
    test -n "$target"; and cd -- $target
end
