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


def recommend_recovery_action(
    context: RecoveryContext,
) -> RecoveryDecision:

    client = get_gemini_client()

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
        return RecoveryDecision.model_validate_json(response.text)

    raise RuntimeError("Gemini returned an empty response.")