from fastapi import FastAPI

app = FastAPI (
    title="RazorRecover API",
    description="Autonomous Revenue Recovery Agent",
    version="0.1.0",
)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "RazorRecover API",
    }
