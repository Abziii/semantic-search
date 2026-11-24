from sqlalchemy import select
from sqlalchemy.orm import Session

from .db_models import DocumentDB


class DocumentRepository:

    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[DocumentDB]:
        statement = select(DocumentDB)
        return list(self.session.scalars(statement).all())

    def get_by_id(self, document_id: str) -> DocumentDB | None:
        statement = select(DocumentDB).where(DocumentDB.id == document_id)
        return self.session.scalar(statement)

    def create(self, document: DocumentDB) -> DocumentDB:
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document
    def update(self, document: DocumentDB) -> DocumentDB:
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document