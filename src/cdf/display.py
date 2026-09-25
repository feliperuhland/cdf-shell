from __future__ import annotations

# Unicode category Cc is exactly C0 (U+0000-U+001F), DEL and C1 (U+007F-U+009F).
# Any of them in a directory name could move the cursor, retitle the window or
# worse when echoed to a terminal, so they are shown as "?" instead.
_CONTROL_CHARS = {code: "?" for code in (*range(0x00, 0x20), *range(0x7F, 0xA0))}


def printable(text: str) -> str:
    """Return `text` with terminal control characters replaced by "?".

    Undecodable bytes (surrogate escapes) are left alone, so
    `os.fsencode(printable(name))` still round-trips every other byte.
    """
    return text.translate(_CONTROL_CHARS)
