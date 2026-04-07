import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.wallet import Wallet


async def setup_user(client: AsyncClient, email: str) -> str:
    password = "strongpassword"
    await client.post("/auth/register", json={"email": email, "password": password, "full_name": "Recon"})
    login = await client.post("/auth/login", json={"email": email, "password": password})
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_reconciliation_clean_run(client: AsyncClient) -> None:
    token = await setup_user(client, "recon@example.com")
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": str(uuid.uuid4())}

    await client.post("/wallet/fund", headers=headers, json={"amount": "200.00", "reference": "recon-fund"})
    run_resp = await client.post("/reconciliation/run", headers={"Authorization": f"Bearer {token}"})

    assert run_resp.status_code == 200
    assert run_resp.json()["discrepancies_found"] == 0


@pytest.mark.asyncio
async def test_reconciliation_flags_discrepancy(client: AsyncClient, db_session: AsyncSession) -> None:
    token = await setup_user(client, "recon2@example.com")
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": str(uuid.uuid4())}

    await client.post("/wallet/fund", headers=headers, json={"amount": "300.00", "reference": "recon-fund-2"})

    user_result = await db_session.execute(select(User).where(User.email == "recon2@example.com"))
    user = user_result.scalar_one()
    wallet_result = await db_session.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = wallet_result.scalar_one()
    wallet.balance = wallet.balance + 10
    await db_session.commit()

    run_resp = await client.post("/reconciliation/run", headers={"Authorization": f"Bearer {token}"})
    assert run_resp.status_code == 200
    assert run_resp.json()["discrepancies_found"] >= 1
