"""HTTP API: POST report text, get structured measurements back."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from clinical_ner import __version__
from clinical_ner.dictionary import ParameterDictionary
from clinical_ner.extract import extract_measurements

MODEL_PATH = os.getenv("CLINICAL_NER_MODEL", "models/clinical_ner")

app = FastAPI(title="Clinical Report NER", version=__version__)


class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200_000, description="OCR text of one report")
    engine: Literal["rules", "model"] = "rules"
    first_only: bool = True


class MeasurementOut(BaseModel):
    parameter: str
    name: str
    value: str
    unit: str
    reference_range: str | None


class ExtractResponse(BaseModel):
    engine: str
    count: int
    measurements: list[MeasurementOut]


@lru_cache
def get_dictionary() -> ParameterDictionary:
    return ParameterDictionary.load()


@lru_cache
def get_model():
    from clinical_ner.model import load

    return load(MODEL_PATH)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "parameters": len(get_dictionary())}


@app.post("/extract", response_model=ExtractResponse)
def extract(request: ExtractRequest) -> ExtractResponse:
    text = request.text.replace("\r\n", "\n")
    dictionary = get_dictionary()
    if request.engine == "model":
        try:
            nlp = get_model()
        except OSError:
            raise HTTPException(503, f"No trained model at {MODEL_PATH}. Run `clinical-ner train` first.")
        from clinical_ner.model import extract_with_model

        found = extract_with_model(nlp, text, dictionary, request.first_only)
    else:
        found = extract_measurements(text, dictionary, request.first_only)
    measurements = [MeasurementOut(**m.to_dict()) for m in found]
    return ExtractResponse(engine=request.engine, count=len(measurements), measurements=measurements)
