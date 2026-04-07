from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.transaction import ReconciliationLogResponse, ReconciliationRunResponse
from app.services.auth_service import get_current_user
from app.services.reconciliation_service import fetch_reconciliation_logs, run_reconciliation

router = APIRouter()


@router.post("/run", response_model=ReconciliationRunResponse)
async def run(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReconciliationRunResponse:
    wallets_checked, discrepancies = await run_reconciliation(db)
    return ReconciliationRunResponse(
        wallets_checked=wallets_checked,
        discrepancies_found=len(discrepancies),
        details=[ReconciliationLogResponse.model_validate(item) for item in discrepancies],
    )


@router.get("/logs", response_model=list[ReconciliationLogResponse])
async def logs(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReconciliationLogResponse]:
    rows = await fetch_reconciliation_logs(db, limit=limit, offset=offset)
    return [ReconciliationLogResponse.model_validate(row) for row in rows]
