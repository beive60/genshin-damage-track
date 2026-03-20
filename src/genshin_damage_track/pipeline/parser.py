"""parse_to_numeric — convert OCR text to integer damage values.

The OCR output for a damage region may look like:
  - "12345"
  - "12,345"
  - "1234567"

This module extracts the first valid integer from such strings and applies
common OCR mis-recognition corrections (e.g. "O" -> "0", "l" -> "1").
"""
from __future__ import annotations

import logging
import re

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
        logger.debug("parse_to_numeric: %r -> %d", text, value)
        return value
    except ValueError:
        logger.debug("parse_to_numeric: int conversion failed for %r", digits_only)
        return None
