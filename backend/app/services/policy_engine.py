from typing import Literal

from pydantic import BaseModel

from app.services.context_builder import RecoveryContext
from app.services.gemini_reasoner import RecoveryDecision


RecoveryAction = Literal[
    "RETRY",
    "PAYMENT_LINK",
    "CUSTOMER_NUDGE",
    "DO_NOT_CONTACT",
]


class PolicyDecision(BaseModel):
    allowed: bool
    action: RecoveryAction
    reason: str


# Maximum number of retry attempts RazorRecover is allowed to trigger.
MAX_RETRIES = 2


def evaluate_policy(
    context: RecoveryContext,
    decision: RecoveryDecision,
) -> PolicyDecision:
    """
    Validate a Gemini recommendation against deterministic
    RazorRecover safety and business rules.

    Gemini recommends.
    Policy Engine authorizes or blocks.
    """

    action = decision.action

    # ---------------------------------------------------------
    # Rule 1: Never retry after the retry limit.
    # ---------------------------------------------------------
    if action == "RETRY":
        if context.payment.retry_count >= MAX_RETRIES:
            return PolicyDecision(
                allowed=False,
                action=action,
                reason=(
                    f"Retry blocked: payment has already reached "
                    f"the maximum retry limit of {MAX_RETRIES}."
                ),
            )

        return PolicyDecision(
            allowed=True,
            action=action,
            reason=(
                f"Retry permitted: current retry count is "
                f"{context.payment.retry_count}/{MAX_RETRIES}."
            ),
        )

    # ---------------------------------------------------------
    # Rule 2: Payment links are allowed for failed payments.
    # ---------------------------------------------------------
    if action == "PAYMENT_LINK":
        if context.payment.status != "FAILED":
            return PolicyDecision(
                allowed=False,
                action=action,
                reason="Payment link blocked: payment is not in FAILED state.",
            )

        return PolicyDecision(
            allowed=True,
            action=action,
            reason="Payment link permitted for the failed payment.",
        )

    # ---------------------------------------------------------
    # Rule 3: Customer nudges require a failed payment.
    # ---------------------------------------------------------
    if action == "CUSTOMER_NUDGE":
        if context.payment.status != "FAILED":
            return PolicyDecision(
                allowed=False,
                action=action,
                reason="Customer nudge blocked: payment is not in FAILED state.",
            )

        return PolicyDecision(
            allowed=True,
            action=action,
            reason="Customer nudge permitted for the failed payment.",
        )

    # ---------------------------------------------------------
    # Rule 4: DO_NOT_CONTACT is always safe.
    # ---------------------------------------------------------
    if action == "DO_NOT_CONTACT":
        return PolicyDecision(
            allowed=True,
            action=action,
            reason="No-contact decision is always permitted.",
        )

    # ---------------------------------------------------------
    # Defensive fallback.
    # ---------------------------------------------------------
    return PolicyDecision(
        allowed=False,
        action=action,
        reason="Action blocked: unsupported recovery action.",
    )