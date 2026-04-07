from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WalletBalanceResponse(BaseModel):
    wallet_id: UUID
    balance: Decimal
    currency: str

    model_config = ConfigDict(from_attributes=True)


class FundRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    reference: str | None = None


class FundResponse(BaseModel):
    transaction_id: UUID
    new_balance: Decimal


class TransferRequest(BaseModel):
    recipient_email: str
    amount: Decimal = Field(gt=0)
    reference: str | None = None


class TransferResponse(BaseModel):
    transaction_id: UUID
    new_balance: Decimal
