from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI

from app.routers import auth, reconciliation, wallet


@asynccontextmanager
async def lifespan(app: FastAPI):
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    yield


app = FastAPI(
    title="PayLedger API",
    description="Fintech wallet and transaction API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
app.include_router(reconciliation.router, prefix="/reconciliation", tags=["Reconciliation"])


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": "payledger"}
