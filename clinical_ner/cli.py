"""Command-line interface: extract, train, evaluate."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from clinical_ner.dictionary import ParameterDictionary
from clinical_ner.evaluate import Scores, triple
from clinical_ner.extract import extract_measurements
from clinical_ner.io import read_report

DEFAULT_MODEL = "models/clinical_ner"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="clinical-ner", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("extract", help="extract measurements from report text files")
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--engine", choices=["rules", "model"], default="rules")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--all", action="store_true", help="keep repeated tests, not just the first")

    p = sub.add_parser("train", help="train the spaCy NER model on synthetic reports")
    p.add_argument("--reports", type=int, default=400)
    p.add_argument("--epochs", type=int, default=15)
    p.add_argument("--output", default=DEFAULT_MODEL)

    p = sub.add_parser("evaluate", help="score both engines on synthetic and sample reports")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--reports", type=int, default=200)
    p.add_argument("--gold", type=Path, default=Path("data/samples/gold.json"))

    args = parser.parse_args(argv)
    return {"extract": _extract, "train": _train, "evaluate": _evaluate}[args.command](args)


def _extract(args) -> int:
    dictionary = ParameterDictionary.load()
    nlp = None
    if args.engine == "model":
        from clinical_ner.model import load

        nlp = load(args.model)
    output = {}
    for path in args.files:
        text = read_report(path)
        if nlp is not None:
            from clinical_ner.model import extract_with_model

            found = extract_with_model(nlp, text, dictionary, not args.all)
        else:
            found = extract_measurements(text, dictionary, not args.all)
        output[str(path)] = [m.to_dict() for m in found]
    json.dump(output, sys.stdout, indent=2)
    print()
    return 0


def _train(args) -> int:
    from clinical_ner.model import train

    nlp = train(n_reports=args.reports, epochs=args.epochs)
    Path(args.output).mkdir(parents=True, exist_ok=True)
    nlp.to_disk(args.output)
    print(f"saved model to {args.output}")
    return 0


def _evaluate(args) -> int:
    from clinical_ner.model import extract_with_model, load
    from clinical_ner.synthetic import generate_report

    dictionary = ParameterDictionary.load()
    nlp = load(args.model)
    engines = {
        "rules": lambda text: extract_measurements(text, dictionary, first_only=False),
        "model": lambda text: extract_with_model(nlp, text, dictionary, first_only=False),
    }

    # Held-out synthetic reports: a different seed from training.
    rng = random.Random(2024)
    synthetic = [generate_report(rng) for _ in range(args.reports)]
    gold_samples = json.loads(args.gold.read_text())

    results = {}
    for name, run in engines.items():
        synth, samples = Scores(), Scores()
        for text, labels in synthetic:
            synth.add(_triples(run(text)), [triple(m.parameter, m.value, m.unit) for m in labels])
        for file, expected in gold_samples.items():
            text = read_report(args.gold.parent / file)
            gold = [triple(dictionary.canonical(e["parameter"]), e["value"], e["unit"]) for e in expected]
            samples.add(_triples(run(text)), gold)
        results[name] = {"synthetic": synth.as_dict(), "sample_reports": samples.as_dict()}
    json.dump(results, sys.stdout, indent=2)
    print()
    return 0


def _triples(measurements):
    return [triple(m.parameter, m.value, m.unit) for m in measurements]


if __name__ == "__main__":
    raise SystemExit(main())
