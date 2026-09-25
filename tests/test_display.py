from __future__ import annotations

import os

from cdf.display import printable


def test_replaces_c0_del_and_c1_controls() -> None:
    assert printable("a\x00b\nc\td\x1b[31me\x7ff\x9bg") == "a?b?c?d?[31me?f?g"


def test_keeps_regular_unicode() -> None:
    assert printable("café/日本/ñ\u00a0x") == "café/日本/ñ\u00a0x"


def test_undecodable_bytes_still_round_trip() -> None:
    raw = b"/tmp/bad\xff\x1bname"
    assert os.fsencode(printable(os.fsdecode(raw))) == b"/tmp/bad\xff?name"
