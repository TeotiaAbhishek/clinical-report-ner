"""Synthetic pathology reports with known labels, for training and testing.

Real reports contain patient health information, so this repo ships none. These
reports mimic the layouts seen in OCR output, with several spellings per test.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# (abbreviation in data/parameters.json, names as labs print them, unit, low, high, decimals)
TESTS = [
    ("TSH", ["TSH", "Thyroid Stimulating Hormone"], "mIU/L", 0.5, 4.0, 2),
    ("FT4", ["FT4", "Free T4", "Free Thyroxine"], "pmol/L", 10, 20, 0),
    ("FT3", ["FT3", "Free T3"], "pmol/L", 3.5, 6.0, 1),
    ("FERR", ["Ferritin", "Serum Ferritin"], "ug/L", 30, 300, 0),
    ("TFER", ["Transferrin"], "g/L", 2.0, 3.6, 1),
    ("HBA1C", ["HbA1c", "Glycated Hemoglobin"], "%", 4.2, 5.7, 1),
    ("CHOL", ["Total Cholesterol", "Cholesterol Total"], "mmol/L", 3.0, 5.5, 1),
    ("TRIGL", ["Triglycerides"], "mmol/L", 0.5, 2.0, 1),
    ("HDLC", ["HDL Cholesterol", "HDL-C"], "mmol/L", 1.0, 2.2, 1),
    ("LDLC", ["LDL Cholesterol", "LDL-C"], "mmol/L", 1.5, 3.5, 1),
    ("UREA", ["Urea"], "mmol/L", 3.0, 8.0, 1),
    ("CREA", ["Creatinine", "Serum Creatinine"], "umol/L", 45, 90, 0),
    ("EGFR", ["eGFR"], "mL/min", 60, 120, 0),
    ("ALT", ["ALT", "Alanine Transaminase"], "U/L", 5, 35, 0),
    ("AST", ["AST", "Aspartate Aminotransferase"], "U/L", 5, 35, 0),
    ("ALP", ["ALP", "Alkaline Phosphatase"], "U/L", 30, 110, 0),
    ("GGT", ["GGT", "Gamma GT"], "U/L", 5, 40, 0),
    ("ALB", ["Albumin"], "g/L", 35, 50, 0),
    ("CRP", ["CRP", "C-Reactive Protein"], "mg/L", 0, 5, 1),
    ("HGB", ["Haemoglobin", "Hemoglobin", "Hb"], "g/L", 115, 165, 0),
    ("WBC", ["White Cell Count", "WBC Count"], "x10^9/L", 4.0, 11.0, 1),
    ("PLAT", ["Platelets", "Platelet Count"], "x10^9/L", 150, 400, 0),
    ("MCV", ["MCV"], "fL", 80, 100, 0),
    ("Na+", ["Sodium"], "mmol/L", 135, 145, 0),
    ("K+", ["Potassium"], "mmol/L", 3.5, 5.2, 1),
    ("vitB12", ["Vitamin B12"], "pmol/L", 150, 600, 0),
    ("vitD", ["Vitamin D"], "nmol/L", 50, 150, 0),
]

LAYOUTS = [
    "{name} ({low}-{high}) {unit} {value}",
    "{name} ({low}-{high}) {value} {unit}",
    "{name} {value} {unit} ({low}-{high})",
    "{name} {value} {unit}",
    "{name} {unit} {value}",
]

HEADERS = [
    "BIOCHEMISTRY",
    "THYROID PROFILE",
    "FULL BLOOD COUNT",
    "Specimen Type: Serum",
    "Test Name Value Unit Bio. Ref Interval",
    "Date Collected: 05/03/2024 Complete: Final",
]

COMMENTS = [
    "Results reviewed by pathologist.",
    "Please note marginally abnormal results may be a variation of normal.",
    "Suggest follow up review as clinically appropriate.",
    "Fasting status not stated.",
]


@dataclass(frozen=True)
class LabelledMeasurement:
    parameter: str
    value: str
    unit: str
    name_span: tuple[int, int]
    value_span: tuple[int, int]
    unit_span: tuple[int, int]


def generate_report(
    rng: random.Random, n_tests: tuple[int, int] = (4, 10)
) -> tuple[str, list[LabelledMeasurement]]:
    """Return report text and its true measurements with character spans."""
    lines = ["SYNTHETIC PATHOLOGY REPORT", rng.choice(HEADERS)]
    labels: list[LabelledMeasurement] = []
    layout = rng.choice(LAYOUTS)  # one lab, one layout per report
    tests = rng.sample(TESTS, k=rng.randint(*n_tests))
    offset = sum(len(line) + 1 for line in lines)
    for abbreviation, names, unit, low, high, decimals in tests:
        name = rng.choice(names)
        value = f"{rng.uniform(low * 0.6, high * 1.4):.{decimals}f}"
        fields = {
            "name": name,
            "value": value,
            "unit": unit,
            "low": _fmt(low, decimals),
            "high": _fmt(high, decimals),
        }
        line = layout.format(**fields)
        spans = {key: _locate(layout, fields, key) for key in ("name", "value", "unit")}
        labels.append(
            LabelledMeasurement(
                parameter=abbreviation,
                value=value,
                unit=unit,
                name_span=_shift(spans["name"], offset),
                value_span=_shift(spans["value"], offset),
                unit_span=_shift(spans["unit"], offset),
            )
        )
        lines.append(line)
        offset += len(line) + 1
        if rng.random() < 0.15:
            comment = rng.choice(COMMENTS)
            lines.append(comment)
            offset += len(comment) + 1
    return "\n".join(lines) + "\n", labels


def _fmt(number: float, decimals: int) -> str:
    return f"{number:.{decimals}f}"


def _locate(layout: str, fields: dict[str, str], key: str) -> tuple[int, int]:
    """Character span of ``key``'s value in the formatted line."""
    before = layout.split("{" + key + "}")[0].format(**fields)
    return len(before), len(before) + len(fields[key])


def _shift(span: tuple[int, int], offset: int) -> tuple[int, int]:
    return span[0] + offset, span[1] + offset
