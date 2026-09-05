import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import delete

# Allow imports from backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal
from app.models import (
    Merchant,
    Customer,
    Order,
    Payment,
    PaymentAttempt,
    Subscription,
    RecoveryCase,
    AgentDecision,
    RecoveryAction,
    Notification,
    AuditLog
)

DATA_DIR = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "generated"
)


def seed_database():

    print("Loading CSV files...")

    customers_df = pd.read_csv(
        DATA_DIR / "customers.csv"
    )

    orders_df = pd.read_csv(
        DATA_DIR / "orders.csv"
    )

    transactions_df = pd.read_csv(
        DATA_DIR / "transactions.csv"
    )

    attempts_df = pd.read_csv(
        DATA_DIR / "payment_attempts.csv"
    )

    subscriptions_df = pd.read_csv(
        DATA_DIR / "subscriptions.csv"
    )

    db = SessionLocal()

    try:
        print("Clearing existing data...")

        db.execute(delete(AuditLog))
        db.execute(delete(Notification))
        db.execute(delete(RecoveryAction))
        db.execute(delete(AgentDecision))
        db.execute(delete(RecoveryCase))

        # Then clear payment-related data.
        db.execute(delete(PaymentAttempt))
        db.execute(delete(Payment))

        # Then clear the remaining data.
        db.execute(delete(Order))
        db.execute(delete(Subscription))
        db.execute(delete(Customer))
        db.execute(delete(Merchant))

        db.commit()

        # ------------------------------------------------
        # Merchant
        # ------------------------------------------------

        merchant = Merchant(
            name="Demo Merchant",
            external_id="merchant_demo_001",
        )

        db.add(merchant)
        db.flush()

        print("Created merchant.")

        # ------------------------------------------------
        # Customers
        # ------------------------------------------------

        customer_map = {}

        for _, row in customers_df.iterrows():

            customer = Customer(
                merchant_id=merchant.id,
                external_id=row["customer_id"],
                name=row["name"],
                email=row["email"],
                phone=row["phone"],
                customer_type=row["customer_type"],
                total_orders=int(row["total_orders"]),
                successful_payments=int(
                    row["successful_payments"]
                ),
                failed_payments=int(
                    row["failed_payments"]
                ),
                lifetime_value=float(
                    row["lifetime_value"]
                ),
            )

            db.add(customer)
            db.flush()

            customer_map[
                row["customer_id"]
            ] = customer.id

        print(
            f"Created {len(customer_map)} customers."
        )

        # ------------------------------------------------
        # Orders
        # ------------------------------------------------

        order_map = {}

        for _, row in orders_df.iterrows():

            customer_id = customer_map[
                row["customer_id"]
            ]

            order = Order(
                merchant_id=merchant.id,
                customer_id=customer_id,
                external_id=row["order_id"],
                amount=float(row["amount"]),
                currency=row["currency"],
                status="CREATED",
                created_at=pd.to_datetime(
                    row["created_at"]
                ),
            )

            db.add(order)
            db.flush()

            order_map[
                row["order_id"]
            ] = order.id

        print(
            f"Created {len(order_map)} orders."
        )

        # ------------------------------------------------
        # Payments
        # ------------------------------------------------

        payment_map = {}

        for _, row in transactions_df.iterrows():

            payment = Payment(
                transaction_id=row["transaction_id"],
                order_id=order_map[row["order_id"]],
                customer_id=customer_map[row["customer_id"]],
                amount=float(row["amount"]),
                currency=row["currency"],
                payment_method=row["payment_method"],
                bank=row["bank"],

                # Every payment starts as FAILED for the
                # recovery-demo environment.
                #
                # The simulator uses:
                #   is_recoverable
                #   optimal_action
                #
                # as isolated ground truth.
                status="FAILED",

                failure_reason=(
                    None
                    if pd.isna(row["failure_reason"])
                    else row["failure_reason"]
                ),

                # Recovery attempts are controlled by the
                # recovery executor, not historical CSV state.
                retry_count=0,

                created_at=pd.to_datetime(
                    row["created_at"]
                ),
            )

            db.add(payment)
            db.flush()

            payment_map[row["transaction_id"]] = payment.id

        print(
            f"Created {len(payment_map)} payments."
        )

       

                # ------------------------------------------------
        # Payment attempts
        # ------------------------------------------------

        attempt_count = 0

        for _, row in attempts_df.iterrows():

            transaction_id = row["transaction_id"]

            # Find transaction ground truth
            transaction = transactions_df[
                transactions_df["transaction_id"]
                == transaction_id
            ]

            if transaction.empty:
                continue

            transaction_row = transaction.iloc[0]

            is_recoverable = (
                str(transaction_row["is_recoverable"]).lower()
                == "true"
            )

            # ------------------------------------------------
            # IMPORTANT:
            #
            # Recoverable demo payments must NOT already have
            # a successful historical attempt.
            #
            # Otherwise the AI correctly concludes that no
            # recovery action is necessary.
            # ------------------------------------------------

            if (
                is_recoverable
                and str(row["status"]).upper() == "SUCCESS"
            ):
                continue

            attempt = PaymentAttempt(
                payment_id=payment_map[transaction_id],
                attempt_number=int(row["attempt_number"]),
                status=row["status"],
                failure_reason=(
                    None
                    if pd.isna(row["failure_reason"])
                    else row["failure_reason"]
                ),
                attempted_at=pd.to_datetime(
                    row["attempted_at"]
                ),
            )

            db.add(attempt)
            attempt_count += 1

        print(
            f"Created {attempt_count} payment attempts."
        )

        # ------------------------------------------------
        # Subscriptions
        # ------------------------------------------------

        subscription_count = 0

        for _, row in subscriptions_df.iterrows():

            subscription = Subscription(
                customer_id=customer_map[
                    row["customer_id"]
                ],
                external_id=row[
                    "subscription_id"
                ],
                plan=row["plan"],
                amount=float(row["amount"]),
                billing_cycle=row[
                    "billing_cycle"
                ],
                status=row["status"],
                next_payment_date=pd.to_datetime(
                    row["next_payment_date"]
                ),
            )

            db.add(subscription)
            subscription_count += 1

        print(
            f"Created {subscription_count} subscriptions."
        )

        db.commit()

        print("\nDatabase seeding complete!")

    except Exception as e:

        db.rollback()

        print(
            f"\nERROR: {e}"
        )

        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()