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
        (r"\n\t\r \xE9 \N{LATIN SMALL LETTER E WITH ACUTE}", "\n\t\r é é"),
        (r"\u005cu00e9", r"\u00e9"),
        ("&#039; &#x27; &#X27;", "' ' '"),
        ("&apos; &eacute; &amp; &NotEqualTilde;", "' é & ≂̸"),
        (r"caf\u00e9 &amp; th&#233; &#x1F600;", "café & thé 😀"),
        (
            "&notaref; &apos &#039 &#x27 &#; &#x; &#xG; &#-1;",
            "&notaref; &apos &#039 &#x27 &#; &#x; &#xG; &#-1;",
        ),
        ("&#128; &#0; &#xD800; &#1114112; &#x110000;", "€ � � � �"),
        ("&#" + "0" * 5000 + "39;", "'"),
        ("&#" + "9" * 5000 + "; &#x" + "F" * 5000 + ";", "� �"),
        (r"&amp;#039; &amp;apos; \u0026apos; &#92;u00e9", r"&#039; &apos; &apos; \u00e9"),
        (r"\x414 \N{latin small letter e with acute}", "A4 é"),
        (r"\u{1F600}\u{0}\u{10FFFF}", "😀\0\U0010ffff"),
        (r"\u{" + "0" * 5000 + "E9}", "é"),
        (
            r"\u{} \u{z} \u{123 \u{D800} \u{110000} \u{1000000} \xE \xG0 \N{UNKNOWN NAME}",
            r"\u{} \u{z} \u{123 \u{D800} \u{110000} \u{1000000} \xE \xG0 \N{UNKNOWN NAME}",
        ),
        (r"\\n \\xE9 \\N{LF} \\u{1F600} \q \b", r"\\n \\xE9 \\N{LF} \\u{1F600} \q \b"),
        ("%C3%a9+%2b%20%F0%9F%98%80", "é++ 😀"),
        ("%A %G0 %41%FF %C3%28 %ED%A0%80 %41", "%A %G0 %41%FF %C3%28 %ED%A0%80 A"),
        (r"\xE9%20&amp;\t\u{1F600}", "é &\t😀"),
        (r"\x5cu00e9 %26amp%3B %5Cn &percnt;41", r"\u00e9 &amp; \n %41"),
    ],
)
def test_decode_unicode_escapes(value, expected):
    assert CidDecodeUnicodeEscapes().main(value) == (expected,)
