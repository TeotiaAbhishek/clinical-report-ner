import random

from clinical_ner.synthetic import generate_report


def test_label_spans_match_text():
    rng = random.Random(1)
    for _ in range(20):
        text, labels = generate_report(rng)
        for label in labels:
            assert text[slice(*label.value_span)] == label.value
            assert text[slice(*label.unit_span)] == label.unit


def test_reports_are_reproducible():
    assert generate_report(random.Random(3)) == generate_report(random.Random(3))
