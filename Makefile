.PHONY: install test lint train evaluate serve docker

install:
	pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check . && ruff format --check .

train:
	clinical-ner train

evaluate:
	clinical-ner evaluate

serve:
	uvicorn clinical_ner.api:app --reload

docker:
	docker build -t clinical-ner . && docker run --rm -p 8000:8000 clinical-ner
