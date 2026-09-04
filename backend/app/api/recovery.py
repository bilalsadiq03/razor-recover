from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Payment, RecoveryCase
from app.services.recovery_executor import execute_recovery

router = APIRouter(
    prefix="/api/recovery",
    tags=["Recovery"],
)


@router.get("/{payment_id}")
def get_recovery_case(payment_id: int):
    db = SessionLocal()

    try:
        payment = db.execute(
            select(Payment)
            .where(Payment.id == payment_id)
        ).scalar_one_or_none()

        if payment is None:
            raise HTTPException(
                status_code=404,
                detail=f"Payment {payment_id} not found.",
            )

        recovery_case = db.execute(
            select(RecoveryCase)
            .where(
                RecoveryCase.payment_id == payment_id
            )
            .order_by(RecoveryCase.id.desc())
        ).scalars().first()

        if recovery_case is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No recovery case found "
                    f"for payment {payment_id}."
                ),
            )

        return {
            "payment_id": payment.id,
            "transaction_id": payment.transaction_id,
            "amount": float(payment.amount),
            "payment_status": payment.status,
            "failure_reason": payment.failure_reason,

            "recovery_case": {
                "id": recovery_case.id,
                "status": recovery_case.status,
                "recoverability": (
                    recovery_case.recoverability
                ),
                "recommended_action": (
                    recovery_case.recommended_action
                ),
                "approved_action": (
                    recovery_case.approved_action
                ),
                "amount_at_risk": float(
                    recovery_case.amount_at_risk
                ),
                "amount_recovered": float(
                    recovery_case.amount_recovered
                ),
                "created_at": (
                    recovery_case.created_at
                    .isoformat()
                    if recovery_case.created_at
                    else None
                ),
                "resolved_at": (
                    recovery_case.resolved_at
                    .isoformat()
                    if recovery_case.resolved_at
                    else None
                ),
            },
        }

    finally:
        db.close()

@router.post("/{payment_id}/execute")
def execute_payment_recovery(payment_id: int):
    try:
        result = execute_recovery(payment_id)

        return {
            "success": True,
            "result": result,
        }

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