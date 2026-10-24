import pytest

from clinical_ner import ParameterDictionary
from clinical_ner.model import extract_with_model, train


@pytest.mark.slow
def test_small_model_learns_layouts():
    nlp = train(n_reports=150, epochs=8, seed=1)
    found = extract_with_model(nlp, "Ferritin (30-300) ug/L 85\nTSH 1.92 mIU/L\n", ParameterDictionary.load())
    assert {(m.parameter, m.value) for m in found} >= {("FERR", "85")}
