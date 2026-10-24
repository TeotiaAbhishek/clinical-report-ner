FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY clinical_ner ./clinical_ner
RUN pip install --no-cache-dir .

# Train the NER model at build time so the image is self-contained (about a minute).
RUN clinical-ner train --output /app/models/clinical_ner
ENV CLINICAL_NER_MODEL=/app/models/clinical_ner

RUN useradd --create-home app
USER app
EXPOSE 8000
CMD ["uvicorn", "clinical_ner.api:app", "--host", "0.0.0.0", "--port", "8000"]
