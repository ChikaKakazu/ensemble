"""FastAPI Demo Application for Ensemble Phase 2 Testing."""
from fastapi import FastAPI

app = FastAPI(
    title="Demo API",
    description="CRUD API for testing Ensemble parallel execution",
    version="0.1.0"
)


# Import and include routers after they are created by workers
def include_routers():
    """Include all route modules. Call after workers complete."""
    try:
        from demo_api.routes import create, read, update, delete
        app.include_router(create.router, tags=["Create"])
        app.include_router(read.router, tags=["Read"])
        app.include_router(update.router, tags=["Update"])
        app.include_router(delete.router, tags=["Delete"])
    except ImportError as e:
        print(f"Note: Some routes not yet available: {e}")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Demo API is running"}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}
