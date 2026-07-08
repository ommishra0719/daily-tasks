from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["Documents"])

limiter = Limiter(key_func=get_remote_address)


@router.get("/", response_model=list[DocumentResponse])
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def list_documents(request: Request, db: AsyncSession = Depends(get_db)):
    return await document_service.get_all_documents(db)


@router.get("/{doc_id}", response_model=DocumentResponse)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def read_document(
    request: Request, doc_id: int, db: AsyncSession = Depends(get_db)
):
    doc = await document_service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def add_document(
    request: Request, document: DocumentCreate, db: AsyncSession = Depends(get_db)
):
    return await document_service.create_document(db, document)


@router.put("/{doc_id}", response_model=DocumentResponse)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def edit_document(
    request: Request,
    doc_id: int,
    document: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
):
    updated = await document_service.update_document(db, doc_id, document)
    if updated is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return updated


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def remove_document(
    request: Request, doc_id: int, db: AsyncSession = Depends(get_db)
):
    deleted = await document_service.delete_document(db, doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
