"""Rule-based extraction of (test, value, unit) measurements from report text."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from clinical_ner.dictionary import ParameterDictionary

# Every word of a name starts with a letter, so earlier result columns ("Vitamin D 73 83")
# are not swallowed into the name.
_NAME = r"(?P<name>[A-Za-z][\w\-\.]*(?: [A-Za-z][\w\-\.]*)*?)"
_VALUE = r"(?P<value>[<>]?\d+(?:\.\d+)?)"
_UNIT = r"(?P<unit>%|[A-Za-zµ0-9\^\*]+/[A-Za-z0-9\.]+(?:/[A-Za-z0-9\.]+)?|[A-Za-zµ]+)"
_RANGE = r"\((?P<range>[^)]*)\)"

# Report layouts seen in OCR output, tried in order on each line.
PATTERNS = [
    re.compile(rf"{_NAME}\s*{_RANGE}\s*{_UNIT}\s+{_VALUE}"),  # TSH (0.5-4.0) mIU/L 1.92
    re.compile(rf"{_NAME}\s*{_RANGE}\s*{_VALUE}\s*{_UNIT}"),  # TSH (0.5-4.0) 1.92 mIU/L
    re.compile(
        rf"{_NAME}\s+{_VALUE}(?:\s+[<>]?\d+(?:\.\d+)?)*\s*{_UNIT}(?=\s|$|\()"
    ),  # TSH 1.92 mIU/L (0.5-4.0)
    re.compile(rf"{_NAME}\s+{_UNIT}\s+{_VALUE}"),  # TSH mIU/L 1.92
]


# Units without a "/" that are still real units; anything else (e.g. "Plasma", "H")
# is OCR noise caught by the pattern and the match is rejected.
_PLAIN_UNITS = {"%", "fl", "pg", "u", "iu", "mmhg", "ratio", "sec", "s", "mm", "cells"}


def is_unit(unit: str) -> bool:
    return "/" in unit or unit.lower() in _PLAIN_UNITS


@dataclass(frozen=True)
class Measurement:
    parameter: str  # canonical abbreviation, e.g. "FERR"
    name: str  # name as written in the report, e.g. "Ferritin"
    value: str
    unit: str
    reference_range: str | None
    # Character offsets in the original text, used to build NER training labels.
    name_span: tuple[int, int]
    value_span: tuple[int, int]
    unit_span: tuple[int, int]

    def to_dict(self, spans: bool = False) -> dict:
        data = asdict(self)
        if not spans:
            for key in ("name_span", "value_span", "unit_span"):
                data.pop(key)
        return data


def extract_measurements(
    text: str, dictionary: ParameterDictionary, first_only: bool = True
) -> list[Measurement]:
    """Return measurements found in ``text``, in reading order.

    With ``first_only`` a test reported more than once (e.g. historical columns or
    repeated pages) keeps only its first value.
    """
    results: list[Measurement] = []
    seen: set[str] = set()
    offset = 0
    for line in text.splitlines(keepends=True):
        for measurement in _extract_line(line, offset, dictionary):
            if first_only and measurement.parameter in seen:
                continue
            seen.add(measurement.parameter)
            results.append(measurement)
        offset += len(line)
    return results


def _extract_line(line: str, offset: int, dictionary: ParameterDictionary):
    for pattern in PATTERNS:
        found = []
        for match in pattern.finditer(line):
            if not is_unit(match.group("unit")):
                continue
            # "<50" with no reference range next to it is a threshold in comment text
            # ("Vitamin D deficiency <50 nmol/L"), not a result.
            if match.group("value")[0] in "<>" and "range" not in pattern.groupindex:
                continue
            name_match = dictionary.match_name(match.group("name"))
            if name_match is None:
                continue
            name_start = match.start("name") + name_match.start
            name_end = match.start("name") + name_match.end
            found.append(
                Measurement(
                    parameter=name_match.canonical,
                    name=line[name_start:name_end],
                    value=match.group("value"),
                    unit=match.group("unit"),
                    reference_range=match.groupdict().get("range"),
                    name_span=(offset + name_start, offset + name_end),
                    value_span=(offset + match.start("value"), offset + match.end("value")),
                    unit_span=(offset + match.start("unit"), offset + match.end("unit")),
                )
            )
        if found:
            # The first layout that yields a known test wins for this line.
            return found
    return []
