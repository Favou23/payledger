# PayLedger - Wallet and Transaction API

A fintech-grade wallet service built with FastAPI, PostgreSQL, Redis, and async SQLAlchemy.
*application deployed on AWS*S

## What We Are Building
- JWT-authenticated users with one wallet each
- Wallet funding and peer-to-peer transfers
- Atomic transfer execution (debit and credit in a single transaction)
- Idempotency keys on mutating endpoints
- Immutable ledger entries
- Reconciliation endpoint to detect wallet/ledger mismatches

## Stack
- Python 3.11+
- FastAPI 0.111+
- SQLAlchemy 2.x (async)
- PostgreSQL 15+
- Redis 7+
- Alembic
- Pytest + HTTPX
- Docker + Docker Compose
- GitHub Actions

## Project Structure
- `app/` main API code
- `tests/` integration-style tests
- `alembic/` migrations
- `.github/workflows/ci.yml` CI pipeline

## Run Locally
1. Create env file:
```bash
cp .env.example .env
```
2. Fill `SECRET_KEY` in `.env` using:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
3. Start services:
```bash
docker compose up --build
```
4. Run migrations (after containers are up):
```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```
5. Open docs:
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

<!-- ## Learning Mode (How We Build So You Understand)
Use this checklist every phase:
1. Read the target service file before running requests.
2. Predict expected DB changes.
3. Run request from Swagger/Postman.
4. Verify DB rows in PostgreSQL.
5. Explain in your own words what happened.

## Checkpoints
### After Models/Migrations
- Explain migration vs model.
- Explain SQLAlchemy models vs Pydantic schemas.

### After Wallet Core
- Explain why `NUMERIC(18,2)` is used for money.
- Explain what rollback guarantees in atomic transfer.
- Explain how idempotency prevents duplicate charges.

### After Tests
- Explain how `conftest.py` isolates test behavior.
- Explain why `--tb=short` improves test output readability. -->

## Endpoints
### Auth
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

### Wallet
- `GET /wallet/balance`
- `POST /wallet/fund` (`Idempotency-Key` required)
- `POST /wallet/transfer` (`Idempotency-Key` required)

### Reconciliation
- `POST /reconciliation/run`
- `GET /reconciliation/logs`

## Notes
- Transactions table is append-only in app logic.
- Reconciliation logs are persisted for auditability.
- Redis stores idempotency responses for 24 hours by default.
