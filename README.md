# PayLedger 💳

**A Production-Grade Fintech Wallet & Transaction API**

A backend REST API that demonstrates real-world fintech infrastructure patterns used in companies like Flutterwave, Paystack, and Wise. PayLedger simulates core wallet operations with atomic transactions, idempotency, reconciliation, and enterprise-level concurrency safety.

---

## Table of Contents

- [Quick Overview](#quick-overview)
- [Architecture Design](#architecture-design)
- [System Capabilities](#system-capabilities)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Data Model](#data-model)
- [Core Design Decisions](#core-design-decisions)
- [Installation & Setup](#installation--setup)
- [API Endpoints](#api-endpoints)
- [Code Walkthrough](#code-walkthrough)
- [Running Tests](#running-tests)
- [Deployment](#deployment)
- [Learning Outcomes](#learning-outcomes)

---

## Quick Overview

Imagine you're building a payment app like Venmo or Square Cash. Your users need:
- ✅ **An account** with a wallet balance
- ✅ **Funding their wallet** (mock payment)
- ✅ **Sending money** to other users reliably
- ✅ **Tracking every transaction** immutably
- ✅ **Verifying account balances** match the ledger
- ✅ **Preventing double-spending** if a request is retried

**PayLedger handles all of this.** It's not just a toy API—every pattern here is used in production fintech systems.

---

## Architecture Design

### High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Client (Mobile/Web)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                   ┌─────────▼────────┐
                   │   FastAPI App    │ (ASGI Server)
                   │ (Uvicorn)        │
                   └────────┬─────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
      ┌──────────┐   ┌─────────────┐  ┌──────────┐
      │PostgreSQL│   │    Redis    │  │ Alembic  │
      │Database  │   │  (Cache)    │  │(Migrations)
      │(Ledger)  │   │             │  │          │
      └──────────┘   └─────────────┘  └──────────┘
```

### Request Flow: Transferring Money

```
┌─────────────────────────────────────────────────────────────────┐
│ Client: POST /wallet/transfer with Idempotency-Key              │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ Check Redis Cache  │
        │ (Idempotency Key)  │
        └────────┬───────────┘
                 │
         ┌───────┴────────┐
         │                │
      Found          Not Found
         │                │
         │        ┌───────▼──────────────┐
         │        │ Authenticate User    │
         │        └───────┬──────────────┘
         │                │
         │        ┌───────▼──────────────┐
         │        │ Load Sender Wallet   │
         │        │ (with row lock)      │
         │        └───────┬──────────────┘
         │                │
         │        ┌───────▼──────────────┐
         │        │ Load Recipient Wallet│
         │        │ (with row lock)      │
         │        └───────┬──────────────┘
         │                │
         │        ┌───────▼──────────────┐
         │        │ Check Sender Balance │
         │        └───────┬──────────────┘
         │                │
         │        ┌───────▼──────────────────┐
         │        │ Debit Sender Balance     │
         │        │ Credit Recipient Balance │
         │        │ Create 2 Ledger Entries │
         │        └───────┬──────────────────┘
         │                │
         │        ┌───────▼──────────────┐
         │        │ Commit Transaction   │
         │        └───────┬──────────────┘
         │                │
         └────────┬───────┘
                  │
         ┌────────▼────────┐
         │ Cache Response  │
         │ in Redis (24h)  │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │ Return Response │
         │ to Client       │
         └────────────────┘
```

### Service Layer Architecture

```
┌──────────────────────────────────────────────────────┐
│                   API Routers                        │
│  (auth.py, wallet.py, reconciliation.py)            │
└────────────────┬─────────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌─────────┐  ┌─────────┐  ┌──────────────────┐
│ Auth    │  │ Wallet  │  │ Reconciliation   │
│Service  │  │Service  │  │Service           │
└────┬────┘  └────┬────┘  └────┬─────────────┘
     │            │            │
     └────────────┼────────────┘
                  │
     ┌────────────┼─────────────┐
     │            │             │
     ▼            ▼             ▼
┌──────────┐  ┌──────────┐  ┌─────────────┐
│Database  │  │Idempotency
│Models    │  │Service   │  │Middleware   │
│(SQLAlchemy)  └──────────┘  └─────────────┘
└──────────┘
```

---

## System Capabilities

### 1. **User Authentication** 🔐
- User registration with email validation
- Secure password hashing with bcrypt
- JWT-based token authentication
- Token refresh mechanism

### 2. **Wallet Management** 💰
- Each user gets exactly one wallet
- Wallet holds balance in a specific currency (default: NGN)
- Non-negative balance enforced at database level
- Precision handling for monetary values (2 decimal places)

### 3. **Transactions** 📝
- **Funding**: Add money to wallet (mock action)
- **Transfer**: Send money between users P2P
- Every transaction creates an immutable ledger entry
- Transfers create 2 ledger entries: debit + credit
- Atomic operations—all or nothing

### 4. **Idempotency** 🔁
- Retry-safe endpoints using idempotency keys
- Redis caches responses for 24 hours
- Same idempotency key = same response (prevents double-spend)
- Implemented on `/fund` and `/transfer` endpoints

### 5. **Reconciliation** 🔍
- Compare wallet balances against transaction ledger
- Find discrepancies (balance ≠ ledger sum)
- Store reconciliation results with timestamps
- Run manually or on a schedule

### 6. **Concurrency Safety** 🛡️
- Row-level locking in SQL (`with_for_update()`)
- Prevents race conditions during concurrent transfers
- Transactions ordered by wallet ID to prevent deadlock
- ACID compliance via PostgreSQL

---

## Tech Stack

| Component | Technology | Why? |
|-----------|-----------|------|
| **Language** | Python 3.11+ | Modern, expressive, great for data handling |
| **Framework** | FastAPI | Async, automatic API docs, type-safe with Pydantic |
| **Web Server** | Uvicorn | ASGI server, high concurrency, built for async |
| **Database** | PostgreSQL 15+ | ACID transactions, row-level locking, JSONB support |
| **ORM** | SQLAlchemy 2.x (async) | Powerful, supports async, fine-grained control |
| **Caching** | Redis 7+ | In-memory, fast idempotency checks, session storage |
| **Migrations** | Alembic | Version control for schema, reproducible deployments |
| **Auth** | JWT + passlib | Stateless, scalable, industry standard |
| **Testing** | pytest + httpx | Async-aware, fixtures-based, comprehensive |
| **Containerization** | Docker Compose | Local dev = production environment |

---

## Project Structure

```
payledger/
├── README.md                         # This file
├── requirements.txt                  # Python dependencies
├── Dockerfile                        # Container image definition
├── docker-compose.yml                # Local dev environment
├── railway.toml                      # Railway deployment config
├── alembic.ini                       # Migration configuration
│
├── alembic/
│   ├── env.py                        # Migration environment
│   ├── script.py.mako                # Migration template
│   └── versions/                     # Generated migration files
│
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app + routes
│   ├── config.py                     # Settings from env vars
│   ├── database.py                   # Async SQLAlchemy engine
│   ├── redis_client.py               # Redis connection singleton
│   │
│   ├── models/                       # SQLAlchemy ORM models
│   │   ├── user.py                   # User entity
│   │   ├── wallet.py                 # Wallet entity + constraints
│   │   ├── transaction.py            # Transaction ledger
│   │   └── reconciliation_log.py     # Reconciliation audit trail
│   │
│   ├── schemas/                      # Pydantic request/response models
│   │   ├── user.py                   # User DTO
│   │   ├── wallet.py                 # Wallet operations DTO
│   │   └── transaction.py            # Transaction DTO
│   │
│   ├── routers/                      # FastAPI endpoints
│   │   ├── auth.py                   # Register, login
│   │   ├── wallet.py                 # Fund, balance, transfer
│   │   └── reconciliation.py         # Reconciliation endpoints
│   │
│   ├── services/                     # Business logic layer
│   │   ├── auth_service.py           # JWT + password logic
│   │   ├── wallet_service.py         # Core wallet operations
│   │   ├── idempotency.py            # Idempotency key handling
│   │   └── reconciliation_service.py # Reconciliation logic
│   │
│   └── middleware/
│       └── idempotency_middleware.py # Idempotency validation
│
└── tests/                            # Test suite
    ├── conftest.py                   # Test fixtures + DB setup
    ├── test_auth.py                  # Auth tests
    ├── test_wallet.py                # Wallet operation tests
    └── test_reconciliation.py        # Reconciliation tests
```

---

## Data Model

### Entity-Relationship Diagram

```
┌─────────────────────┐
│       Users         │
├─────────────────────┤
│ id (UUID, PK)       │
│ email (String, UQ)  │◄─────────┐
│ hashed_password     │          │
│ full_name           │          │ 1:1
│ is_active           │          │
│ created_at          │          │
└─────────────────────┘          │
                         ┌───────────────────┐
                         │     Wallets       │
                         ├───────────────────┤
                         │ id (UUID, PK)     │
                         │ user_id (FK)──────┘
                         │ balance (Decimal) │
                         │ currency          │
                         │ created_at        │
                         └────────┬──────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    │                            │
          (sender)  │ 1:N                 1:N    │ (recipient)
                    │                            │
              ┌─────▼──────────────────────────┐
              │      Transactions (Ledger)     │
              ├────────────────────────────────┤
              │ id (UUID, PK)                  │
              │ idempotency_key (String, UQ)   │
              │ type (FUND|TRANSFER_*)         │
              │ amount (Numeric)               │
              │ sender_wallet_id (FK)          │
              │ recipient_wallet_id (FK)       │
              │ status (SUCCESS|FAILED)        │
              │ reference                      │
              │ metadata_json (JSONB)          │
              │ created_at                     │
              └────────────────────────────────┘
```

### Database Schema

```sql
-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX idx_users_email ON users(email);

-- Wallets Table
CREATE TABLE wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id),
    balance NUMERIC(18, 2) NOT NULL DEFAULT 0.00
        CHECK (balance >= 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'NGN',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Transactions Table (the immutable ledger)
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key VARCHAR(255) UNIQUE,
    type VARCHAR(50) NOT NULL,  -- 'FUND', 'TRANSFER_DEBIT', 'TRANSFER_CREDIT'
    amount NUMERIC(18, 2) NOT NULL,
    sender_wallet_id UUID REFERENCES wallets(id),
    recipient_wallet_id UUID REFERENCES wallets(id),
    status VARCHAR(50) NOT NULL DEFAULT 'SUCCESS',
    reference VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX idx_transactions_sender ON transactions(sender_wallet_id);
CREATE INDEX idx_transactions_recipient ON transactions(recipient_wallet_id);
```

---

## Core Design Decisions

### Why 1: Idempotency Keys (Not Sequential IDs)

**Problem:** In fintech, network issues happen. If a client doesn't receive a response, they retry the same request. Without idempotency, you'd create duplicate transactions.

**Solution:** We use idempotency keys (provided by the client in the `Idempotency-Key` header):
- First request: Process normally, cache the response in Redis
- Retry with same key: Return cached response—no duplicate transaction

**Code Example:**
```python
@router.post("/transfer")
async def transfer(
    payload: TransferRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),  # ← Client provides this
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TransferResponse:
    # Check Redis first
    cached = await check_idempotency(redis, idempotency_key)
    if cached:
        return TransferResponse(**cached)  # ← Return instantly, no double-spend!

    # ... process transfer ...
    
    # Cache the response for 24 hours
    await store_idempotency(redis, idempotency_key, response)
    return TransferResponse(**response)
```

**Why Redis?** Sub-millisecond lookup speed. On every critical endpoint, you need idempotency checks to be *fast*.

---

### Why 2: Row-Level Locking (with_for_update())

**Problem:** Two users transfer from the same wallet at the exact same time. Without locking, you could have a race condition:
- Wallet has $100
- User A: checks balance ($100) → deducts $60 → balance = $40
- User B: checks balance ($100) → deducts $70 → balance = $30 ❌ WRONG!

**Solution:** We use database-level row locking:

```python
# Lock the wallet row, preventing concurrent modifications
wallets_result = await db.execute(
    select(Wallet)
    .where(Wallet.id.in_([sender_wallet.id, recipient_wallet.id]))
    .order_by(Wallet.id)
    .with_for_update()  # ← This locks the rows
)
locked_sender = locked_wallets[sender_wallet.id]
locked_recipient = locked_wallets[recipient_wallet.id]

# Now we check balance & deduct atomically
if locked_sender.balance < amount:
    raise HTTPException(status_code=400, detail="Insufficient balance")
locked_sender.balance -= amount
locked_recipient.balance += amount
```

**Why this order?** We sort wallets by ID before locking. This prevents **deadlock** if two transfers happen simultaneously in opposite directions.

---

### Why 3: Two Ledger Entries Per Transfer (Debit + Credit)

**Problem:** You want to know:
- How much left user A's wallet? (debit perspective)
- How much entered user B's wallet? (credit perspective)
- They should always equal!

**Solution:** Every transfer creates 2 transaction records:

```python
debit_txn = Transaction(
    idempotency_key=idempotency_key,  # Only debit gets the key
    type="TRANSFER_DEBIT",
    sender_wallet_id=locked_sender.id,
    recipient_wallet_id=locked_recipient.id,
    amount=amount,
    direction="debit",
)
credit_txn = Transaction(
    idempotency_key=None,  # Credit doesn't have a key
    type="TRANSFER_CREDIT",
    sender_wallet_id=locked_sender.id,
    recipient_wallet_id=locked_recipient.id,
    amount=amount,
    direction="credit",
)
```

This gives you an **immutable audit trail**. At any point, you can verify:
- Sum of all debits from wallet A = what left
- Sum of all credits to wallet B = what arrived
- They equal (or you've found a bug!)

---

### Why 4: Decimal Precision (Not Floats)

**Problem:** Floats have rounding errors. $0.01 + $0.02 might = $0.0300000000001

**Solution:** Use `Decimal` type:

```python
from decimal import Decimal

MONEY_QUANT = Decimal("0.01")  # 2 decimal places for currency

def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT)  # Rounds to 2 decimals

amount = _money(Decimal("100.999"))  # → Decimal('101.00')
```

Database column: `Numeric(18, 2)` = up to $9,999,999,999,999,999.99 with 2 decimals.

---

### Why 5: Async/Await (Not Synchronous)

**Problem:** With 1000 concurrent users, synchronous I/O blocks threads. You'd need 1000 threads!

**Solution:** FastAPI + async SQLAlchemy:

```python
# Doesn't block—the server handles other requests while this I/O waits
async def transfer(...):
    result = await db.execute(select(...))  # Non-blocking DB query
    await redis.get(...)                     # Non-blocking cache lookup
```

One thread can handle 1000+ concurrent connections via event loop. **Same server, 100x more capacity.**

---

### Why 6: Alembic Migrations

**Problem:** You start with 3 columns, then add 2 more. How do you sync this across dev, staging, production databases?

**Solution:** Version-controlled migrations:

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add metadata_json to transactions"

# This creates: alembic/versions/001_add_metadata.py with:
#   - upgrade() - add the column
#   - downgrade() - remove the column

# Both dev and production run the same migrations in order
alembic upgrade head
```

Result: Every environment has the *exact same* schema.

---

## Installation & Setup

### Prerequisites

- **Docker & Docker Compose** (easiest) — or
- **Python 3.11+**, PostgreSQL 15+, Redis 7+

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/payledger.git
cd payledger

# Start all services (API, PostgreSQL, Redis)
docker compose up -d

# Run migrations automatically on startup (built into app)
# API is ready at http://localhost:8000

# View API docs
open http://localhost:8000/docs
```

**How it works:**
- `docker-compose.yml` starts 3 services:
  - **API**: FastAPI app on port 8000
  - **PostgreSQL**: Database on port 5432
  - **Redis**: Cache on port 6379

- The app automatically runs `alembic upgrade head` on startup (via `lifespan` hook)
- All data persists in `postgres_data` volume

### Option 2: Local Python Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up .env file
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://payleger:payleger_pass@localhost:5432/payleger_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF

# Start PostgreSQL & Redis (separately or via docker)
docker run -d --name postgres -e POSTGRES_DB=payleger_db \
  -e POSTGRES_USER=payleger -e POSTGRES_PASSWORD=payleger_pass \
  -p 5432:5432 postgres:15

docker run -d --name redis -p 6379:6379 redis:7-alpine

# Run migrations
cd payledger
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

---

## API Endpoints

### Authentication

#### 1. Register a New User
```http
POST /auth/register
Content-Type: application/json

{
  "email": "alice@example.com",
  "password": "SecurePass123!",
  "full_name": "Alice Johnson"
}
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "alice@example.com",
  "full_name": "Alice Johnson",
  "created_at": "2026-04-10T14:30:00Z"
}
```

**What Happens Inside:**
1. Hash password with bcrypt (CPU-bound, takes ~100ms)
2. Insert user into database
3. Automatically create a wallet (balance = $0)
4. Return user details

---

#### 2. Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "alice@example.com",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**What Happens Inside:**
1. Look up user by email
2. Verify password against stored hash
3. Create JWT token (expires in 30 min)
4. Return token to client

**On Subsequent Requests:**
```http
GET /wallet/balance
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

### Wallet Operations

#### 3. Get Wallet Balance
```http
GET /wallet/balance
Authorization: Bearer <token>
```

**Response:**
```json
{
  "wallet_id": "660e8400-e29b-41d4-a716-446655440000",
  "balance": "5000.50",
  "currency": "NGN"
}
```

**No Side Effects** — just a read operation.

---

#### 4. Fund Wallet (Add Money)
```http
POST /wallet/fund
Authorization: Bearer <token>
Idempotency-Key: fund-alice-001
Content-Type: application/json

{
  "amount": "5000.00",
  "reference": "initial_load"
}
```

**Response:**
```json
{
  "transaction_id": "770e8400-e29b-41d4-a716-446655440000",
  "new_balance": "5000.00"
}
```

**What Happens Inside:**

1. **Extract token from header** → Get Alice's user_id
2. **Check idempotency cache** → Is `"fund-alice-001"` already in Redis?
   - **Yes?** Return cached response instantly (same `transaction_id`, no new ledger entry)
   - **No?** Continue...
3. **Load wallet** with row lock (`with_for_update()`)
4. **Add amount to balance:**
   - Old balance: $0.00
   - Add: $5,000.00
   - New balance: $5,000.00
5. **Create transaction record** (type: `FUND`)
6. **Commit atomically** to database
7. **Cache response** in Redis for 24 hours
8. **Return response**

**Retry Scenario:** If Alice's network drops, she retries with same key:
- Step 2 finds it in cache → instant response with original `transaction_id`
- **No duplicate ledger entry!**

---

#### 5. Transfer Money to Another User

```http
POST /wallet/transfer
Authorization: Bearer <token>
Idempotency-Key: transfer-to-bob-001
Content-Type: application/json

{
  "recipient_email": "bob@example.com",
  "amount": "1500.00",
  "reference": "payment_for_groceries"
}
```

**Response:**
```json
{
  "transaction_id": "880e8400-e29b-41d4-a716-446655440000",
  "new_balance": "3500.00"
}
```

**What Happens Inside (Complex!):**

```python
# 1. Authentication
current_user = get_current_user(token)
# → Returns: User(id='alice-uuid', email='alice@example.com')

# 2. Idempotency Check
cached = await check_idempotency(redis, 'transfer-to-bob-001')
# → Check Redis for key 'idempotency:transfer-to-bob-001'
# → If found, return it immediately

# 3. Load Sender Wallet with Row Lock
sender_wallet = await db.execute(
    select(Wallet)
    .where(Wallet.id == alice_wallet_id)
    .with_for_update()  # ← Lock this row!
)
# → Alice can't make 2 transfers simultaneously

# 4. Find Recipient
recipient_user = await db.execute(
    select(User).where(User.email == 'bob@example.com')
)
# → Throws 404 if Bob doesn't exist

# 5. Load Recipient Wallet with Row Lock (Sorted by ID to prevent deadlock)
wallets = await db.execute(
    select(Wallet)
    .where(Wallet.id.in_([alice_wallet.id, bob_wallet.id]))
    .order_by(Wallet.id)  # ← Important for concurrency!
    .with_for_update()
)

# 6. Validate Balance
if alice_wallet.balance < Decimal('1500.00'):
    raise HTTPException(400, "Insufficient balance")

# 7. Update Balances Atomically
alice_wallet.balance -= Decimal('1500.00')  # $5000 → $3500
bob_wallet.balance += Decimal('1500.00')    # $2000 → $3500

# 8. Create 2 Ledger Entries
debit_txn = Transaction(
    idempotency_key='transfer-to-bob-001',  # Only debit has the key
    type='TRANSFER_DEBIT',
    sender_wallet_id=alice_wallet.id,
    recipient_wallet_id=bob_wallet.id,
    amount=Decimal('1500.00'),
    status='SUCCESS'
)
credit_txn = Transaction(
    idempotency_key=None,  # Credit doesn't have the key
    type='TRANSFER_CREDIT',
    sender_wallet_id=alice_wallet.id,
    recipient_wallet_id=bob_wallet.id,
    amount=Decimal('1500.00'),
    status='SUCCESS'
)

# 9. Commit All Changes Atomically
db.add_all([debit_txn, credit_txn])
await db.commit()  # Either all succeed or all rollback

# 10. Cache Response & Return
await store_idempotency(redis, 'transfer-to-bob-001', response)
return TransferResponse(
    transaction_id='880e8400...',
    new_balance='3500.00'
)
```

**Edge Cases Handled:**
- Bob doesn't exist → 404
- Bob's wallet missing → 404 (shouldn't happen; created on user registration)
- Alice has insufficient balance → 400
- Alice & Bob are same person → 400
- Concurrent transfers from Alice → queued (row lock)
- Retry with same key → cached response returned

---

### Reconciliation

#### 6. Run Reconciliation Check
```http
POST /reconciliation/run
Authorization: Bearer <token>
```

**Response:**
```json
{
  "wallets_checked": 42,
  "discrepancies_found": 0,
  "details": []
}
```

If there *were* discrepancies:
```json
{
  "wallets_checked": 42,
  "discrepancies_found": 1,
  "details": [
    {
      "wallet_id": "660e8400-e29b-41d4-a716-446655440000",
      "wallet_balance": "5000.00",
      "ledger_total": "4500.00",
      "difference": "500.00",
      "created_at": "2026-04-10T14:30:00Z"
    }
  ]
}
```

**What This Means:**
- Wallet thinks it has $5,000
- But ledger says only $4,500 shouldbe there
- Difference: $500 discrepancy 🚨

**Why Use This?** To catch bugs early:
- Database corruption? Reconciliation finds it.
- Code bug causing wrong balance? Caught before it cascades.
- Lost transaction? Auditable in the ledger.

---

#### 7. Get Reconciliation Logs
```http
GET /reconciliation/logs?limit=50&offset=0
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": "990e8400-e29b-41d4-a716-446655440000",
    "wallet_id": "660e8400-e29b-41d4-a716-446655440000",
    "wallet_balance": "5000.00",
    "ledger_total": "5000.00",
    "difference": "0.00",
    "created_at": "2026-04-10T14:30:00Z"
  }
]
```

**Pagination:** `limit` (max 100), `offset` for cursor-based pagination.

---

## Code Walkthrough

### How the App Starts

**[app/main.py](app/main.py):**

```python
from contextlib import asynccontextmanager
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from app.routers import auth, reconciliation, wallet

# Lifespan: runs on app startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run database migrations before first request
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    yield  # App is now running
    # (cleanup code here if needed)

app = FastAPI(
    title="PayLedger API",
    description="Fintech wallet and transaction API",
    version="0.1.0",
    lifespan=lifespan,  # Run migrations on startup
)

# Mount routers (groups endpoints)
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
app.include_router(reconciliation.router, prefix="/reconciliation", tags=["Reconciliation"])

@app.get("/health")
async def healthcheck():
    return {"status": "ok", "service": "payledger"}
```

**Order of Operations:**
1. FastAPI creates app instance
2. On `uvicorn app.main:app`, the lifespan context is entered
3. Alembic runs migrations (`CREATE TABLE users IF NOT EXISTS ...`)
4. Server starts listening on :8000
5. First request comes in

---

### How Authentication Works

**[app/services/auth_service.py](app/services/auth_service.py) (excerpt):**

```python
from passlib.context import CryptContext
from python_jose import jwt
from datetime import timedelta

# PasswordContext handles bcrypt hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def register_user(db: AsyncSession, email: str, password: str, full_name: str):
    # Hash the password (takes ~100ms, very secure)
    hashed_pwd = pwd_context.hash(password)
    
    # Create user
    user = User(
        email=email,
        hashed_password=hashed_pwd,
        full_name=full_name
    )
    db.add(user)
    
    # Create wallet automatically
    wallet = Wallet(
        user_id=user.id,
        balance=Decimal("0.00"),
        currency="NGN"
    )
    db.add(wallet)
    await db.commit()
    return user

async def login_user(db: AsyncSession, email: str, password: str):
    # Find user by email
    user = await db.execute(select(User).where(User.email == email))
    user = user.scalar_one_or_none()
    
    if not user or not pwd_context.verify(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}

# This is called on protected endpoints
async def get_current_user(token: str = Depends(HTTPBearer())) -> User:
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        
        user = await db.execute(select(User).where(User.id == user_id))
        user = user.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**Security Layer:**
- Passwords never stored in plain text (bcrypt hash)
- JWT tokens expire (30 min default)
- Every protected endpoint calls `get_current_user(token)` via dependency injection

---

### How a Transaction is Created (The Complex Part)

**[app/services/wallet_service.py](app/services/wallet_service.py):**

```python
async def transfer_funds(
    db: AsyncSession,
    sender_wallet: Wallet,
    recipient_email: str,
    amount: Decimal,
    idempotency_key: str,
    reference: str | None,
) -> tuple[Transaction, Decimal]:
    
    amount = _money(amount)  # Quantize to 2 decimals
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be > 0")
    
    try:
        # 1. Find recipient
        recipient_user = await db.execute(
            select(User).where(User.email == recipient_email)
        )
        recipient_user = recipient_user.scalar_one_or_none()
        if not recipient_user:
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        # 2. Get recipient wallet
        recipient_wallet_result = await db.execute(
            select(Wallet).where(Wallet.user_id == recipient_user.id)
        )
        recipient_wallet = recipient_wallet_result.scalar_one_or_none()
        if not recipient_wallet:
            raise HTTPException(status_code=404, detail="Recipient wallet not found")
        
        # 3. Prevent self-transfer
        if recipient_wallet.id == sender_wallet.id:
            raise HTTPException(status_code=400, detail="Cannot transfer to yourself")
        
        # 4. CRITICAL: Lock wallets in sorted order (prevents deadlock)
        wallets_result = await db.execute(
            select(Wallet)
            .where(Wallet.id.in_([sender_wallet.id, recipient_wallet.id]))
            .order_by(Wallet.id)  # ← Ordered lock acquisition
            .with_for_update()     # ← Row-level lock
        )
        locked_wallets = {w.id: w for w in wallets_result.scalars().all()}
        locked_sender = locked_wallets[sender_wallet.id]
        locked_recipient = locked_wallets[recipient_wallet.id]
        
        # 5. Check balance
        if locked_sender.balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        # 6. Update balances
        locked_sender.balance = _money(locked_sender.balance - amount)
        locked_recipient.balance = _money(locked_recipient.balance + amount)
        
        # 7. Create ledger entries (debit + credit)
        debit_txn = Transaction(
            idempotency_key=idempotency_key,  # Debit is idempotent
            type="TRANSFER_DEBIT",
            amount=amount,
            sender_wallet_id=locked_sender.id,
            recipient_wallet_id=locked_recipient.id,
            status="SUCCESS",
            reference=reference,
            metadata_json={"direction": "debit"},
        )
        credit_txn = Transaction(
            idempotency_key=None,  # Credit doesn't have a key
            type="TRANSFER_CREDIT",
            amount=amount,
            sender_wallet_id=locked_sender.id,
            recipient_wallet_id=locked_recipient.id,
            status="SUCCESS",
            reference=reference,
            metadata_json={"direction": "credit"},
        )
        
        # 8. Add to session (not committed yet)
        db.add_all([debit_txn, credit_txn])
        await db.flush()  # Execute DDL/DML
        
        # 9. Commit atomically (all-or-nothing)
        await db.commit()
        
    except Exception:
        # If anything fails, rollback all changes
        await db.rollback()
        raise
    
    # 10. Return debit txn (sender cares about money leaving)
    await db.refresh(debit_txn)
    return debit_txn, locked_sender.balance
```

**Why Each Step is Critical:**

| Step | Why |
|------|-----|
| Quantize amount | Prevent floating-point errors ($0.01 + $0.02 ≠ $0.03 in floats) |
| Check recipient exists | Fail early before starting transaction |
| Ordered lock acquisition | Prevent A→B & B→A deadlock |
| Row-level lock | Prevent concurrent conflicting updates |
| Check balance | Fail if insufficient |
| Create 2 ledger entries | Audit trail: money out ≠ money in means bug |
| db.flush() | Execute but don't commit yet |
| db.commit() | All-or-nothing atomicity |
| Rollback on exception | No partial transactions |

---

### How Reconciliation Works

**[app/services/reconciliation_service.py](app/services/reconciliation_service.py):**

```python
async def run_reconciliation(db: AsyncSession) -> tuple[int, list]:
    # 1. Get all wallets
    wallets_result = await db.execute(select(Wallet))
    wallets = wallets_result.scalars().all()
    
    discrepancies = []
    
    for wallet in wallets:
        # 2. Sum all transactions (debits + credits)
        
        # Sum of money that went OUT (debits)
        debits_result = await db.execute(
            select(func.sum(Transaction.amount))
            .where(
                (Transaction.type == "TRANSFER_DEBIT") |
                (Transaction.type == "FUND")
            )
            .where(Transaction.sender_wallet_id == wallet.id)
        )
        debits = debits_result.scalar() or Decimal("0.00")
        
        # Sum of money that came IN (credits)
        credits_result = await db.execute(
            select(func.sum(Transaction.amount))
            .where(Transaction.type == "TRANSFER_CREDIT")
            .where(Transaction.recipient_wallet_id == wallet.id)
        )
        credits = credits_result.scalar() or Decimal("0.00")
        
        # 3. Calculate expected balance
        ledger_total = credits - debits
        
        # 4. Compare
        difference = wallet.balance - ledger_total
        
        if difference != 0:  # Discrepancy found!
            discrepancies.append({
                "wallet_id": wallet.id,
                "wallet_balance": wallet.balance,
                "ledger_total": ledger_total,
                "difference": difference,
            })
            
            # Log for audit
            log = ReconciliationLog(
                wallet_id=wallet.id,
                wallet_balance=wallet.balance,
                ledger_total=ledger_total,
                difference=difference,
            )
            db.add(log)
    
    await db.commit()
    return len(wallets), discrepancies
```

**Example:**

Alice's wallet has these transactions:
- FUND: +$5,000
- TRANSFER_DEBIT: -$1,500
- TRANSFER_CREDIT (to Bob): this doesn't affect Alice

**Calculation:**
- Credits to Alice: $5,000 (FUND only)
- Debits from Alice: $1,500 (TRANSFER_DEBIT)
- Ledger total should be: $5,000 - $1,500 = $3,500

**If wallet balance says $3,500:** ✅ Reconciles!
**If wallet balance says $4,000:** 🚨 Discrepancy of $500!

---

## Running Tests

### Test Structure

```bash
tests/
├── conftest.py              # Shared fixtures & setup
├── test_auth.py             # Auth endpoint tests
├── test_wallet.py           # Wallet operation tests
└── test_reconciliation.py   # Reconciliation tests
```

### Run All Tests

```bash
# With coverage report
pytest tests/ --cov=app --cov-report=html

# With verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_wallet.py -v

# Run specific test function
pytest tests/test_wallet.py::test_fund_wallet -v

# Run with output capture disabled (see print statements)
pytest tests/ -s
```

### Test Example: Fund Wallet

**[tests/test_wallet.py](tests/test_wallet.py):**

```python
@pytest.mark.asyncio
async def test_fund_wallet(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_token: str,
):
    """Test funding a wallet successfully."""
    
    # Setup
    response = await client.post(
        "/wallet/fund",
        json={"amount": "1000.00", "reference": "test_fund"},
        headers={
            "Authorization": f"Bearer {test_token}",
            "Idempotency-Key": "fund-test-001",
        },
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "transaction_id" in data
    assert data["new_balance"] == "1000.00"
    
    # Verify in database
    wallet = await get_wallet_for_user(db_session, test_user.id)
    assert wallet.balance == Decimal("1000.00")


@pytest.mark.asyncio
async def test_fund_wallet_idempotency(
    client: AsyncClient,
    test_user: User,
    test_token: str,
):
    """Test that retry with same key returns cached response."""
    
    # First request
    response1 = await client.post(
        "/wallet/fund",
        json={"amount": "500.00", "reference": "test"},
        headers={
            "Authorization": f"Bearer {test_token}",
            "Idempotency-Key": "fund-idempotent-001",
        },
    )
    txn_id_1 = response1.json()["transaction_id"]
    
    # Retry with same key
    response2 = await client.post(
        "/wallet/fund",
        json={"amount": "500.00", "reference": "test"},
        headers={
            "Authorization": f"Bearer {test_token}",
            "Idempotency-Key": "fund-idempotent-001",
        },
    )
    txn_id_2 = response2.json()["transaction_id"]
    
    # Should return same transaction ID (from cache)
    assert txn_id_1 == txn_id_2
    assert response2.status_code == 200
```

**What This Tests:**
1. Fund endpoint returns 200 OK
2. Balance updates correctly in database
3. Retry with same idempotency key returns cached response (no duplicate transaction)

### Run Tests

```bash
# Start services
docker compose up -d

# Run tests
pytest tests/ -v

# Expected output:
# tests/test_auth.py::test_register_user PASSED
# tests/test_wallet.py::test_fund_wallet PASSED
# tests/test_wallet.py::test_transfer_funds PASSED
# tests/test_wallet.py::test_fund_wallet_idempotency PASSED
# tests/test_reconciliation.py::test_run_reconciliation PASSED
```

---

## Deployment

### Deploy to Railway (Production)

Railway is a simple PaaS that runs Docker containers. No credit card required. 

#### Step 1: Prepare Repository

```bash
# Push to GitHub
git add .
git commit -m "Ready for deployment"
git push origin main
```

#### Step 2: Create railway.toml

```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

#### Step 3: Update Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway injects $PORT automatically
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

#### Step 4: Add Environment Variables

On Railway UI, set:
```
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://user:pass@host:6379
SECRET_KEY=<generate random key>
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### Step 5: Deploy

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login & deploy
railway login
railway up
```

**Result:** Your API is live at `https://payledger-production.railway.app`

**Swagger Docs:** `https://payledger-production.railway.app/docs`

---

### Environment Variables Explained

**.env (Local Development)**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://payleger:payleger_pass@localhost:5432/payleger_db

# Redis (cache + idempotency)
REDIS_URL=redis://localhost:6379/0

# JWT secret (encrypt tokens)
SECRET_KEY=your-secret-key-here-min-32-chars

# When tokens expire (minutes)
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**How to Generate SECRET_KEY:**
```python
import secrets
print(secrets.token_urlsafe(32))
# Output: "xlPz9qK2_mN8rT7vW4bC5dF6gH9jL1oP"
```

---

## Learning Outcomes

After building PayLedger, you understand:

### Backend Architecture 🏗️
- **Layered architecture**: routers → services → database models
- **Dependency injection**: FastAPI's `Depends()` for clean code
- **Middleware**: Request processing pipeline

### Database Design 🗄️
- **ACID transactions**: Atomicity, Consistency, Isolation, Durability
- **Row-level locking**: Preventing race conditions
- **Schema migrations**: Version-controlled database changes
- **Indexing**: Query optimization on large datasets

### Fintech Patterns 💰
- **Idempotency**: Retry-safe operations
- **Immutable ledgers**: Audit trails vs mutable state
- **Reconciliation**: Detecting bugs in production
- **Precision handling**: `Decimal` vs `float` for money

### Async/Concurrency ⚡
- **Event loops**: Handling 1000+ concurrent connections
- **Non-blocking I/O**: `await` for database & cache
- **Race conditions**: Real-world concurrency bugs & fixes

### Testing & DevOps 🧪
- **Unit tests**: pytest fixtures, async testing
- **Integration tests**: Full HTTP endpoint testing
- **Containerization**: Docker & Docker Compose
- **CI/CD**: Automated deployments

### Security 🔐
- **Password hashing**: bcrypt + salt
- **JWT tokens**: Stateless authentication
- **SQL injection**: SQLAlchemy parameterization
- **Input validation**: Pydantic schemas

---

## Quick Reference

### Common Commands

```bash
# Development
docker compose up -d              # Start all services
docker compose logs -f            # View logs

# Testing
pytest tests/ -v                  # Run all tests
pytest tests/test_wallet.py -v   # Run specific file

# Database
alembic upgrade head              # Apply migrations
alembic downgrade -1              # Rollback 1 migration
alembic revision --autogenerate -m "Add column"  # Create migration

# API
curl -X GET http://localhost:8000/health
open http://localhost:8000/docs   # Interactive API docs
```

### API Base URL
- **Local:** `http://localhost:8000`
- **Production (Railway):** `https://payledger-production.railway.app`

### Key Files to Know

| File | Purpose |
|------|---------|
| [app/main.py](app/main.py) | FastAPI app entry point |
| [app/models/](app/models/) | Database ORM definitions |
| [app/services/wallet_service.py](app/services/wallet_service.py) | Core transaction logic |
| [app/routers/wallet.py](app/routers/wallet.py) | API endpoints |
| [tests/conftest.py](tests/conftest.py) | Test setup & fixtures |
| [docker-compose.yml](docker-compose.yml) | Local dev environment |

---

## Contributing

This is a learning project. To extend it:

1. **New Feature**: Create branch `feature/your-feature`
2. **Make Changes**: Add models → services → routers
3. **Write Tests**: Test your new functionality
4. **Update Migrations**: `alembic revision --autogenerate`
5. **Submit PR**: Push to GitHub, open PR

---

## Resources & References

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **SQLAlchemy 2.0**: https://docs.sqlalchemy.org/
- **Evernote's Wallet Service**: Real-world fintech architecture
- **Idempotency Patterns**: https://stripe.com/blog/idempotency
- **ACID Transactions**: https://en.wikipedia.org/wiki/ACID

---

## License

MIT License. Feel free to use this project as a learning resource.

---

## Contact & Questions

**Built by:** Shaib God'sfavour  
**GitHub:** https://github.com/yourusername  
**Portfolio:** https://yourportfolio.com

For questions, open an issue or reach out!

---

**Last Updated:** April 2026  
**Status:** ✅ Production-ready (learning project)
