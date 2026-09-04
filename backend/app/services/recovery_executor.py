import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import (
    Payment,
    RecoveryCase,
    AgentDecision,
    RecoveryAction,
    AuditLog,
)

from app.services.context_builder import build_recovery_context
from app.services.gemini_reasoner import recommend_recovery_action
from app.services.policy_engine import evaluate_policy
from app.services.payment_simulator import simulate_recovery


def execute_recovery(payment_id: int) -> dict:
    """
    Execute the complete AI recovery workflow for one failed payment.

    Flow:
        Context -> Gemini -> Policy -> Simulator -> Database records
    """

    db = SessionLocal()

    try:
        # ---------------------------------------------------------
        # 1. Find payment
        # ---------------------------------------------------------
        payment = db.execute(
            select(Payment).where(Payment.id == payment_id)
        ).scalar_one_or_none()

        if payment is None:
            raise ValueError(f"Payment {payment_id} not found.")

        if payment.status != "FAILED":
            raise ValueError(
                f"Payment {payment_id} is not in FAILED state."
            )

        # ---------------------------------------------------------
        # 2. Find and lock recovery case
        # ---------------------------------------------------------
        recovery_case = db.execute(
            select(RecoveryCase)
            .where(
                RecoveryCase.payment_id == payment_id,
                RecoveryCase.status == "PENDING",
            )
            .with_for_update()
        ).scalar_one_or_none()

        if recovery_case is None:
            raise ValueError(
                f"No pending recovery case found for payment {payment_id}."
            )
            
        # ---------------------------------------------------------
        # 3. Build context
        # ---------------------------------------------------------
        context = build_recovery_context(payment_id)

        # ---------------------------------------------------------
        # 4. Ask Gemini
        # ---------------------------------------------------------
        ai_decision = recommend_recovery_action(context)

        agent_decision = AgentDecision(
            recovery_case_id=recovery_case.id,
            agent_name="gemini-reasoner",
            decision=ai_decision.action,
            confidence=ai_decision.confidence,
            reason_summary=ai_decision.reason,
        )

        db.add(agent_decision)
        db.flush()

        # ---------------------------------------------------------
        # 5. Apply policy
        # ---------------------------------------------------------
        policy_decision = evaluate_policy(
            context,
            ai_decision,
        )

        # ---------------------------------------------------------
        # 6. BLOCKED action
        # ---------------------------------------------------------
        if not policy_decision.allowed:

            recovery_case.status = "BLOCKED"
            recovery_case.approved_action = None

            audit_log = AuditLog(
                recovery_case_id=recovery_case.id,
                event_type="POLICY_BLOCK",
                actor="policy-engine",
                action=ai_decision.action,
                result="BLOCKED",
                metadata_json=json.dumps({
                    "reason": policy_decision.reason,
                    "confidence": ai_decision.confidence,
                }),
            )

            db.add(audit_log)
            db.commit()

            return {
                "payment_id": payment.id,
                "transaction_id": payment.transaction_id,
                "recovery_case_id": recovery_case.id,
                "ai_action": ai_decision.action,
                "confidence": ai_decision.confidence,
                "allowed": False,
                "status": "BLOCKED",
                "amount_recovered": 0.0,
                "reason": policy_decision.reason,
            }

        # ---------------------------------------------------------
        # 7. APPROVED action
        # ---------------------------------------------------------
        recovery_case.approved_action = policy_decision.action
        recovery_case.status = "EXECUTING"

        db.flush()

        # ---------------------------------------------------------
        # 8. Execute simulated recovery
        # ---------------------------------------------------------
        simulation = simulate_recovery(
            payment_id,
            policy_decision.action,
        )

        amount_recovered = Decimal(
            str(simulation.amount_recovered)
        )

        action_status = (
            "SUCCESS"
            if simulation.success
            else "FAILED"
        )

        recovery_action = RecoveryAction(
            recovery_case_id=recovery_case.id,
            action_type=policy_decision.action,
            status=action_status,
            amount_recovered=amount_recovered,
            executed_at=datetime.utcnow(),
        )

        db.add(recovery_action)

        # ---------------------------------------------------------
        # 9. Update recovery case
        # ---------------------------------------------------------
        recovery_case.amount_recovered = amount_recovered
        recovery_case.status = (
            "RECOVERED"
            if simulation.success
            else "FAILED"
        )

        if simulation.success:
            recovery_case.resolved_at = datetime.utcnow()

        db.flush()

        # ---------------------------------------------------------
        # 10. Audit the execution
        # ---------------------------------------------------------
        audit_log = AuditLog(
            recovery_case_id=recovery_case.id,
            event_type="RECOVERY_EXECUTED",
            actor="recovery-executor",
            action=policy_decision.action,
            result=action_status,
            metadata_json=json.dumps({
                "amount_recovered": float(amount_recovered),
                "policy_reason": policy_decision.reason,
                "simulation_reason": simulation.reason,
                "gemini_confidence": ai_decision.confidence,
            }),
        )

        db.add(audit_log)

        db.commit()

        return {
            "payment_id": payment.id,
            "transaction_id": payment.transaction_id,
            "recovery_case_id": recovery_case.id,
            "ai_action": ai_decision.action,
            "approved_action": policy_decision.action,
            "confidence": ai_decision.confidence,
            "allowed": True,
            "status": action_status,
            "amount_recovered": float(amount_recovered),
            "reason": simulation.reason,
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()