from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.batch_recovery import run_batch
from app.services.recovery_executor import execute_recovery


router = APIRouter(
    prefix="/api/recovery",
    tags=["Recovery"],
)


class BatchRecoveryRequest(BaseModel):
    batch_size: int = Field(
        default=3,
        ge=1,
        le=100,
    )

    delay_seconds: float = Field(
        default=15.0,
        ge=0,
    )

    max_revenue_at_risk: float = Field(
        default=100000.0,
        gt=0,
    )

    max_consecutive_errors: int = Field(
        default=3,
        ge=1,
        le=10,
    )


@router.post("/{payment_id}/execute")
def execute_payment_recovery(payment_id: int):
    """
    Execute the autonomous recovery workflow
    for one failed payment.
    """

    try:
        return execute_recovery(payment_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


@router.post("/batch")
def execute_batch_recovery(
    request: BatchRecoveryRequest,
):
    """
    Execute a controlled batch recovery run.
    """

    try:
        return run_batch(
            batch_size=request.batch_size,
            delay_seconds=request.delay_seconds,
            max_revenue_at_risk=request.max_revenue_at_risk,
            max_consecutive_errors=request.max_consecutive_errors,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )