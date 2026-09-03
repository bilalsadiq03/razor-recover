from sqlalchemy import select, func

from app.core.database import SessionLocal
from app.models import (
    Payment,
    Customer,
    Subscription,
    RecoveryCase,
)

from app.services.recovery_scoring import (
    calculate_recovery_score,
)


def scan_failed_payments():

    db = SessionLocal()

    try:
        failed_payments = db.scalars(
            select(Payment)
            .where(Payment.status == "FAILED")
        ).all()

        print(
            f"Found {len(failed_payments)} failed payments."
        )

        created = 0

        for payment in failed_payments:

            customer = db.get(
                Customer,
                payment.customer_id,
            )

            if customer is None:
                continue

            active_subscription = db.scalar(
                select(
                    func.count(Subscription.id)
                )
                .where(
                    Subscription.customer_id
                    == customer.id
                )
                .where(
                    Subscription.status
                    == "ACTIVE"
                )
            )

            has_active_subscription = (
                active_subscription > 0
            )

            result = calculate_recovery_score(
                amount=payment.amount,
                failure_reason=payment.failure_reason,
                successful_payments=(
                    customer.successful_payments
                ),
                failed_payments=(
                    customer.failed_payments
                ),
                retry_count=payment.retry_count,
                has_active_subscription=(
                    has_active_subscription
                ),
            )

            recovery_case = RecoveryCase(
                payment_id=payment.id,
                customer_id=customer.id,
                amount_at_risk=payment.amount,
                recovery_score=result.score,
                failure_category=(
                    payment.failure_reason
                    or "UNKNOWN"
                ),
                recoverability=(
                    result.recoverability
                ),
                recommended_action=(
                    result.recommended_action
                ),
                approved_action=None,
                status="PENDING",
                amount_recovered=0,
            )

            db.add(recovery_case)

            created += 1

        db.commit()

        print(
            f"Created {created} recovery cases."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    scan_failed_payments()