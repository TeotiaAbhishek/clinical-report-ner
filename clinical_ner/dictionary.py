"""Lookup of pathology test names, abbreviations and synonyms."""

from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent / "resources" / "parameters.json"


@dataclass(frozen=True)
class NameMatch:
    canonical: str  # abbreviation from the dictionary, e.g. "FERR"
    start: int  # character offsets of the matched words within the searched string
    end: int


class ParameterDictionary:
    """Maps every abbreviation and synonym (case-insensitive) to its abbreviation."""

    def __init__(self, entries: list[dict], fuzzy_cutoff: float = 0.88):
        self.fuzzy_cutoff = fuzzy_cutoff
        # Some synonyms appear under several abbreviations ("creatinine" under CREA and
        # CREAN). Resolve them by priority: the abbreviation itself, then an entry's
        # first (primary) synonym, then any other synonym; ties keep the first entry.
        best: dict[str, tuple[int, str]] = {}
        for entry in entries:
            abbreviation = entry["Abbreviation"].strip()
            if not abbreviation:
                continue
            synonyms = entry.get("Synonyms", [])
            for priority, term in [
                (0, abbreviation),
                *((1 if i == 0 else 2, s) for i, s in enumerate(synonyms)),
            ]:
                term = term.strip().lower()
                if term and (term not in best or priority < best[term][0]):
                    best[term] = (priority, abbreviation)
        self._lookup = {term: abbreviation for term, (_, abbreviation) in best.items()}
        self._terms = list(self._lookup)

    @classmethod
    def load(cls, path: str | Path = DEFAULT_PATH, **kwargs) -> ParameterDictionary:
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f), **kwargs)

    def __len__(self) -> int:
        return len(self._lookup)

    def canonical(self, term: str) -> str | None:
        """Exact (case-insensitive) lookup, then a fuzzy match to tolerate OCR typos."""
        term = term.strip().lower()
        if not term:
            return None
        if term in self._lookup:
            return self._lookup[term]
        # Very short strings fuzzy-match almost anything, so require an exact hit.
        if len(term) < 5:
            return None
        close = difflib.get_close_matches(term, self._terms, n=1, cutoff=self.fuzzy_cutoff)
        return self._lookup[close[0]] if close else None

    def match_name(self, text: str) -> NameMatch | None:
        """Find the test name at the end of ``text``.

        OCR lines often carry noise before the test name ("| HbA1c", "Normal Ferritin"),
        so this tries the longest trailing run of words first and shrinks it.
        """
        words = [(w.start(), w.end()) for w in _iter_words(text)]
        for i in range(len(words)):
            start, end = words[i][0], words[-1][1]
            canonical = self.canonical(text[start:end])
            if canonical:
                return NameMatch(canonical, start, end)
        return None


def _iter_words(text: str):
    return re.finditer(r"\S+", text)
