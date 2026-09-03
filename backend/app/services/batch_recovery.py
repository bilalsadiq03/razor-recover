import time
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.recovery import RecoveryCase
from app.services.recovery_executor import execute_recovery


def run_batch(
    batch_size: int = 10,
    delay_seconds: float = 15.0,
    max_revenue_at_risk: float = 100000.0,
    max_consecutive_errors: int = 3,
) -> dict:
    db = SessionLocal()

    try:
        cases = db.execute(
            select(RecoveryCase)
            .where(RecoveryCase.status == "PENDING")
            .order_by(RecoveryCase.id)
            .limit(batch_size)
        ).scalars().all()

        print(f"Found {len(cases)} pending recovery cases.")

        results = []
        selected_cases = []

        revenue_selected = Decimal("0")
        consecutive_errors = 0
        stop_reason = None

        for idx, case in enumerate(cases):

            case_amount = Decimal(str(case.amount_at_risk))

            # Financial safety limit
            if revenue_selected + case_amount > Decimal(
                str(max_revenue_at_risk)
            ):
                stop_reason = "MAX_REVENUE_AT_RISK_REACHED"

                print(
                    f"Stopping batch: revenue-at-risk limit of "
                    f"₹{max_revenue_at_risk:.2f} reached."
                )

                break

            revenue_selected += case_amount
            selected_cases.append(case)

            # Rate limiting between Gemini requests
            if idx > 0:
                print(
                    f"Waiting {delay_seconds:.1f}s "
                    f"before next Gemini request..."
                )
                time.sleep(delay_seconds)

            print(
                f"Processing case {case.id} "
                f"(payment_id={case.payment_id}, "
                f"amount=₹{case.amount_at_risk})"
            )

            try:
                result = execute_recovery(case.payment_id)

                results.append(result)

                # Successful execution resets consecutive error count
                consecutive_errors = 0

                print(
                    f"  AI action: {result['ai_action']}"
                )
                print(
                    f"  Approved action: {result['approved_action']}"
                )
                print(
                    f"  Status: {result['status']}"
                )
                print(
                    f"  Recovered: ₹{result['amount_recovered']}"
                )

            except Exception as exc:
                error_text = str(exc)

                print(
                    f"  ERROR processing case {case.id}: {exc}"
                )

                consecutive_errors += 1

                # Stop immediately when Gemini quota is exhausted
                if (
                    "rate limit" in error_text.lower()
                    or "quota" in error_text.lower()
                ):
                    stop_reason = "GEMINI_QUOTA_EXCEEDED"

                    print(
                        "  Gemini quota reached. "
                        "Stopping batch."
                    )

                    break

                # Stop after too many consecutive errors
                if consecutive_errors >= max_consecutive_errors:
                    stop_reason = (
                        "MAX_CONSECUTIVE_ERRORS_REACHED"
                    )

                    print(
                        f"  Stopping batch: "
                        f"{max_consecutive_errors} "
                        f"consecutive errors reached."
                    )

                    break

        # ---------------------------------------------------------
        # Batch metrics
        # ---------------------------------------------------------

        revenue_at_risk = sum(
            Decimal(str(case.amount_at_risk))
            for case in selected_cases
        )

        successful = sum(
            1
            for result in results
            if result.get("status") == "SUCCESS"
        )

        failed = sum(
            1
            for result in results
            if result.get("status") == "FAILED"
        )

        policy_blocked = sum(
            1
            for result in results
            if result.get("status") == "BLOCKED"
        )

        revenue_recovered = sum(
            Decimal(
                str(result.get("amount_recovered", 0))
            )
            for result in results
        )

        not_selected = len(cases) - len(selected_cases)
        deferred = len(selected_cases) - len(results)

        case_recovery_rate = (
            successful / len(results)
            if results
            else 0.0
        )

        revenue_recovery_rate = (
            float(revenue_recovered / revenue_at_risk)
            if revenue_at_risk > 0
            else 0.0
        )

        summary = {
            "cases_found": len(cases),
            "cases_processed": len(results),
            "successful_recoveries": successful,
            "failed_recoveries": failed,
            "policy_blocked": policy_blocked,
            "deferred": deferred,
            "revenue_at_risk": float(revenue_at_risk),
            "revenue_recovered": float(revenue_recovered),
            "recovery_rate": case_recovery_rate,
            "revenue_recovery_rate": revenue_recovery_rate,
            "stop_reason": stop_reason or "BATCH_COMPLETED",
            "not_selected": not_selected,
        }

        # ---------------------------------------------------------
        # Batch summary
        # ---------------------------------------------------------

        print("\n=== BATCH SUMMARY ===")
        print(
            f"Cases found: "
            f"{summary['cases_found']}"
        )
        print(
            f"Cases processed: "
            f"{summary['cases_processed']}"
        )
        print(
            f"Successful recoveries: "
            f"{summary['successful_recoveries']}"
        )
        print(
            f"Failed recoveries: "
            f"{summary['failed_recoveries']}"
        )
        print(
            f"Policy blocked: "
            f"{summary['policy_blocked']}"
        )
        print(
            f"Deferred: "
            f"{summary['deferred']}"
        )
        print(
            f"Not selected: "
            f"{summary['not_selected']}"
        )
        print(
            f"Revenue at risk: "
            f"₹{summary['revenue_at_risk']:.2f}"
        )
        print(
            f"Revenue recovered: "
            f"₹{summary['revenue_recovered']:.2f}"
        )
        print(
            f"Case recovery rate: "
            f"{summary['recovery_rate']:.2%}"
        )
        print(
            f"Revenue recovery rate: "
            f"{summary['revenue_recovery_rate']:.2%}"
        )
        print(
            f"Stop reason: "
            f"{summary['stop_reason']}"
        )

        return summary

    finally:
        db.close()


if __name__ == "__main__":
    run_batch(
        batch_size=3,
        delay_seconds=15,
        max_revenue_at_risk=100000,
        max_consecutive_errors=3,
    )