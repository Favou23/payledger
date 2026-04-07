from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reconciliation_log import ReconciliationLog
from app.models.transaction import Transaction
from app.models.wallet import Wallet


async def run_reconciliation(db: AsyncSession) -> tuple[int, list[ReconciliationLog]]:
    wallets_result = await db.execute(select(Wallet))
    wallets = wallets_result.scalars().all()

    logs: list[ReconciliationLog] = []
    tolerance = Decimal("0.01")

    try:
        for wallet in wallets:
            credits_result = await db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.recipient_wallet_id == wallet.id)
            )
            credits = Decimal(str(credits_result.scalar_one()))

            debits_result = await db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.sender_wallet_id == wallet.id)
            )
            debits = Decimal(str(debits_result.scalar_one()))

            ledger_balance = (credits - debits).quantize(Decimal("0.01"))
            actual_balance = Decimal(str(wallet.balance)).quantize(Decimal("0.01"))
            discrepancy = (ledger_balance - actual_balance).quantize(Decimal("0.01"))

            flagged = abs(discrepancy) > tolerance
            log = ReconciliationLog(
                wallet_id=wallet.id,
                ledger_balance=ledger_balance,
                actual_balance=actual_balance,
                discrepancy=discrepancy,
                flagged=flagged,
            )
            db.add(log)
            logs.append(log)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    for log in logs:
        await db.refresh(log)

    discrepancies = [log for log in logs if log.flagged]
    return len(wallets), discrepancies


async def fetch_reconciliation_logs(db: AsyncSession, limit: int = 50, offset: int = 0) -> list[ReconciliationLog]:
    result = await db.execute(
        select(ReconciliationLog).order_by(ReconciliationLog.checked_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())
