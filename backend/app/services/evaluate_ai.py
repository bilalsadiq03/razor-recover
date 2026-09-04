from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import (
    Payment,
    RecoveryCase,
    AgentDecision,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

GROUND_TRUTH = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "transactions.csv"
)


def load_ground_truth() -> pd.DataFrame:
    """Load ground truth for failed transactions."""

    truth = pd.read_csv(GROUND_TRUTH)

    truth = truth[
        truth["status"].eq("FAILED")
    ].copy()

    truth["is_recoverable"] = (
        truth["is_recoverable"]
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("true")
    )

    truth["optimal_action"] = (
        truth["optimal_action"]
        .fillna("DO_NOT_CONTACT")
        .astype(str)
        .str.strip()
    )

    truth["transaction_id"] = (
        truth["transaction_id"]
        .astype(str)
        .str.strip()
    )

    return truth


def load_ai_predictions() -> pd.DataFrame:
    """
    Load the latest Gemini decision for each recovery case.

    AgentDecision is the source of truth for the
    AI-generated recovery decision.
    """

    db = SessionLocal()

    try:
        rows = db.execute(
            select(
                Payment.id.label("payment_id"),
                Payment.transaction_id.label(
                    "transaction_id"
                ),
                RecoveryCase.id.label(
                    "recovery_case_id"
                ),
                AgentDecision.decision.label(
                    "ai_action"
                ),
                AgentDecision.confidence.label(
                    "confidence"
                ),
                AgentDecision.reason_summary.label(
                    "reason"
                ),
                AgentDecision.created_at.label(
                    "decision_created_at"
                ),
            )
            .join(
                RecoveryCase,
                RecoveryCase.payment_id
                == Payment.id,
            )
            .join(
                AgentDecision,
                AgentDecision.recovery_case_id
                == RecoveryCase.id,
            )
            .where(
                Payment.status == "FAILED"
            )
            .order_by(
                RecoveryCase.id.desc(),
                AgentDecision.created_at.desc(),
            )
        ).all()

    finally:
        db.close()

    predictions = pd.DataFrame(
        rows,
        columns=[
            "payment_id",
            "transaction_id",
            "recovery_case_id",
            "ai_action",
            "confidence",
            "reason",
            "decision_created_at",
        ],
    )

    if predictions.empty:
        return predictions

    # Keep the latest AI decision for each recovery case.
    predictions = (
        predictions
        .sort_values(
            "decision_created_at",
            ascending=False,
        )
        .drop_duplicates(
            subset=["recovery_case_id"],
            keep="first",
        )
        .copy()
    )

    # Keep only the newest recovery case for each payment.
    predictions = (
        predictions
        .sort_values(
            "recovery_case_id",
            ascending=False,
        )
        .drop_duplicates(
            subset=["payment_id"],
            keep="first",
        )
        .copy()
    )

    predictions["transaction_id"] = (
        predictions["transaction_id"]
        .astype(str)
        .str.strip()
    )

    predictions["ai_action"] = (
        predictions["ai_action"]
        .astype(str)
        .str.strip()
    )

    return predictions


def calculate_classification_metrics(
    merged: pd.DataFrame,
) -> dict:
    """
    Treat any recovery action other than DO_NOT_CONTACT
    as an AI prediction that the payment is recoverable.
    """

    predicted = (
        merged["ai_action"]
        != "DO_NOT_CONTACT"
    )

    actual = (
        merged["is_recoverable"]
        .fillna(False)
        .astype(bool)
    )

    tp = int((predicted & actual).sum())
    fp = int((predicted & ~actual).sum())
    fn = int((~predicted & actual).sum())
    tn = int((~predicted & ~actual).sum())

    precision = (
        tp / (tp + fp)
        if tp + fp
        else 0.0
    )

    recall = (
        tp / (tp + fn)
        if tp + fn
        else 0.0
    )

    f1 = (
        2 * precision * recall
        / (precision + recall)
        if precision + recall
        else 0.0
    )

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def calculate_business_metrics(
    merged: pd.DataFrame,
) -> dict:
    """
    Calculate revenue metrics based on AI recovery decisions.
    """

    predicted = (
        merged["ai_action"]
        != "DO_NOT_CONTACT"
    )

    actual = (
        merged["is_recoverable"]
        .fillna(False)
        .astype(bool)
    )

    total_revenue_at_risk = (
        merged["amount"].sum()
    )

    recoverable_revenue = (
        merged.loc[
            actual,
            "amount",
        ].sum()
    )

    correctly_identified_revenue = (
        merged.loc[
            predicted & actual,
            "amount",
        ].sum()
    )

    missed_recoverable_revenue = (
        merged.loc[
            ~predicted & actual,
            "amount",
        ].sum()
    )

    false_positive_revenue = (
        merged.loc[
            predicted & ~actual,
            "amount",
        ].sum()
    )

    return {
        "total_revenue_at_risk":
            total_revenue_at_risk,

        "recoverable_revenue":
            recoverable_revenue,

        "correctly_identified_revenue":
            correctly_identified_revenue,

        "missed_recoverable_revenue":
            missed_recoverable_revenue,

        "false_positive_revenue":
            false_positive_revenue,
    }


def main():

    print("Loading ground truth...")

    truth = load_ground_truth()

    print(
        f"Ground truth failed payments: "
        f"{len(truth)}"
    )

    print("\nLoading AI predictions...")

    predictions = load_ai_predictions()

    print(
        f"Unique AI predictions: "
        f"{len(predictions)}"
    )

    if predictions.empty:
        raise RuntimeError(
            "No AI decisions found in the database."
        )

    merged = truth.merge(
        predictions,
        on="transaction_id",
        how="inner",
    )

    print(
        f"Matched AI decisions: "
        f"{len(merged)}"
    )

    if merged.empty:
        raise RuntimeError(
            "No ground-truth records matched "
            "AI predictions."
        )

    # --------------------------------------------------
    # Classification
    # --------------------------------------------------

    metrics = calculate_classification_metrics(
        merged
    )

    # --------------------------------------------------
    # Action accuracy
    # --------------------------------------------------

    action_accuracy = (
        merged["ai_action"]
        == merged["optimal_action"]
    ).mean()

    # --------------------------------------------------
    # Business metrics
    # --------------------------------------------------

    business = calculate_business_metrics(
        merged
    )

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    print("\n")
    print("=" * 55)
    print(
        "          RAZORRECOVER AI EVALUATION"
    )
    print("=" * 55)

    print("\n--- DATASET ---")

    print(
        f"Ground truth cases: "
        f"{len(truth)}"
    )

    print(
        f"AI predictions:     "
        f"{len(predictions)}"
    )

    print(
        f"Matched cases:      "
        f"{len(merged)}"
    )

    print("\n--- CLASSIFICATION ---")

    print(
        f"True Positives:     "
        f"{metrics['tp']}"
    )

    print(
        f"False Positives:    "
        f"{metrics['fp']}"
    )

    print(
        f"False Negatives:    "
        f"{metrics['fn']}"
    )

    print(
        f"True Negatives:     "
        f"{metrics['tn']}"
    )

    print(
        f"\nPrecision:          "
        f"{metrics['precision']:.3f}"
    )

    print(
        f"Recall:             "
        f"{metrics['recall']:.3f}"
    )

    print(
        f"F1 Score:           "
        f"{metrics['f1']:.3f}"
    )

    print(
        f"Action Accuracy:    "
        f"{action_accuracy:.3f}"
    )

    print("\n--- BUSINESS METRICS ---")

    print(
        "Revenue at Risk:          "
        f"₹{business['total_revenue_at_risk']:,.2f}"
    )

    print(
        "Actually Recoverable:     "
        f"₹{business['recoverable_revenue']:,.2f}"
    )

    print(
        "Recoverable Identified:   "
        f"₹{business['correctly_identified_revenue']:,.2f}"
    )

    print(
        "Recoverable Missed:       "
        f"₹{business['missed_recoverable_revenue']:,.2f}"
    )

    print(
        "False-Positive Revenue:   "
        f"₹{business['false_positive_revenue']:,.2f}"
    )

    print("\n" + "=" * 55)


if __name__ == "__main__":
    main()