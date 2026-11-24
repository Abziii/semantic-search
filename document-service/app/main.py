
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from redis import Redis
from sqlalchemy import select

from .database import Base, make_database
from .db_models import DocumentDB
from .repository import DocumentRepository
from .cache import DocumentCache


class Document(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    text: str = Field(min_length=1)

class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    text: str | None = Field(default=None, min_length=1)
    
def normalize_text(text: str) -> str:
    """Normalize text for duplicate detection."""
    return " ".join(text.casefold().split())


def create_app(
    database_url: str = "sqlite:///./document-service/app.db",
    redis_client: Redis | None = None,
    cache_ttl: int = 60,
) -> FastAPI:

    engine, session_factory = make_database(database_url)

    owns_redis_client = redis_client is None

    if redis_client is None:
        redis_client = Redis.from_url(
            "redis://localhost:6379/0",
            decode_responses=True,
        )

    cache = DocumentCache(redis_client, ttl=cache_ttl)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(bind=engine)

        yield

        engine.dispose()

        if owns_redis_client:
            redis_client.close()

    app = FastAPI(
        title="Document Service",
        description="Microservice responsible for storing and retrieving documents.",
        version="2.0.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    def health_check():
        return {
            "status": "healthy",
            "service": "document-service"
        }

    @app.get("/documents", response_model=list[Document])
    def get_documents():
        with session_factory() as session:
            repository = DocumentRepository(session)
            documents = repository.get_all()

            return [
                Document.model_validate(document, from_attributes=True)
                for document in documents
            ]

    @app.get("/documents/{document_id}", response_model=Document)
    def get_document(document_id: str):

        cached_document, cache_status = cache.get(document_id)

        if cache_status == "HIT":
            return JSONResponse(
                content=cached_document,
                headers={"X-Cache": "HIT"},
            )

        with session_factory() as session:
            repository = DocumentRepository(session)
            document = repository.get_by_id(document_id)

            if document is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document with ID '{document_id}' not found"
                )

            result = Document.model_validate(
                document,
                from_attributes=True,
            )

        if cache_status != "BYPASS":
            cache.set(document_id, result.model_dump())

        return_document = result.model_dump()

        

        return JSONResponse(
            content=return_document,
            headers={"X-Cache": cache_status},
        )

    @app.post(
        "/documents",
        status_code=status.HTTP_201_CREATED,
        response_model=Document,
    )
    def create_document(document: Document):

        with session_factory() as session:
            repository = DocumentRepository(session)

            # Check for duplicate ID
            if repository.get_by_id(document.id) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Document with ID '{document.id}' already exists"
                )

            # Check for duplicate content
            normalized_new_text = normalize_text(document.text)

            existing_documents = repository.get_all()

            for existing in existing_documents:
                if normalize_text(existing.text) == normalized_new_text:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="A document with identical text already exists"
                    )

            db_document = DocumentDB(**document.model_dump())

            try:
                repository.create(db_document)
            except Exception:
                session.rollback()
                raise

            return document

    return app


app = create_app()
