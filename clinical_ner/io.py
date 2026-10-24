"""Reading report text."""

from pathlib import Path


def read_report(path: str | Path) -> str:
    """Read an OCR text file, keeping line breaks (they separate tests)."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return text.replace("\r\n", "\n").replace("|", " ")
