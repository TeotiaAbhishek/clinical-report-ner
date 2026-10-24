"""Precision, recall and F1 on (test, value, unit) triples."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass
class Scores:
    true_positives: int = 0
    predicted: int = 0
    expected: int = 0

    def add(self, predicted: Iterable[tuple], expected: Iterable[tuple]) -> None:
        predicted, expected = set(predicted), set(expected)
        self.true_positives += len(predicted & expected)
        self.predicted += len(predicted)
        self.expected += len(expected)

    @property
    def precision(self) -> float:
        return self.true_positives / self.predicted if self.predicted else 0.0

    @property
    def recall(self) -> float:
        return self.true_positives / self.expected if self.expected else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0

    def as_dict(self) -> dict:
        return {
            "precision": round(self.precision, 3),
            "recall": round(self.recall, 3),
            "f1": round(self.f1, 3),
        }


def triple(parameter: str, value: str, unit: str) -> tuple[str, str, str]:
    return parameter, value, unit.lower()
