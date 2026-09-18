from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, UploadFile, status
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.membership import Membership
from app.models.progress_photo import ProgressPhoto
from app.models.user import User
from app.routes.organization import check_role

router = APIRouter(prefix="/progress-photo", tags=["progress-photo"])


class ProgressPhotoResponse(BaseModel):
    id: str | None = None
    user_id: str
    organization_id: str
    cantiere_id: str
    stage: str
    url: str
    description: str | None = None
    timestamp: str


@router.post("/upload", response_model=ProgressPhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_progress_photo(
    cantiere_id: Annotated[UUID, Form(...)],
    stage: Annotated[str, Form(...)],
    description: Annotated[str | None, Form()] = None,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> ProgressPhotoResponse:
    membership = await Membership.find_one(Membership.user_id == current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="User is not a member of any organization")

    url = f"/uploads/{file.filename}"

    photo = ProgressPhoto(
        user_id=current_user.id,
        organization_id=membership.organization_id,
        cantiere_id=cantiere_id,
        stage=stage,
        url=url,
        description=description,
    )
    await photo.insert()

    return ProgressPhotoResponse(
        id=str(photo.id),
        user_id=str(photo.user_id),
        organization_id=str(photo.organization_id),
        cantiere_id=str(photo.cantiere_id),
        stage=photo.stage,
        url=photo.url,
        description=photo.description,
        timestamp=photo.timestamp.isoformat(),
    )


@router.get("/cantiere/{id}", response_model=list[ProgressPhotoResponse])
async def get_progress_photos_by_cantiere(
    id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
) -> list[ProgressPhotoResponse]:
    photos = await ProgressPhoto.find(ProgressPhoto.cantiere_id == id).sort(+ProgressPhoto.timestamp).to_list()
    return [
        ProgressPhotoResponse(
            id=str(p.id),
            user_id=str(p.user_id),
            organization_id=str(p.organization_id),
            cantiere_id=str(p.cantiere_id),
            stage=p.stage,
            url=p.url,
            description=p.description,
            timestamp=p.timestamp.isoformat(),
        )
        for p in photos
    ]


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_progress_photo(
    id: UUID = Path(...),
    current_user: User = Depends(check_role(["owner", "admin", "manager"])),
) -> None:
    photo = await ProgressPhoto.get(id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    await photo.delete()
