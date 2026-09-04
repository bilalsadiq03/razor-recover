from fastapi import FastAPI

from app.api.recovery import router as recovery_router


app = FastAPI(
    title="RazorRecover API",
    description="Autonomous Revenue Recovery Agent",
    version="0.1.0",
)


app.include_router(recovery_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "RazorRecover API",
    }