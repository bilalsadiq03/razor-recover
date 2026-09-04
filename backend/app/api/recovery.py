from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.batch_recovery import run_batch
from app.services.recovery_executor import execute_recovery


router = APIRouter(
    prefix="/api/recovery",
    tags=["Recovery"],
)


class RecoveryExecutionResponse(BaseModel):
    payment_id: int
    transaction_id: str
    recovery_case_id: int
    ai_action: str
    approved_action: str | None = None
    confidence: float
    allowed: bool
    status: str
    amount_recovered: float
    reason: str


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


class BatchRecoveryResponse(BaseModel):
    cases_found: int
    cases_processed: int
    successful_recoveries: int
    failed_recoveries: int
    policy_blocked: int
    deferred: int
    not_selected: int
    revenue_at_risk: float
    revenue_recovered: float
    recovery_rate: float
    revenue_recovery_rate: float
    stop_reason: str


@router.post(
    "/{payment_id}/execute",
    response_model=RecoveryExecutionResponse,
)
def execute_payment_recovery(payment_id: int):
    """Execute recovery for one failed payment."""

    try:
        return execute_recovery(payment_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Recovery execution failed.",
        )


@router.post(
    "/batch",
    response_model=BatchRecoveryResponse,
)
def execute_batch_recovery(
    request: BatchRecoveryRequest,
):
    """Execute a controlled batch recovery run."""

    try:
        return run_batch(
            batch_size=request.batch_size,
            delay_seconds=request.delay_seconds,
            max_revenue_at_risk=request.max_revenue_at_risk,
            max_consecutive_errors=request.max_consecutive_errors,
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Batch recovery execution failed.",
        )