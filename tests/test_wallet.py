import uuid

import pytest
from httpx import AsyncClient


async def create_and_login(client: AsyncClient, email: str) -> str:
    password = "strongpassword"
    await client.post("/auth/register", json={"email": email, "password": password, "full_name": email.split("@")[0]})
    login = await client.post("/auth/login", json={"email": email, "password": password})
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_wallet_fund(client: AsyncClient, auth_header: dict[str, str]) -> None:
    idem = str(uuid.uuid4())
    resp = await client.post(
        "/wallet/fund",
        headers={**auth_header, "Idempotency-Key": idem},
        json={"amount": "1000.00", "reference": "fund-1"},
    )
    assert resp.status_code == 200
    assert str(resp.json()["new_balance"]) == "1000.00"


@pytest.mark.asyncio
async def test_wallet_fund_rejects_negative_amount(client: AsyncClient, auth_header: dict[str, str]) -> None:
    resp = await client.post(
        "/wallet/fund",
        headers={**auth_header, "Idempotency-Key": str(uuid.uuid4())},
        json={"amount": "-5.00", "reference": "bad-fund"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_transfer_and_idempotency(client: AsyncClient) -> None:
    sender_token = await create_and_login(client, "sender2@example.com")
    recipient_email = "recipient2@example.com"
    await create_and_login(client, recipient_email)

    sender_headers = {"Authorization": f"Bearer {sender_token}"}
    fund_idem = str(uuid.uuid4())
    await client.post(
        "/wallet/fund",
        headers={**sender_headers, "Idempotency-Key": fund_idem},
        json={"amount": "500.00", "reference": "fund-for-transfer"},
    )

    transfer_key = str(uuid.uuid4())
    first = await client.post(
        "/wallet/transfer",
        headers={**sender_headers, "Idempotency-Key": transfer_key},
        json={"recipient_email": recipient_email, "amount": "100.00", "reference": "transfer-1"},
    )
    second = await client.post(
        "/wallet/transfer",
        headers={**sender_headers, "Idempotency-Key": transfer_key},
        json={"recipient_email": recipient_email, "amount": "100.00", "reference": "transfer-1"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


@pytest.mark.asyncio
async def test_transfer_insufficient_balance(client: AsyncClient) -> None:
    sender_token = await create_and_login(client, "sender3@example.com")
    recipient_email = "recipient3@example.com"
    await create_and_login(client, recipient_email)

    headers = {"Authorization": f"Bearer {sender_token}", "Idempotency-Key": str(uuid.uuid4())}
    resp = await client.post(
        "/wallet/transfer",
        headers=headers,
        json={"recipient_email": recipient_email, "amount": "9999.00", "reference": "too-much"},
    )

    assert resp.status_code == 400
