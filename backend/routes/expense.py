from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status

from backend.core.database import get_collection
from backend.dependencies.auth import get_current_user
from backend.models.expense import ExpenseCreate, ExpenseDB, ExpensePublic

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("/", response_model=ExpensePublic, status_code=status.HTTP_201_CREATED)
async def create_expense(
    payload: ExpenseCreate,
    current_user: dict = Depends(get_current_user),
) -> ExpensePublic:
    """Create a new expense."""
    expenses_collection = get_collection("expenses")
    memberships_collection = get_collection("memberships")

    # Get user's tenant
    membership = await memberships_collection.find_one(
        {"user_id": current_user["_id"]}
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of any tenant",
        )

    expense = ExpenseDB(
        user_id=current_user["_id"],
        tenant_id=membership["tenant_id"],
        cantiere_id=payload.cantiere_id,
        category=payload.category,
        amount=payload.amount,
        description=payload.description,
        receipt_url=payload.receipt_url,
    )
    await expenses_collection.insert_one(expense.model_dump(by_alias=True))

    return ExpensePublic(
        id=str(expense.id),
        user_id=str(expense.user_id),
        tenant_id=str(expense.tenant_id),
        cantiere_id=str(expense.cantiere_id),
        category=expense.category,
        amount=expense.amount,
        description=expense.description,
        receipt_url=expense.receipt_url,
        timestamp=expense.timestamp.isoformat(),
    )


@router.get("/my", response_model=list[ExpensePublic])
async def get_my_expenses(
    current_user: dict = Depends(get_current_user),
) -> list[ExpensePublic]:
    """Get all expenses for the current user."""
    expenses_collection = get_collection("expenses")

    expenses = await expenses_collection.find(
        {"user_id": current_user["_id"]}
    ).sort("timestamp", -1).to_list(length=100)

    return [
        ExpensePublic(
            id=str(e["_id"]),
            user_id=str(e["user_id"]),
            tenant_id=str(e["tenant_id"]),
            cantiere_id=str(e["cantiere_id"]),
            category=e["category"],
            amount=e["amount"],
            description=e["description"],
            receipt_url=e.get("receipt_url"),
            timestamp=e["timestamp"].isoformat(),
        )
        for e in expenses
    ]


@router.get("/cantiere/{id}", response_model=list[ExpensePublic])
async def get_cantiere_expenses(
    id: UUID = Path(...),
    current_user: dict = Depends(get_current_user),
) -> list[ExpensePublic]:
    """Get all expenses for a specific cantiere."""
    expenses_collection = get_collection("expenses")

    expenses = await expenses_collection.find(
        {"cantiere_id": id}
    ).sort("timestamp", -1).to_list(length=100)

    return [
        ExpensePublic(
            id=str(e["_id"]),
            user_id=str(e["user_id"]),
            tenant_id=str(e["tenant_id"]),
            cantiere_id=str(e["cantiere_id"]),
            category=e["category"],
            amount=e["amount"],
            description=e["description"],
            receipt_url=e.get("receipt_url"),
            timestamp=e["timestamp"].isoformat(),
        )
        for e in expenses
    ]


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    id: UUID = Path(...),
    current_user: dict = Depends(get_current_user),
) -> None:
    """Delete an expense."""
    expenses_collection = get_collection("expenses")

    expense = await expenses_collection.find_one({"_id": id})
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found",
        )

    # Check if user owns this expense or has admin role
    if str(expense["user_id"]) != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this expense",
        )

    await expenses_collection.delete_one({"_id": id})
