from fastapi.testclient import TestClient
from app.main import app
from tests.test_health import client, response

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
