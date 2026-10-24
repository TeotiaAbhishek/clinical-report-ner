from fastapi.testclient import TestClient

from clinical_ner.api import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_extract_rules():
    response = client.post("/extract", json={"text": "Ferritin (30-300) ug/L 85\nTSH 1.9 mIU/L\n"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["measurements"][0] == {
        "parameter": "FERR",
        "name": "Ferritin",
        "value": "85",
        "unit": "ug/L",
        "reference_range": "30-300",
    }


def test_rejects_empty_text():
    assert client.post("/extract", json={"text": ""}).status_code == 422
