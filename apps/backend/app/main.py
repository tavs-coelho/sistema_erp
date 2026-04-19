from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import SessionLocal
from .routers import accounting, auth, budget, core, employee_portal, hr, patrimony, procurement, public
from .seed import seed_data

app = FastAPI(title="Sistema ERP Municipal", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(core.router)
app.include_router(accounting.router)
app.include_router(procurement.router)
app.include_router(budget.router)
app.include_router(public.router)
app.include_router(hr.router)
app.include_router(employee_portal.router)
app.include_router(patrimony.router)


@app.get("/")
def healthcheck():
    return {"name": "Sistema ERP Municipal", "status": "ok"}


@app.on_event("startup")
def startup_seed():
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()
