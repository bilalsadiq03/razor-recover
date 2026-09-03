from dataclasses import dataclass
from decimal import Decimal


FAILURE_SCORES = {
    "NETWORK_TIMEOUT": 90,
    "UPI_TIMEOUT": 88,
    "BANK_DECLINED": 65,
    "INSUFFICIENT_FUNDS": 55,
    "LIMIT_EXCEEDED": 40,
    "AUTHENTICATION_FAILED": 35,
    "CARD_EXPIRED": 25,
    "CUSTOMER_CANCELLED": 10,
}


@dataclass
class RecoveryScore:
    score: float
    recoverability: str
    recommended_action: str
    explanation: str


def calculate_amount_score(amount: Decimal) -> float:
    """
    Gives higher-value payments more priority,
    but caps their influence.
    """

    amount = float(amount)

    if amount >= 50000:
        return 100

    if amount >= 25000:
        return 90

    if amount >= 10000:
        return 75

    if amount >= 5000:
        return 60

    if amount >= 1000:
        return 45

    return 30


def calculate_customer_score(
    successful_payments: int,
    failed_payments: int,
) -> float:

    total = successful_payments + failed_payments

    if total == 0:
        return 50

    success_rate = successful_payments / total

    return success_rate * 100


def calculate_attempt_penalty(
    retry_count: int,
) -> float:

    if retry_count == 0:
        return 0

    if retry_count == 1:
        return 15

    if retry_count == 2:
        return 30

    return 50


def calculate_recovery_score(
    amount: Decimal,
    failure_reason: str | None,
    successful_payments: int,
    failed_payments: int,
    retry_count: int,
    has_active_subscription: bool = False,
) -> RecoveryScore:

    failure_score = FAILURE_SCORES.get(
        failure_reason,
        30,
    )

    customer_score = calculate_customer_score(
        successful_payments,
        failed_payments,
    )

    amount_score = calculate_amount_score(
        amount
    )

    attempt_penalty = calculate_attempt_penalty(
        retry_count
    )

    subscription_bonus = (
        5 if has_active_subscription else 0
    )

    # Weighted baseline.
    raw_score = (
        failure_score * 0.45
        + customer_score * 0.30
        + amount_score * 0.20
        + subscription_bonus
        - attempt_penalty
    )

    score = max(
        0,
        min(100, raw_score),
    )

    if score >= 75:
        recoverability = "HIGH"
    elif score >= 50:
        recoverability = "MEDIUM"
    elif score >= 30:
        recoverability = "LOW"
    else:
        recoverability = "VERY_LOW"

    # Deterministic action policy.
    if score >= 75:
        if failure_reason in {
            "NETWORK_TIMEOUT",
            "UPI_TIMEOUT",
        }:
            action = "RETRY"
        else:
            action = "PAYMENT_LINK"

    elif score >= 50:
        action = "PAYMENT_LINK"

    elif score >= 30:
        action = "CUSTOMER_NUDGE"

    else:
        action = "DO_NOT_CONTACT"

    explanation = (
        f"Failure score={failure_score:.1f}, "
        f"customer score={customer_score:.1f}, "
        f"amount score={amount_score:.1f}, "
        f"retry penalty={attempt_penalty:.1f}, "
        f"subscription bonus={subscription_bonus:.1f}."
    )

    return RecoveryScore(
        score=round(score, 2),
        recoverability=recoverability,
        recommended_action=action,
        explanation=explanation,
    )