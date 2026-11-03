import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database.session import engine, Base, SessionLocal
from app.services.seed_data import seed_induspilot_demonstration_data

# Import API Routers
from app.api.v1.suppliers import router as suppliers_router
from app.api.v1.materials import router as materials_router
from app.api.v1.bom import router as bom_router
from app.api.v1.quotations import router as quotations_router
from app.api.v1.compare import router as compare_router
from app.api.v1.costing import router as costing_router
from app.api.v1.optimizer import router as optimizer_router
from app.api.v1.negotiation import router as negotiation_router
from app.api.v1.customer_quotes import router as customer_quotes_router
from app.api.v1.copilot import router as copilot_router
from app.api.v1.approvals import router as approvals_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.demo import router as demo_router
from app.api.v1.documents import router as documents_router

# Ensure all tables exist on import
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables and auto-seed if empty
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_induspilot_demonstration_data(db, force_reset=False)
    finally:
        db.close()
    yield
    # Shutdown

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="IndusPilot — Agentic AI for Intelligent Manufacturing Procurement & Quotation Optimisation",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
v1_prefix = settings.API_V1_STR
app.include_router(dashboard_router, prefix=f"{v1_prefix}/dashboard", tags=["Dashboard"])
app.include_router(suppliers_router, prefix=f"{v1_prefix}/suppliers", tags=["Suppliers"])
app.include_router(materials_router, prefix=f"{v1_prefix}/materials", tags=["Materials & Inventory"])
app.include_router(bom_router, prefix=f"{v1_prefix}/bom", tags=["Bill of Materials"])
app.include_router(documents_router, prefix=f"{v1_prefix}/documents", tags=["Document Processing"])
app.include_router(quotations_router, prefix=f"{v1_prefix}/quotations", tags=["Quotation Intelligence"])
app.include_router(compare_router, prefix=f"{v1_prefix}/compare", tags=["Supplier Comparison"])
app.include_router(costing_router, prefix=f"{v1_prefix}/costing", tags=["Manufacturing Costing"])
app.include_router(optimizer_router, prefix=f"{v1_prefix}/optimizer", tags=["Procurement Optimization"])
app.include_router(negotiation_router, prefix=f"{v1_prefix}/negotiation", tags=["Autonomous Negotiation"])
app.include_router(customer_quotes_router, prefix=f"{v1_prefix}/customer-quotes", tags=["Customer Quotations"])
app.include_router(copilot_router, prefix=f"{v1_prefix}/copilot", tags=["AI Copilot"])
app.include_router(approvals_router, prefix=f"{v1_prefix}/approvals", tags=["Human Approvals"])
app.include_router(demo_router, prefix=f"{v1_prefix}/demo", tags=["Demo & Scenarios"])

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "simulation_mode": settings.SIMULATION_MODE
    }

@app.get("/")
def root():
    return {
        "message": "IndusPilot API is running.",
        "documentation": "/docs",
        "hackathon": "Tech4Bharat 2026",
        "problem_statement": "4.1 Raw Material Procurement & Manufacturing Quotation Optimisation"
    }
