"""parse_to_numeric — convert OCR text to integer damage values.

The OCR output for a damage region may look like:
  - "12345"
  - "12,345"
  - "1234567"

For character list regions (Pattern 2) the output looks like:
  - "太郎: 12345 (67%)"
  - "次郎: 678 (12%)"
  Multiple lines may be present, one per character (up to 4).

This module extracts the first valid integer from such strings and applies
common OCR mis-recognition corrections (e.g. "O" → "0", "l" → "1").
"""
from __future__ import annotations

import logging
import re
from typing import NamedTuple

logger = logging.getLogger(__name__)

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

# Regex to match a character entry line: "太郎: 12345 (67%)"
# Captures: name, damage (with optional commas), percentage
_CHARACTER_ENTRY_RE = re.compile(
    r"([\u3000-\u9fff\uff00-\uffef\u3040-\u309f\u30a0-\u30ff]+)"  # name
    r"\s*[:：]\s*"                                                    # colon separator
    r"(\d[\d,]*)"                                                    # damage
    r"\s*[(\（]\s*"                                                   # open paren
    r"(\d+(?:\.\d+)?)\s*%"                                           # percentage
    r"\s*[)\）]"                                                      # close paren
)


class CharacterEntry(NamedTuple):
    """Parsed character damage entry from Pattern 2 text."""

    name: str
    damage: int
    percentage: float


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
        logger.debug("parse_to_numeric: no number found in %r (corrected: %r)", text, corrected)
        return None

    digits_only = match.group().replace(",", "")
    try:
        value = int(digits_only)
        logger.debug("parse_to_numeric: %r → %d", text, value)
        return value
    except ValueError:
        logger.debug("parse_to_numeric: int conversion failed for %r", digits_only)
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


def parse_character_entries(text: str) -> list[CharacterEntry]:
    """Parse character damage entries from multi-line OCR text.

    Expects lines such as::

        太郎: 12345 (67%)
        次郎: 678 (12%)

    Parameters
    ----------
    text:
        Raw multi-line OCR text from the character list region.

    Returns
    -------
    list[CharacterEntry]
        Parsed entries (up to 4).  Empty list when no valid entries found.
    """
    if not text or not text.strip():
        return []

    corrected = _apply_corrections(text)
    entries: list[CharacterEntry] = []

    for match in _CHARACTER_ENTRY_RE.finditer(corrected):
        name = match.group(1)
        damage_str = match.group(2).replace(",", "")
        pct_str = match.group(3)
        try:
            damage = int(damage_str)
            percentage = float(pct_str)
            entries.append(CharacterEntry(name=name, damage=damage, percentage=percentage))
        except ValueError:
            continue

    return entries[:4]  # at most 4 characters
