from fastapi import FastAPI

from app.routers import auth, reconciliation, wallet

app = FastAPI(title="PayLedger API", version="0.1.0")

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
app.include_router(reconciliation.router, prefix="/reconciliation", tags=["Reconciliation"])


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
