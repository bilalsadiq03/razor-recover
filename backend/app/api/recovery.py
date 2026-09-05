from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from typing import Optional

from app.core.database import SessionLocal
from app.models import Payment, RecoveryCase

from app.services.batch_recovery import run_batch
from app.services.recovery_executor import execute_recovery


router = APIRouter(
    prefix="/api/recovery",
    tags=["Recovery"],
)


# ============================================================
# Response Models
# ============================================================

class RecoveryCaseResponse(BaseModel):
    id: int
    payment_id: int
    transaction_id: str
    amount: float
    status: str
    recoverability: str
    recommended_action: str | None = None
    approved_action: str | None = None
    amount_at_risk: float
    amount_recovered: float


class PaymentResponse(BaseModel):
    payment_id: int
    transaction_id: str
    amount: float
    payment_status: str
    failure_reason: Optional[str] = None
    recovery_case: RecoveryCaseResponse | None


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


# ============================================================
# List Recovery Cases
# ============================================================

@router.get(
    "",
    response_model=list[RecoveryCaseResponse],
)
def list_recovery_cases(
    status: str | None = None,
    limit: int = 50,
):
    """
    Return recovery cases for the dashboard.

    Optional:
        status: filter by recovery status
        limit: maximum number of cases
    """

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100.",
        )

    db = SessionLocal()

    try:
        query = (
            select(
                RecoveryCase,
                Payment.transaction_id,
            )
            .join(
                Payment,
                Payment.id == RecoveryCase.payment_id,
            )
            .order_by(
                RecoveryCase.id.desc()
            )
            .limit(limit)
        )

        if status:
            query = query.where(
                RecoveryCase.status == status.upper()
            )

        rows = db.execute(query).all()

        return [
            RecoveryCaseResponse(
                id=case.id,
                payment_id=case.payment_id,
                transaction_id=transaction_id,
                amount=float(case.amount_at_risk),
                status=case.status,
                recoverability=case.recoverability,
                recommended_action=case.recommended_action,
                approved_action=case.approved_action,
                amount_at_risk=float(
                    case.amount_at_risk
                ),
                amount_recovered=float(
                    case.amount_recovered
                ),
            )
            for case, transaction_id in rows
        ]

    finally:
        db.close()


# ============================================================
# Get Payment + Recovery Details
# ============================================================

@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
)
def get_payment_recovery(payment_id: int):
    """
    Return payment details and its latest recovery case.
    """

    db = SessionLocal()

    try:
        payment = db.execute(
            select(Payment).where(
                Payment.id == payment_id
            )
        ).scalar_one_or_none()

        if payment is None:
            raise HTTPException(
                status_code=404,
                detail=f"Payment {payment_id} not found.",
            )

        recovery_case = db.execute(
            select(RecoveryCase)
            .where(
                RecoveryCase.payment_id
                == payment_id
            )
            .order_by(
                RecoveryCase.id.desc()
            )
        ).scalars().first()

        recovery_response = None

        if recovery_case is not None:
            recovery_response = RecoveryCaseResponse(
                id=recovery_case.id,
                payment_id=recovery_case.payment_id,
                transaction_id=payment.transaction_id,
                amount=float(
                    recovery_case.amount_at_risk
                ),
                status=recovery_case.status,
                recoverability=recovery_case.recoverability,
                recommended_action=(
                    recovery_case.recommended_action
                ),
                approved_action=(
                    recovery_case.approved_action
                ),
                amount_at_risk=float(
                    recovery_case.amount_at_risk
                ),
                amount_recovered=float(
                    recovery_case.amount_recovered
                ),
            )

        return PaymentResponse(
            payment_id=payment.id,
            transaction_id=payment.transaction_id,
            amount=float(payment.amount),
            payment_status=payment.status,
            failure_reason=payment.failure_reason,
            recovery_case=recovery_response,
        )

    finally:
        db.close()


# ============================================================
# Execute Individual Recovery
# ============================================================

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


# ============================================================
# Execute Batch Recovery
# ============================================================

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
            max_revenue_at_risk=(
                request.max_revenue_at_risk
            ),
            max_consecutive_errors=(
                request.max_consecutive_errors
            ),
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Batch recovery execution failed.",
        )