# Clinical Report NER

Turn the OCR text of a pathology report into structured results. Given a scanned lab report, this package finds each test, its value, unit and reference range, and maps the test name to a standard abbreviation (for example "Serum Ferritin", "Ferritin" and the OCR typo "Ferritn" all become `FERR`).

```text
TSH (0.5-4.0) mIU/L 1.92          ->  {"parameter": "TSH",  "value": "1.92", "unit": "mIU/L",  "reference_range": "0.5-4.0"}
Serum Ferritin 85 ug/L (30-300)   ->  {"parameter": "FERR", "value": "85",   "unit": "ug/L",   "reference_range": null}
Vitamin D 73 83 nmol/L            ->  {"parameter": "vitD", "value": "73",   "unit": "nmol/L", "reference_range": null}
```

It ships as a Python package with a command-line tool, a FastAPI service, a Docker image and CI.

## How it works

Two extraction engines share one parameter dictionary of 259 tests and about 2,500 synonyms.

| Engine | How | When to use |
|---|---|---|
| `rules` (default) | Four regex layouts applied line by line, with validation of units and fuzzy dictionary matching to tolerate OCR typos | Fast, transparent, no model needed |
| `model` | A spaCy NER model tags `PARAMETER`, `VALUE` and `UNIT` tokens; each parameter is then paired with the next value and unit on its line | Layouts the regexes don't cover |

```text
OCR text
   |
   +-- rules: regex layouts --> unit check --> dictionary match ----+
   |                                                                 +--> {parameter, name, value, unit, range}
   +-- model: spaCy NER --> pair entities per line --> dictionary ---+
```

Design choices worth knowing:

- **Line by line.** Each test sits on its own line in lab reports, so lines are matched separately. This stops a name from absorbing text from the line above.
- **Noise rejection.** A match is dropped if its "unit" isn't a unit (`Plasma`, `H`), or if a value with `<` or `>` has no reference range, which usually means a threshold in comment text ("Vitamin D deficiency <50 nmol/L").
- **Ambiguous synonyms.** About 65 terms appear under more than one abbreviation (such as "creatinine" under `CREA` and `CREAN`). These resolve in priority order: the abbreviation itself, then an entry's primary synonym, then any other synonym.
- **First result only.** Reports often repeat a test in historical columns or on later pages. By default the first value is kept; `--all` keeps every occurrence.

## Data and privacy

Real pathology reports contain patient health information, so **this repository contains no real reports**. The model is trained on synthetic reports from `clinical_ner/synthetic.py`, which mimic layouts seen in real OCR output: 27 common tests, several spellings each, five layouts, header and comment noise. Three hand-written reports in `data/samples/` have hand-labelled answers in `gold.json`.

`data/private/` is git-ignored for local testing on real reports.

## Results

`clinical-ner evaluate` scores each engine on (test, value, unit) triples:

| Engine | 200 held-out synthetic reports (F1) | 3 hand-labelled sample reports (F1) |
|---|---:|---:|
| rules | 1.00 | 1.00 |
| model | 1.00 | 1.00 |

These scores show the pipeline is internally consistent. They do not measure real-world accuracy, because the test reports use the same layouts the engines were built for. On real de-identified reports used during development, both engines found most results but also made errors, such as picking up thresholds from comment text and misreading units garbled by OCR. Measuring real accuracy needs a labelled set of real reports, which is the next step.

## Usage

```bash
pip install -e ".[dev]"

# Extract from one or more text files (prints JSON)
clinical-ner extract data/samples/renal_liver.txt
clinical-ner extract report.txt --engine model --all

# Train the spaCy model (about a minute on a laptop CPU) and evaluate both engines
clinical-ner train
clinical-ner evaluate
```

### API

```bash
uvicorn clinical_ner.api:app --reload
```

```bash
curl -X POST localhost:8000/extract \
  -H 'Content-Type: application/json' \
  -d '{"text": "Ferritin (30-300) ug/L 85\nTSH 1.92 mIU/L", "engine": "rules"}'
```

```json
{
  "engine": "rules",
  "count": 2,
  "measurements": [
    {"parameter": "FERR", "name": "Ferritin", "value": "85", "unit": "ug/L", "reference_range": "30-300"},
    {"parameter": "TSH", "name": "TSH", "value": "1.92", "unit": "mIU/L", "reference_range": null}
  ]
}
```

Interactive docs are at `localhost:8000/docs`. `GET /health` reports status, version and dictionary size.

### Docker

```bash
docker build -t clinical-ner .          # also trains the model inside the image
docker run -p 8000:8000 clinical-ner
```

### Python

```python
from clinical_ner import ParameterDictionary, extract_measurements

dictionary = ParameterDictionary.load()
for m in extract_measurements(open("report.txt").read(), dictionary):
    print(m.parameter, m.value, m.unit)
```

## Testing and CI

```bash
make test    # 31 tests: dictionary, every layout, noise rejection, spans, API, and a small model training run
make lint    # ruff
```

GitHub Actions runs lint, tests, full training and evaluation, then builds the Docker image and smoke-tests the API on every push and pull request.

## Project structure

```text
clinical_ner/
├── dictionary.py            parameter lookup: exact, fuzzy, ambiguity rules
├── extract.py               rule-based engine
├── model.py                 spaCy NER training and entity pairing
├── synthetic.py             labelled synthetic report generator
├── evaluate.py              precision, recall and F1
├── api.py                   FastAPI service
├── cli.py                   clinical-ner command
└── resources/parameters.json
data/samples/                synthetic sample reports and gold labels
tests/
Dockerfile
.github/workflows/ci.yml
```

## Next steps

- Label 50 to 100 real de-identified reports and report accuracy on them.
- Add table-aware parsing for multi-column reports (several dates side by side).
- Flag results outside their reference range.
- Accept PDFs and images directly by adding an OCR step (Tesseract).

## Background

This started in 2024 as a notebook that matched regex patterns and trained a spaCy model on a single report. Version 1.0 restructures it into a tested package and API. It also fixes two bugs from the notebook: relation extraction read a global variable instead of the document it was given, and training labels for two layouts used a stale character offset.
