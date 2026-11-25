from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import create_app, DocumentRepository


def test_document_survives_new_app_instance(shared_database):
    first_app = create_app(
        database_url=shared_database,
    )

    with TestClient(first_app) as client:
        response = client.post(
            "/documents",
            json={
                "id": "persistence-001",
                "title": "Test persistence",
                "description": "Persistence test",
                "text": "This document should survive application restart.",
            },
        )

        assert response.status_code == 201

    second_app = create_app(
        database_url=shared_database,
    )

    with TestClient(second_app) as client:
        response = client.get("/documents/persistence-001")

        assert response.status_code == 200
        assert response.json()["id"] == "persistence-001"
        assert response.json()["title"] == "Test persistence"



def test_second_get_uses_cache(client):
    document = {
        "id": "cache-hit-001",
        "title": "Cache test",
        "description": "Testing Redis cache",
        "text": "This document tests cache hit behavior.",
    }

    create_response = client.post("/documents", json=document)
    assert create_response.status_code == 201

    original_get = DocumentRepository.get_by_id

    with patch.object(
        DocumentRepository,
        "get_by_id",
        autospec=True,
        side_effect=original_get,
    ) as repository_get:

        first_response = client.get("/documents/cache-hit-001")

        assert first_response.status_code == 200
        assert first_response.headers["X-Cache"] == "MISS"
        assert repository_get.call_count == 1

        second_response = client.get("/documents/cache-hit-001")

        assert second_response.status_code == 200
        assert second_response.headers["X-Cache"] == "HIT"
        assert repository_get.call_count == 1

def test_update_invalidates_cache(client):
    document = {
        "id": "cache-update-001",
        "title": "Old title",
        "description": "Testing cache invalidation",
        "text": "Original document content.",
    }

    response = client.post("/documents", json=document)
    assert response.status_code == 201

    # Pierwszy odczyt - MISS
    response = client.get("/documents/cache-update-001")
    assert response.status_code == 200
    assert response.headers["X-Cache"] == "MISS"

    # Drugi odczyt - HIT
    response = client.get("/documents/cache-update-001")
    assert response.headers["X-Cache"] == "HIT"
    assert response.json()["title"] == "Old title"

    # Aktualizacja dokumentu
    response = client.patch(
        "/documents/cache-update-001",
        json={"title": "New title"},
    )
    assert response.status_code == 200

    # Po aktualizacji cache powinien byc pusty
    response = client.get("/documents/cache-update-001")
    assert response.status_code == 200
    assert response.headers["X-Cache"] == "MISS"
    assert response.json()["title"] == "New title"

    # Kolejny odczyt - HIT z nowymi danymi
    response = client.get("/documents/cache-update-001")
    assert response.headers["X-Cache"] == "HIT"
    assert response.json()["title"] == "New title"
def test_redis_failure_does_not_break_api(client):
    document = {
        "id": "redis-failure-001",
        "title": "Redis failure test",
        "description": "Testing Redis outage",
        "text": "This document should work without Redis.",
    }

    # Zapis dokumentu powinien działać.
    response = client.post("/documents", json=document)
    assert response.status_code == 201

    # Symulujemy awarię Redis.
    with patch("app.main.DocumentCache.get", return_value=(None, "BYPASS")), \
         patch("app.main.DocumentCache.set", return_value=False), \
         patch("app.main.DocumentCache.invalidate", return_value=False):

        # Odczyt powinien pobrać dokument z SQLite.
        response = client.get("/documents/redis-failure-001")

        assert response.status_code == 200
        assert response.headers["X-Cache"] == "BYPASS"
        assert response.json()["id"] == "redis-failure-001"

        # Aktualizacja 
        response = client.patch(
            "/documents/redis-failure-001",
            json={"title": "Updated without Redis"},
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Updated without Redis"

        # Sprawdzamy, czy dane faktycznie zapisano w SQLite.
        response = client.get("/documents/redis-failure-001")

        assert response.status_code == 200
        assert response.json()["title"] == "Updated without Redis"