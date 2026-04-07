import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReconciliationLog(Base):
    __tablename__ = "reconciliation_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wallets.id"), nullable=False)
    ledger_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    actual_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    discrepancy: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
