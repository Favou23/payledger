from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TransactionResponse(BaseModel):
    id: UUID
    type: str
    amount: Decimal
    sender_wallet_id: UUID | None
    recipient_wallet_id: UUID | None
    status: str
    reference: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReconciliationLogResponse(BaseModel):
    id: UUID
    wallet_id: UUID
    ledger_balance: Decimal
    actual_balance: Decimal
    discrepancy: Decimal
    flagged: bool
    checked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReconciliationRunResponse(BaseModel):
    wallets_checked: int
    discrepancies_found: int
    details: list[ReconciliationLogResponse]
