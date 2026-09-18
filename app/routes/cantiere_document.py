from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, UploadFile, status
from pydantic import BaseModel

from app.core.event_bus import emit_event
from app.core.security import get_current_user
from app.models.cantiere_document import CantiereDocument
from app.models.membership import Membership
from app.models.user import User
from app.routes.organization import check_role

router = APIRouter(prefix="/cantiere-document", tags=["cantiere-document"])


class CantiereDocumentResponse(BaseModel):
    id: str | None = None
    cantiere_id: str
    organization_id: str
    user_id: str
    type: str
    title: str
    description: str | None = None
    url: str
    uploaded_at: str
    version: int


@router.post("/upload", response_model=CantiereDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_cantiere_document(
    cantiere_id: Annotated[UUID, Form(...)],
    type: Annotated[str, Form(...)],
    title: Annotated[str, Form(...)],
    description: Annotated[str | None, Form()] = None,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> CantiereDocumentResponse:
    membership = await Membership.find_one(Membership.user_id == current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="User is not a member of any organization")

    existing = await CantiereDocument.find_one(
        CantiereDocument.cantiere_id == cantiere_id,
        CantiereDocument.type == type,
        CantiereDocument.title == title,
    )
    version = 1 if existing is None else existing.version + 1

    document = CantiereDocument(
        cantiere_id=cantiere_id,
        organization_id=membership.organization_id,
        user_id=current_user.id,
        type=type,
        title=title,
        description=description,
        url=f"/uploads/{file.filename}",
        version=version,
    )
    await document.insert()

    try:
        await emit_event(
            event_name="documento.uploaded",
            payload={
                "organization_id": document.organization_id,
                "entity_id": document.id,
                "data": {"document_id": str(document.id), "cantiere_id": str(document.cantiere_id), "type": document.type, "title": document.title},
            },
        )
    except Exception:
        pass

    return CantiereDocumentResponse(
        id=str(document.id),
        cantiere_id=str(document.cantiere_id),
        organization_id=str(document.organization_id),
        user_id=str(document.user_id),
        type=document.type,
        title=document.title,
        description=document.description,
        url=document.url,
        uploaded_at=document.uploaded_at.isoformat(),
        version=document.version,
    )


@router.get("/cantiere/{id}", response_model=list[CantiereDocumentResponse])
async def get_documents_by_cantiere(
    id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
) -> list[CantiereDocumentResponse]:
    documents = await CantiereDocument.find(CantiereDocument.cantiere_id == id).sort(CantiereDocument.uploaded_at).to_list()  # type: ignore[arg-type]
    return [
        CantiereDocumentResponse(
            id=str(doc.id),
            cantiere_id=str(doc.cantiere_id),
            organization_id=str(doc.organization_id),
            user_id=str(doc.user_id),
            type=doc.type,
            title=doc.title,
            description=doc.description,
            url=doc.url,
            uploaded_at=doc.uploaded_at.isoformat(),
            version=doc.version,
        )
        for doc in documents
    ]


@router.get("/{id}", response_model=CantiereDocumentResponse)
async def get_document(id: UUID = Path(...), current_user: User = Depends(get_current_user)) -> CantiereDocumentResponse:
    document = await CantiereDocument.get(id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return CantiereDocumentResponse(
        id=str(document.id),
        cantiere_id=str(document.cantiere_id),
        organization_id=str(document.organization_id),
        user_id=str(document.user_id),
        type=document.type,
        title=document.title,
        description=document.description,
        url=document.url,
        uploaded_at=document.uploaded_at.isoformat(),
        version=document.version,
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    id: UUID = Path(...),
    current_user: User = Depends(check_role(["owner", "admin", "manager"])),
) -> None:
    document = await CantiereDocument.get(id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    await document.delete()
