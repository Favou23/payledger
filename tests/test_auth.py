import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_login_and_me(client: AsyncClient) -> None:
    register_payload = {"email": "user@example.com", "password": "strongpassword", "full_name": "User One"}
    register_resp = await client.post("/auth/register", json=register_payload)
    assert register_resp.status_code == 201

    duplicate_resp = await client.post("/auth/register", json=register_payload)
    assert duplicate_resp.status_code == 409

    login_resp = await client.post(
        "/auth/login", json={"email": register_payload["email"], "password": register_payload["password"]}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    me_resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == register_payload["email"]


@pytest.mark.asyncio
async def test_login_fails_with_wrong_password(client: AsyncClient) -> None:
    await client.post("/auth/register", json={"email": "fail@example.com", "password": "correctpass", "full_name": "Fail"})
    login_resp = await client.post("/auth/login", json={"email": "fail@example.com", "password": "wrongpass"})
    assert login_resp.status_code == 401


@pytest.mark.asyncio
async def test_balance_after_registration(client: AsyncClient) -> None:
    await client.post("/auth/register", json={"email": "bal@example.com", "password": "strongpassword", "full_name": "Bal"})
    login = await client.post("/auth/login", json={"email": "bal@example.com", "password": "strongpassword"})
    token = login.json()["access_token"]

    balance = await client.get("/wallet/balance", headers={"Authorization": f"Bearer {token}"})
    assert balance.status_code == 200
    assert str(balance.json()["balance"]) == "0.00"
    assert uuid.UUID(balance.json()["wallet_id"])
