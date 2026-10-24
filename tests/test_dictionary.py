import pytest

from clinical_ner import ParameterDictionary


@pytest.fixture(scope="module")
def dictionary():
    return ParameterDictionary.load()


@pytest.mark.parametrize(
    "term, expected",
    [
        ("TSH", "TSH"),
        ("ferritin", "FERR"),
        ("Total Cholesterol", "CHOL"),
        ("Ferritn", "FERR"),  # OCR typo, fuzzy match
        ("creatinine", "CREA"),  # also listed under CREAN; primary synonym wins
        ("hematocrit", "HCT"),
    ],
)
def test_canonical(dictionary, term, expected):
    assert dictionary.canonical(term) == expected


@pytest.mark.parametrize("term", ["", "Specimen Type", "Fasting", "abc"])
def test_unknown_terms(dictionary, term):
    assert dictionary.canonical(term) is None


def test_match_name_skips_leading_noise(dictionary):
    match = dictionary.match_name("Normal Ferritin")
    assert match.canonical == "FERR"
    assert "Normal Ferritin"[match.start : match.end] == "Ferritin"
