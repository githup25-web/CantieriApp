from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, UploadFile, status
from pydantic import BaseModel

from app.core.event_bus import emit_event
from app.core.security import get_current_user
from app.models.expense import Expense
from app.models.membership import Membership
from app.models.user import User
from app.routes.organization import check_role

router = APIRouter(prefix="/expense", tags=["expense"])


class ExpenseResponse(BaseModel):
    id: str | None = None
    user_id: str
    organization_id: str
    cantiere_id: str
    category: str
    amount: float
    description: str
    receipt_url: str | None = None
    timestamp: str


@router.post("/create", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    category: Annotated[str, Form(...)],
    amount: Annotated[float, Form(...)],
    description: Annotated[str, Form(...)],
    cantiere_id: Annotated[UUID, Form(...)],
    file: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
) -> ExpenseResponse:
    membership = await Membership.find_one(Membership.user_id == current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="User is not a member of any organization")

    receipt_url = None
    if file is not None:
        receipt_url = f"/uploads/{file.filename}"

    expense = Expense(
        user_id=current_user.id,
        organization_id=membership.organization_id,
        cantiere_id=cantiere_id,
        category=category,
        amount=amount,
        description=description,
        receipt_url=receipt_url,
    )
    await expense.insert()

    try:
        await emit_event(
            event_name="spesa.created",
            payload={
                "organization_id": expense.organization_id,
                "entity_id": expense.id,
                "data": {"expense_id": str(expense.id), "cantiere_id": str(expense.cantiere_id)},
            },
        )
    except Exception:
        pass

    return ExpenseResponse(
        id=str(expense.id),
        user_id=str(expense.user_id),
        organization_id=str(expense.organization_id),
        cantiere_id=str(expense.cantiere_id),
        category=expense.category,
        amount=expense.amount,
        description=expense.description,
        receipt_url=expense.receipt_url,
        timestamp=expense.timestamp.isoformat(),
    )


@router.get("/my", response_model=list[ExpenseResponse])
async def get_my_expenses(current_user: User = Depends(get_current_user)) -> list[ExpenseResponse]:
    expenses = await Expense.find(Expense.user_id == current_user.id).to_list()
    return [
        ExpenseResponse(
            id=str(e.id),
            user_id=str(e.user_id),
            organization_id=str(e.organization_id),
            cantiere_id=str(e.cantiere_id),
            category=e.category,
            amount=e.amount,
            description=e.description,
            receipt_url=e.receipt_url,
            timestamp=e.timestamp.isoformat(),
        )
        for e in expenses
    ]


@router.get("/cantiere/{id}", response_model=list[ExpenseResponse])
async def get_cantiere_expenses(
    id: UUID = Path(...),
    current_user: User = Depends(check_role(["owner", "admin", "manager", "accountant"])),
) -> list[ExpenseResponse]:
    expenses = await Expense.find(Expense.cantiere_id == id).to_list()
    return [
        ExpenseResponse(
            id=str(e.id),
            user_id=str(e.user_id),
            organization_id=str(e.organization_id),
            cantiere_id=str(e.cantiere_id),
            category=e.category,
            amount=e.amount,
            description=e.description,
            receipt_url=e.receipt_url,
            timestamp=e.timestamp.isoformat(),
        )
        for e in expenses
    ]


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    id: UUID = Path(...),
    current_user: User = Depends(check_role(["owner", "admin", "accountant"])),
) -> None:
    expense = await Expense.get(id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    await expense.delete()
