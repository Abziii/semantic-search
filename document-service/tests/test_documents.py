
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    test_app = create_app()

    with TestClient(test_app) as test_client:
        yield test_client


def test_create_and_read_document(client):
    payload = {
        "id": "doc-001",
        "title": "Artificial Intelligence",
        "description": "Introduction to AI",
        "text": "Artificial intelligence is a field of computer science."
    }

    response = client.post("/documents", json=payload)

    assert response.status_code == 201
    assert response.json()["id"] == "doc-001"

    response = client.get("/documents/doc-001")

    assert response.status_code == 200
    assert response.json()["title"] == "Artificial Intelligence"


def test_invalid_document_does_not_modify_storage(client):
    payload = {
        "id": "doc-002",
        "description": "Missing title",
        "text": "This document has no title."
    }

    response = client.post("/documents", json=payload)

    assert response.status_code == 422

    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json() == []


def test_duplicate_content_returns_conflict(client):
    first_document = {
        "id": "doc-001",
        "title": "First document",
        "description": "First description",
        "text": "Semantic search uses text embeddings."
    }

    second_document = {
        "id": "doc-002",
        "title": "Second document",
        "description": "Second description",
        "text": "SEMANTIC SEARCH uses   text embeddings."
    }

    response = client.post("/documents", json=first_document)
    assert response.status_code == 201

    response = client.post("/documents", json=second_document)

    assert response.status_code == 409

    response = client.get("/documents")

    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get("/documents/doc-002")
    assert response.status_code == 404


def test_missing_document_returns_404(client):
    response = client.get("/documents/doc-999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
