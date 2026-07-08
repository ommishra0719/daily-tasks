"""
Business logic for documents. Routers should stay thin (HTTP concerns only)
and delegate all persistence logic here — this keeps the service layer
reusable/testable independent of FastAPI, and swappable (e.g. mock this
module entirely in unit tests instead of spinning up a real DB).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document
from app.schemas.document import DocumentCreate, DocumentUpdate


async def get_all_documents(db: AsyncSession) -> list[Document]:
    result = await db.execute(select(Document))
    return list(result.scalars().all())


async def get_document(db: AsyncSession, doc_id: int) -> Document | None:
    result = await db.execute(select(Document).where(Document.id == doc_id))
    return result.scalar_one_or_none()


async def create_document(db: AsyncSession, data: DocumentCreate) -> Document:
    doc = Document(title=data.title, content=data.content)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def update_document(
    db: AsyncSession, doc_id: int, data: DocumentUpdate
) -> Document | None:
    doc = await get_document(db, doc_id)
    if doc is None:
        return None

    doc.title = data.title
    doc.content = data.content
    await db.commit()
    await db.refresh(doc)
    return doc


async def delete_document(db: AsyncSession, doc_id: int) -> bool:
    doc = await get_document(db, doc_id)
    if doc is None:
        return False

    await db.delete(doc)
    await db.commit()
    return True
