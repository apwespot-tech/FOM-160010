from fastapi.testclient import TestClient


def test_openapi_is_served(client: TestClient) -> None:
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    assert "/api/auth/code" in response.json()["paths"]


def test_docs_page_is_served(client: TestClient) -> None:
    assert client.get("/api/docs").status_code == 200
