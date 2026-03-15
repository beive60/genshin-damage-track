"""parse_to_numeric — convert OCR text to integer damage values.

The OCR output for a damage region may look like:
  - "12345"
  - "12,345"
  - "太郎: 12345 (67%)"
  - "胡桃 123,456"

This module extracts the first valid integer from such strings and applies
common OCR mis-recognition corrections (e.g. "O" → "0", "l" → "1").
"""
from __future__ import annotations

import re

# OCR mis-recognition correction table.
# Only uppercase look-alike characters are corrected; lowercase letters such
# as "o" are intentionally excluded to avoid false positives in text strings
# that happen to contain those letters (e.g. "no result").
_OCR_CORRECTIONS: dict[str, str] = {
    "O": "0",
    "l": "1",
    "I": "1",
    "S": "5",
    "B": "8",
    "Z": "2",
    "G": "6",
}

# Regex to match a sequence of digits (with optional comma separators)
_NUMBER_RE = re.compile(r"\d[\d,]*")

# Regex to match a CJK character-based name before a colon or space
# (used for character name extraction in Pattern 2).
# The range \u3000-\u9fff covers CJK Unified Ideographs, Hiragana, Katakana, etc.
_NAME_RE = re.compile(r"^([\u3000-\u9fff\uff00-\uffef\u3040-\u309f\u30a0-\u30ff]+)")


def _apply_corrections(text: str) -> str:
    """Replace known OCR mis-recognised characters."""
    return "".join(_OCR_CORRECTIONS.get(ch, ch) for ch in text)


def parse_to_numeric(text: str) -> int | None:
    """Extract the first integer from *text*, or ``None`` when not found.

    Parameters
    ----------
    text:
        Raw string returned by OCR.

    Returns
    -------
    int | None
        Parsed integer value, or ``None`` if no numeric content is found.
    """
    if not text or not text.strip():
        return None

    corrected = _apply_corrections(text)
    match = _NUMBER_RE.search(corrected)
    if match is None:
        return None

    digits_only = match.group().replace(",", "")
    try:
        return int(digits_only)
    except ValueError:
        return None


def parse_character_name(text: str) -> str | None:
    """Extract a CJK character name from the beginning of *text*.

    Parameters
    ----------
    text:
        Raw string returned by OCR (e.g. ``"胡桃 123,456"``).

    Returns
    -------
    str | None
        The extracted name, or ``None`` when the text does not start with a
        recognisable CJK name segment.
    """
    if not text or not text.strip():
        return None

    match = _NAME_RE.match(text.strip())
    if match:
        return match.group(1)
    return None
