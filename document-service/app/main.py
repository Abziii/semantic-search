
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    text: str = Field(min_length=1)


def normalize_text(text: str) -> str:
    """Normalize text for duplicate detection."""
    return " ".join(text.casefold().split())


def create_app() -> FastAPI:

    app = FastAPI(
        title="Document Service",
        description="Microservice responsible for storing and retrieving documents.",
        version="1.0.0"
    )

    # Separate storage for each application instance
    documents: dict[str, Document] = {}

    @app.get("/health")
    def health_check():
        return {
            "status": "healthy",
            "service": "document-service"
        }

    @app.get("/documents")
    def get_documents():
        return list(documents.values())

    @app.get("/documents/{document_id}")
    def get_document(document_id: str):

        document = documents.get(document_id)

        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{document_id}' not found"
            )

        return document

    @app.post(
        "/documents",
        status_code=status.HTTP_201_CREATED
    )
    def create_document(document: Document):

        # Check for duplicate ID
        if document.id in documents:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Document with ID '{document.id}' already exists"
            )

        # Check for duplicate content
        normalized_new_text = normalize_text(document.text)

        for existing in documents.values():
            if normalize_text(existing.text) == normalized_new_text:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A document with identical text already exists"
                )

        # Save document only after all checks pass
        documents[document.id] = document

        return document

    return app


app = create_app()
