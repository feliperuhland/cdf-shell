# cdf shell integration for fish. Load it with:
#   command cdf --init fish | source
function cdf --description 'Interactively find a directory below here and cd into it'
    for arg in $argv
        switch $arg
            case '--'
                # Everything after it is search text.
                break
            case --help -h --version --init '--init=*'
                command cdf $argv
                return
        end
    end
    set -l lines (command cdf $argv)
    or return
    # Command substitution splits on newlines and drops only the final one
    # (the one cdf prints). Rejoin with variable operations: `string join` and
    # `string collect` would add or trim newlines that belong to the name.
    set -l target $lines[1]
    for line in $lines[2..-1]
        set target "$target"\n"$line"
    end
    # Only ever cd into a real directory; anything else (e.g. help text from
    # combined short flags like -ah) is printed instead.
    if test -d "$target"
        cd -- $target
    else if test -n "$target"
        printf '%s\n' $target
    end
end
