import pytest

from nodes.cid_decode_unicode_escapes import CidDecodeUnicodeEscapes


@pytest.mark.parametrize(
    "value, expected",
    [
        ("", ""),
        ("café, 日本語 😀\n", "café, 日本語 😀\n"),
        (r"caf\u00e9 et déjà vu \u00E0", "café et déjà vu à"),
        (r"\U0001F600 \U0010FFFF", "😀 \U0010ffff"),
        (r"\uD83d\udE00 \uD800\uDC00", "😀 \U00010000"),
        (r"\u00 \uZZZZ \U0001F6 \U00110000", r"\u00 \uZZZZ \U0001F6 \U00110000"),
        (
            r"\uD800\u00e9\uDC00 \U0000D800",
            r"\uD800" + "é" + r"\uDC00 \U0000D800",
        ),
        (
            r"\\u00e9 \\\u00e9 \\uD83D\uDE00",
            r"\\u00e9 \\" + "é " + r"\\uD83D\uDE00",
        ),
        (
            r"\n \t \xE9 \N{LATIN SMALL LETTER E WITH ACUTE}",
            r"\n \t \xE9 \N{LATIN SMALL LETTER E WITH ACUTE}",
        ),
        (r"\u005cu00e9", r"\u00e9"),
    ],
)
def test_decode_unicode_escapes(value, expected):
    assert CidDecodeUnicodeEscapes().main(value) == (expected,)
