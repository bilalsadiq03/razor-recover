from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import (
    Payment,
    PaymentAttempt,
    Customer,
    Subscription,
)


@dataclass
class PaymentContext:
    transaction_id: str
    amount: float
    currency: str
    payment_method: str
    bank: str | None
    status: str
    failure_reason: str | None
    retry_count: int


@dataclass
class CustomerContext:
    customer_type: str
    total_orders: int
    successful_payments: int
    failed_payments: int
    lifetime_value: float
    historical_success_rate: float


@dataclass
class SubscriptionContext:
    active: bool
    plan: str | None
    amount: float | None
    billing_cycle: str | None
    next_payment_date: str | None


@dataclass
class AttemptContext:
    attempt_number: int
    status: str
    failure_reason: str | None
    attempted_at: str


@dataclass
class RecoveryContext:
    payment: PaymentContext
    customer: CustomerContext
    subscription: SubscriptionContext
    recent_attempts: list[AttemptContext]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_recovery_context(
    payment_id: int,
) -> RecoveryContext:

    db = SessionLocal()

    try:
        # --------------------------------------------------
        # Payment
        # --------------------------------------------------

        payment = db.execute(
            select(Payment).where(
                Payment.id == payment_id
            )
        ).scalar_one_or_none()

        if payment is None:
            raise ValueError(
                f"Payment {payment_id} not found."
            )

        # --------------------------------------------------
        # Customer
        # --------------------------------------------------

        customer = db.execute(
            select(Customer).where(
                Customer.id == payment.customer_id
            )
        ).scalar_one()

        # --------------------------------------------------
        # Subscription
        # --------------------------------------------------

        subscription = db.execute(
            select(Subscription)
            .where(
                Subscription.customer_id
                == customer.id
            )
            .where(
                Subscription.status == "ACTIVE"
            )
            .order_by(
                Subscription.id.desc()
            )
        ).scalars().first()

        # --------------------------------------------------
        # Payment attempts
        # --------------------------------------------------

        attempts = db.execute(
            select(PaymentAttempt)
            .where(
                PaymentAttempt.payment_id
                == payment.id
            )
            .order_by(
                PaymentAttempt.attempt_number.asc()
            )
        ).scalars().all()

        # --------------------------------------------------
        # Historical success rate
        # --------------------------------------------------

        total_payments = (
            customer.successful_payments
            + customer.failed_payments
        )

        if total_payments > 0:
            historical_success_rate = (
                customer.successful_payments
                / total_payments
            )
        else:
            historical_success_rate = 0.0

        # --------------------------------------------------
        # Build payment context
        # --------------------------------------------------

        payment_context = PaymentContext(
            transaction_id=payment.transaction_id,
            amount=float(payment.amount),
            currency=payment.currency,
            payment_method=payment.payment_method,
            bank=payment.bank,
            status=payment.status,
            failure_reason=payment.failure_reason,
            retry_count=payment.retry_count,
        )

        # --------------------------------------------------
        # Build customer context
        # --------------------------------------------------

        customer_context = CustomerContext(
            customer_type=customer.customer_type,
            total_orders=customer.total_orders,
            successful_payments=customer.successful_payments,
            failed_payments=customer.failed_payments,
            lifetime_value=float(
                customer.lifetime_value
            ),
            historical_success_rate=round(
                historical_success_rate,
                4,
            ),
        )

        # --------------------------------------------------
        # Build subscription context
        # --------------------------------------------------

        if subscription:

            next_payment_date = (
                subscription.next_payment_date.isoformat()
                if subscription.next_payment_date
                else None
            )

            subscription_context = (
                SubscriptionContext(
                    active=True,
                    plan=subscription.plan,
                    amount=float(
                        subscription.amount
                    ),
                    billing_cycle=(
                        subscription.billing_cycle
                    ),
                    next_payment_date=(
                        next_payment_date
                    ),
                )
            )

        else:

            subscription_context = (
                SubscriptionContext(
                    active=False,
                    plan=None,
                    amount=None,
                    billing_cycle=None,
                    next_payment_date=None,
                )
            )

        # --------------------------------------------------
        # Build attempt history
        # --------------------------------------------------

        attempt_contexts = [
            AttemptContext(
                attempt_number=attempt.attempt_number,
                status=attempt.status,
                failure_reason=attempt.failure_reason,
                attempted_at=attempt.attempted_at.isoformat(),
            )
            for attempt in attempts
        ]

        return RecoveryContext(
            payment=payment_context,
            customer=customer_context,
            subscription=subscription_context,
            recent_attempts=attempt_contexts,
        )

    finally:
        db.close()