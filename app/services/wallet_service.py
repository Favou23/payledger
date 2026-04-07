from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.user import User
from app.models.wallet import Wallet

MONEY_QUANT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT)


async def get_wallet_for_user(db: AsyncSession, user_id: str) -> Wallet:
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    return wallet


async def fund_wallet(
    db: AsyncSession,
    wallet: Wallet,
    amount: Decimal,
    idempotency_key: str,
    reference: str | None,
) -> tuple[Transaction, Decimal]:
    amount = _money(amount)
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be greater than zero")

    try:
        locked_result = await db.execute(select(Wallet).where(Wallet.id == wallet.id).with_for_update())
        locked_wallet = locked_result.scalar_one()
        locked_wallet.balance = _money(locked_wallet.balance + amount)

        transaction = Transaction(
            idempotency_key=idempotency_key,
            type="FUND",
            amount=amount,
            recipient_wallet_id=locked_wallet.id,
            status="SUCCESS",
            reference=reference,
            metadata_json={"action": "wallet_funding"},
        )
        db.add(transaction)
        await db.flush()
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await db.refresh(transaction)
    return transaction, locked_wallet.balance


async def transfer_funds(
    db: AsyncSession,
    sender_wallet: Wallet,
    recipient_email: str,
    amount: Decimal,
    idempotency_key: str,
    reference: str | None,
) -> tuple[Transaction, Decimal]:
    amount = _money(amount)
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be greater than zero")

    try:
        recipient_user_result = await db.execute(select(User).where(User.email == recipient_email))
        recipient_user = recipient_user_result.scalar_one_or_none()
        if not recipient_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")

        recipient_wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == recipient_user.id))
        recipient_wallet = recipient_wallet_result.scalar_one_or_none()
        if not recipient_wallet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient wallet not found")
        if recipient_wallet.id == sender_wallet.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot transfer to same wallet")

        wallets_result = await db.execute(
            select(Wallet)
            .where(Wallet.id.in_([sender_wallet.id, recipient_wallet.id]))
            .order_by(Wallet.id)
            .with_for_update()
        )
        locked_wallets = {wallet.id: wallet for wallet in wallets_result.scalars().all()}
        locked_sender = locked_wallets[sender_wallet.id]
        locked_recipient = locked_wallets[recipient_wallet.id]

        if locked_sender.balance < amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")

        locked_sender.balance = _money(locked_sender.balance - amount)
        locked_recipient.balance = _money(locked_recipient.balance + amount)

        debit_txn = Transaction(
            idempotency_key=idempotency_key,
            type="TRANSFER_DEBIT",
            amount=amount,
            sender_wallet_id=locked_sender.id,
            recipient_wallet_id=locked_recipient.id,
            status="SUCCESS",
            reference=reference,
            metadata_json={"direction": "debit"},
        )
        credit_txn = Transaction(
            idempotency_key=None,
            type="TRANSFER_CREDIT",
            amount=amount,
            sender_wallet_id=locked_sender.id,
            recipient_wallet_id=locked_recipient.id,
            status="SUCCESS",
            reference=reference,
            metadata_json={"direction": "credit"},
        )
        db.add_all([debit_txn, credit_txn])
        await db.flush()
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await db.refresh(debit_txn)
    return debit_txn, locked_sender.balance
