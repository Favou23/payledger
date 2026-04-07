from fastapi import APIRouter, Depends, Header, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.redis_client import get_redis
from app.schemas.wallet import (
    FundRequest,
    FundResponse,
    TransferRequest,
    TransferResponse,
    WalletBalanceResponse,
)
from app.services.auth_service import get_current_user
from app.services.idempotency import check_idempotency, store_idempotency
from app.services.wallet_service import fund_wallet, get_wallet_for_user, transfer_funds

router = APIRouter()


@router.get("/balance", response_model=WalletBalanceResponse)
async def balance(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> WalletBalanceResponse:
    wallet = await get_wallet_for_user(db, current_user.id)
    return WalletBalanceResponse(wallet_id=wallet.id, balance=wallet.balance, currency=wallet.currency)


@router.post("/fund", response_model=FundResponse)
async def fund(
    payload: FundRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> FundResponse:
    cached = await check_idempotency(redis, idempotency_key)
    if cached:
        return FundResponse(**cached)

    wallet = await get_wallet_for_user(db, current_user.id)
    txn, new_balance = await fund_wallet(db, wallet, payload.amount, idempotency_key, payload.reference)

    response = {"transaction_id": str(txn.id), "new_balance": str(new_balance)}
    await store_idempotency(redis, idempotency_key, response)
    return FundResponse(**response)


@router.post("/transfer", response_model=TransferResponse)
async def transfer(
    payload: TransferRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TransferResponse:
    cached = await check_idempotency(redis, idempotency_key)
    if cached:
        return TransferResponse(**cached)

    sender_wallet = await get_wallet_for_user(db, current_user.id)
    txn, new_balance = await transfer_funds(
        db=db,
        sender_wallet=sender_wallet,
        recipient_email=payload.recipient_email,
        amount=payload.amount,
        idempotency_key=idempotency_key,
        reference=payload.reference,
    )

    response = {"transaction_id": str(txn.id), "new_balance": str(new_balance)}
    await store_idempotency(redis, idempotency_key, response)
    return TransferResponse(**response)
