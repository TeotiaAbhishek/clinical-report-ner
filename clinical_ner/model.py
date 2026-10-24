"""spaCy NER model for test names, values and units, trained on synthetic reports."""

from __future__ import annotations

import bisect
import random
from pathlib import Path

import spacy
from spacy.language import Language
from spacy.training import Example

from clinical_ner.dictionary import ParameterDictionary
from clinical_ner.extract import Measurement, is_unit
from clinical_ner.synthetic import generate_report

LABELS = ("PARAMETER", "VALUE", "UNIT")


def make_examples(nlp: Language, n_reports: int, seed: int) -> list[Example]:
    rng = random.Random(seed)
    examples = []
    for _ in range(n_reports):
        text, measurements = generate_report(rng)
        doc = nlp.make_doc(text)
        entities = []
        for m in measurements:
            for span, label in ((m.name_span, "PARAMETER"), (m.value_span, "VALUE"), (m.unit_span, "UNIT")):
                entities.append((*span, label))
        examples.append(Example.from_dict(doc, {"entities": entities}))
    return examples


def train(n_reports: int = 400, epochs: int = 15, seed: int = 13) -> Language:
    nlp = spacy.blank("en")
    ner = nlp.add_pipe("ner")
    for label in LABELS:
        ner.add_label(label)
    examples = make_examples(nlp, n_reports, seed)
    optimizer = nlp.initialize(lambda: examples)
    rng = random.Random(seed)
    for epoch in range(epochs):
        rng.shuffle(examples)
        losses: dict[str, float] = {}
        for batch in spacy.util.minibatch(examples, size=16):
            nlp.update(batch, sgd=optimizer, drop=0.2, losses=losses)
        print(f"epoch {epoch + 1}/{epochs}  ner loss {losses['ner']:.1f}")
    return nlp


def load(path: str | Path) -> Language:
    return spacy.load(path)


def extract_with_model(
    nlp: Language, text: str, dictionary: ParameterDictionary, first_only: bool = True
) -> list[Measurement]:
    """Run NER, then pair each PARAMETER with the nearest VALUE and UNIT on its line."""
    doc = nlp(text)
    results: list[Measurement] = []
    seen: set[str] = set()
    line_starts = _line_starts(text)
    by_line: dict[int, list] = {}
    for ent in doc.ents:
        by_line.setdefault(_line_of(ent.start_char, line_starts), []).append(ent)
    for line in sorted(by_line):
        ents = by_line[line]
        for i, ent in enumerate(ents):
            if ent.label_ != "PARAMETER":
                continue
            canonical = dictionary.canonical(ent.text)
            if canonical is None or (first_only and canonical in seen):
                continue
            following = ents[i + 1 :]
            value = next((e for e in following if e.label_ == "VALUE"), None)
            unit = next((e for e in following if e.label_ == "UNIT" and is_unit(e.text)), None)
            if value is None or unit is None:
                continue
            seen.add(canonical)
            results.append(
                Measurement(
                    parameter=canonical,
                    name=ent.text,
                    value=value.text,
                    unit=unit.text,
                    reference_range=None,
                    name_span=(ent.start_char, ent.end_char),
                    value_span=(value.start_char, value.end_char),
                    unit_span=(unit.start_char, unit.end_char),
                )
            )
    return results


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _line_of(char: int, starts: list[int]) -> int:
    return bisect.bisect_right(starts, char) - 1
