import random

import pytest

from clinical_ner import ParameterDictionary, extract_measurements
from clinical_ner.synthetic import generate_report


@pytest.fixture(scope="module")
def dictionary():
    return ParameterDictionary.load()


@pytest.mark.parametrize(
    "line, expected",
    [
        ("TSH (0.5-4.0) mIU/L 1.92", ("TSH", "1.92", "mIU/L", "0.5-4.0")),
        ("TSH (0.5-4.0) 1.92 mIU/L", ("TSH", "1.92", "mIU/L", "0.5-4.0")),
        ("Ferritin 85 ug/L (30-300)", ("FERR", "85", "ug/L", None)),
        ("HbA1c 7.20 % 4.2-5.7", ("HBA1C", "7.20", "%", None)),
        ("Platelets x10^9/L 230", ("PLAT", "230", "x10^9/L", None)),
        ("Vitamin D 73 83 nmol/L", ("vitD", "73", "nmol/L", None)),  # first of several columns
        ("eGFR (>60) mL/min 88", ("EGFR", "88", "mL/min", ">60")),
    ],
)
def test_layouts(dictionary, line, expected):
    (m,) = extract_measurements(line + "\n", dictionary)
    assert (m.parameter, m.value, m.unit, m.reference_range) == expected


@pytest.mark.parametrize(
    "line",
    [
        "Specimen Type: Serum",
        "D.O.B: 01/01/1970 Gender: F",
        "Vitamin D deficiency <50 nmol/L",  # threshold in a comment, not a result
        "Average Estimated Glucose 254 Plasma",  # "Plasma" is not a unit
    ],
)
def test_ignores_non_results(dictionary, line):
    assert extract_measurements(line + "\n", dictionary) == []


def test_spans_point_at_source_text(dictionary):
    text = "THYROID PROFILE\nFT4 (10-20) pmol/L 14\n"
    (m,) = extract_measurements(text, dictionary)
    assert text[slice(*m.name_span)] == "FT4"
    assert text[slice(*m.value_span)] == "14"
    assert text[slice(*m.unit_span)] == "pmol/L"


def test_first_only_keeps_first_occurrence(dictionary):
    text = "TSH (0.5-4.0) mIU/L 1.1\nTSH (0.5-4.0) mIU/L 2.2\n"
    assert [m.value for m in extract_measurements(text, dictionary)] == ["1.1"]
    assert [m.value for m in extract_measurements(text, dictionary, first_only=False)] == ["1.1", "2.2"]


def test_recall_on_synthetic_reports(dictionary):
    rng = random.Random(7)
    found = expected = 0
    for _ in range(50):
        text, labels = generate_report(rng)
        got = {(m.parameter, m.value) for m in extract_measurements(text, dictionary, first_only=False)}
        expected += len(labels)
        found += sum((label.parameter, label.value) in got for label in labels)
    assert found / expected > 0.95
