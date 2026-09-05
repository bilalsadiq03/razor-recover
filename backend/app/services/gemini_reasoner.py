import time
from typing import Literal

from pydantic import BaseModel, Field
from google.genai import types

from app.services.gemini_client import get_gemini_client
from app.services.context_builder import RecoveryContext


class RecoveryDecision(BaseModel):
    action: Literal[
        "RETRY",
        "PAYMENT_LINK",
        "CUSTOMER_NUDGE",
        "DO_NOT_CONTACT",
    ]

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the recommended recovery action.",
    )

    reason: str = Field(
        min_length=1,
        description="Concise explanation for the decision.",
    )


SYSTEM_INSTRUCTIONS = """
You are the recovery decision agent for RazorRecover.

Your task is to recommend the safest and most appropriate action
for a failed payment.

You may ONLY choose one action:

RETRY
PAYMENT_LINK
CUSTOMER_NUDGE
DO_NOT_CONTACT

Consider:

- payment failure reason
- payment method
- payment amount
- customer type
- historical payment success rate
- previous retry attempts
- active subscription status
- recent payment attempts

Rules:

- Do not invent information.
- Do not execute any action.
- Do not send messages.
- Do not create payment links.
- Do not make payments.
- Only recommend an action.
- Do not use hidden ground-truth information.
- Prefer actions that are appropriate for the failure reason.
- Avoid repeated retries when previous attempts have failed.

Return a structured decision containing:
action, confidence, and reason.
"""


def build_reasoning_prompt(context: RecoveryContext) -> str:
    return f"""
{SYSTEM_INSTRUCTIONS}

RECOVERY CONTEXT:

{context.to_dict()}

Analyze the recovery context and recommend the single best action.
"""

def deterministic_fallback(
    context: RecoveryContext,
) -> RecoveryDecision:
    """
    Safe deterministic fallback used when Gemini is unavailable.

    This does not use dataset ground truth.
    It only uses the same recovery context available to Gemini.
    """

    # ---------------------------------------------------------
    # Already successfully recovered
    # ---------------------------------------------------------

    if any(
        attempt.status == "SUCCESS"
        for attempt in context.recent_attempts
    ):
        return RecoveryDecision(
            action="DO_NOT_CONTACT",
            confidence=1.0,
            reason=(
                "Fallback decision: a previous payment attempt "
                "already succeeded."
            ),
        )

    # ---------------------------------------------------------
    # Retry transient failures when retry budget remains
    # ---------------------------------------------------------

    transient_failures = {
        "NETWORK_TIMEOUT",
        "UPI_TIMEOUT",
        "BANK_TIMEOUT",
        "GATEWAY_TIMEOUT",
        "TEMPORARY_FAILURE",
    }

    if (
        context.payment.failure_reason
        in transient_failures
        and context.payment.retry_count < 2
    ):
        return RecoveryDecision(
            action="RETRY",
            confidence=0.85,
            reason=(
                "Fallback decision: the payment failed because "
                "of a transient failure and retry capacity remains."
            ),
        )

    # ---------------------------------------------------------
    # Customer-facing recovery for other failed payments
    # ---------------------------------------------------------

    if context.payment.status == "FAILED":
        return RecoveryDecision(
            action="PAYMENT_LINK",
            confidence=0.70,
            reason=(
                "Fallback decision: payment remains failed and "
                "a payment link is a safe recovery option."
            ),
        )

    # ---------------------------------------------------------
    # Safest fallback
    # ---------------------------------------------------------

    return RecoveryDecision(
        action="DO_NOT_CONTACT",
        confidence=1.0,
        reason=(
            "Fallback decision: no safe recovery action "
            "could be determined."
        ),
    )


def recommend_recovery_action(
    context: RecoveryContext,
) -> RecoveryDecision:

    client = get_gemini_client()

    max_retries = 2

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-3.7-flash",
                contents=build_reasoning_prompt(context),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RecoveryDecision,
                    temperature=0.2,
                ),
            )

            if response.parsed is not None:
                return response.parsed

            if response.text:
                return RecoveryDecision.model_validate_json(
                    response.text
                )

            raise RuntimeError(
                "Gemini returned an empty response."
            )

        except Exception as exc:
            error_text = str(exc)

            # -------------------------------------------------
            # Gemini quota exhausted
            # -------------------------------------------------
            if (
                "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
            ):
                print(
                    "Gemini quota exceeded. "
                    "Using deterministic fallback."
                )

                return deterministic_fallback(context)

            # -------------------------------------------------
            # Gemini temporarily unavailable
            # -------------------------------------------------
            if (
                "503" in error_text
                or "UNAVAILABLE" in error_text
            ):
                if attempt < max_retries:
                    wait_seconds = 2 ** attempt

                    print(
                        f"Gemini temporarily unavailable. "
                        f"Retrying in {wait_seconds}s..."
                    )

                    time.sleep(wait_seconds)
                    continue

                print(
                    "Gemini unavailable after retries. "
                    "Using deterministic fallback."
                )

                return deterministic_fallback(context)

            raise