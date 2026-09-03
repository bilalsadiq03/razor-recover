from dataclasses import dataclass

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Payment

from app.services.context_builder import RecoveryContext


@dataclass
class PaymentSimulationResult:
    success: bool
    amount_recovered: float
    reason: str


def simulate_recovery(
    payment_id: int,
    action: str,
) -> PaymentSimulationResult:
    """
    Simulate the outcome of a recovery action.

    IMPORTANT:
    Ground-truth fields are used only inside the simulator.
    They are never exposed to Gemini.
    """

    db = SessionLocal()

    try:
        payment = db.execute(
            select(Payment).where(Payment.id == payment_id)
        ).scalar_one_or_none()

        if payment is None:
            raise ValueError(f"Payment {payment_id} not found.")

        if payment.status != "FAILED":
            return PaymentSimulationResult(
                success=False,
                amount_recovered=0.0,
                reason="Payment is not in FAILED state.",
            )

        context = RecoveryContext

        # Ground truth will be loaded from the synthetic dataset.
        # This information is intentionally isolated from the AI layer.
        from pathlib import Path
        import csv

        project_root = Path(__file__).resolve().parents[3]
        transactions_path = (
            project_root / "data" / "generated" / "transactions.csv"
        )

        ground_truth = None

        with transactions_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                if row["transaction_id"].strip() == payment.transaction_id:
                    ground_truth = row
                    break

        if ground_truth is None:
            raise ValueError(
                f"Ground truth not found for {payment.transaction_id}."
            )

        optimal_action = ground_truth["optimal_action"]
        is_recoverable = ground_truth["is_recoverable"].lower() == "true"

        # ---------------------------------------------------------
        # DO_NOT_CONTACT
        # ---------------------------------------------------------
        if action == "DO_NOT_CONTACT":
            return PaymentSimulationResult(
                success=False,
                amount_recovered=0.0,
                reason="No recovery action was executed.",
            )

        # ---------------------------------------------------------
        # Non-recoverable payment
        # ---------------------------------------------------------
        if not is_recoverable:
            return PaymentSimulationResult(
                success=False,
                amount_recovered=0.0,
                reason="Payment is not recoverable in the simulation.",
            )

        # ---------------------------------------------------------
        # Optimal action succeeds.
        # ---------------------------------------------------------
        if action == optimal_action:
            return PaymentSimulationResult(
                success=True,
                amount_recovered=float(payment.amount),
                reason=(
                    f"{action} successfully recovered the payment."
                ),
            )

        # ---------------------------------------------------------
        # Non-optimal actions have a reduced chance of recovery.
        #
        # For the first version, we keep this deterministic.
        # We can introduce probabilistic outcomes later.
        # ---------------------------------------------------------
        return PaymentSimulationResult(
            success=False,
            amount_recovered=0.0,
            reason=(
                f"{action} did not recover the payment. "
            ),
        )

    finally:
        db.close()