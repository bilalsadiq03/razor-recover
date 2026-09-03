from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import (
    Payment,
    RecoveryCase,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

GROUND_TRUTH = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "transactions.csv"
)


def load_ground_truth() -> pd.DataFrame:
    """Load hidden ground truth for failed transactions."""

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
    )

    # Make absolutely sure the join key is a string.
    truth["transaction_id"] = (
        truth["transaction_id"]
        .astype(str)
        .str.strip()
    )

    return truth


def load_predictions() -> pd.DataFrame:
    """
    Load baseline predictions.

    Payment.transaction_id is the stable synthetic
    transaction identifier shared with transactions.csv.
    """

    db = SessionLocal()

    try:
        rows = db.execute(
            select(
                Payment.id.label("payment_id"),
                Payment.transaction_id.label("transaction_id"),
                RecoveryCase.id.label(
                    "recovery_case_id"
                ),
                RecoveryCase.recoverability,
                RecoveryCase.recommended_action,
            )
            .join(
                RecoveryCase,
                RecoveryCase.payment_id
                == Payment.id,
            )
            .where(
                Payment.status == "FAILED"
            )
            .order_by(
                RecoveryCase.id.desc()
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
            "recoverability",
            "recommended_action",
        ],
    )

    if predictions.empty:
        return predictions

    # If multiple recovery cases exist for the same payment,
    # keep the newest one.
    predictions = (
        predictions
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

    return predictions


def calculate_classification_metrics(
    merged: pd.DataFrame,
):

    predicted = (
        merged["recoverability"]
        .isin(["HIGH", "MEDIUM"])
        .fillna(False)
        .astype(bool)
    )

    actual = (
        merged["is_recoverable"]
        .fillna(False)
        .astype(bool)
    )

    tp = int(
        (predicted & actual).sum()
    )

    fp = int(
        (predicted & ~actual).sum()
    )

    fn = int(
        (~predicted & actual).sum()
    )

    tn = int(
        (~predicted & ~actual).sum()
    )

    precision = (
        tp / (tp + fp)
        if tp + fp
        else 0
    )

    recall = (
        tp / (tp + fn)
        if tp + fn
        else 0
    )

    f1 = (
        2 * precision * recall
        / (precision + recall)
        if precision + recall
        else 0
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
):

    predicted = (
        merged["recoverability"]
        .isin(["HIGH", "MEDIUM"])
        .fillna(False)
        .astype(bool)
    )

    actual = (
        merged["is_recoverable"]
        .fillna(False)
        .astype(bool)
    )

    total_revenue_at_risk = (
        merged["amount"]
        .sum()
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

    print("\nLoading baseline predictions...")

    predictions = load_predictions()

    print(
        f"Unique database predictions: "
        f"{len(predictions)}"
    )

    # --------------------------------------------------
    # Join using the stable transaction ID.
    # --------------------------------------------------

    merged = truth.merge(
        predictions,
        on="transaction_id",
        how="inner",
    )

    print(
        f"Matched payments: {len(merged)}"
    )

    if len(merged) != len(truth):

        missing = (
            len(truth)
            - len(merged)
        )

        print(
            f"WARNING: {missing} "
            "ground-truth records "
            "were not matched."
        )

    if merged.empty:

        raise RuntimeError(
            "No ground-truth records matched "
            "database predictions."
        )

    # --------------------------------------------------
    # Classification
    # --------------------------------------------------

    metrics = (
        calculate_classification_metrics(
            merged
        )
    )

    # --------------------------------------------------
    # Action accuracy
    # --------------------------------------------------

    action_accuracy = (
        merged["recommended_action"]
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
        "        RAZORRECOVER BASELINE EVALUATION"
    )
    print("=" * 55)

    print("\n--- DATASET ---")

    print(
        f"Ground truth cases: "
        f"{len(truth)}"
    )

    print(
        f"Unique predictions: "
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