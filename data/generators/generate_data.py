import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker


fake = Faker("en_IN")

random.seed(42)
Faker.seed(42)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


PAYMENT_METHODS = [
    "UPI",
    "CARD",
    "NETBANKING",
    "WALLET",
]

BANKS = [
    "HDFC",
    "ICICI",
    "SBI",
    "AXIS",
    "KOTAK",
]

CUSTOMER_TYPES = [
    "new",
    "returning",
    "vip",
]

FAILURE_TYPES = [
    "NETWORK_TIMEOUT",
    "BANK_DECLINED",
    "INSUFFICIENT_FUNDS",
    "CARD_EXPIRED",
    "CUSTOMER_CANCELLED",
    "UPI_TIMEOUT",
    "AUTHENTICATION_FAILED",
    "LIMIT_EXCEEDED",
]


RECOVERY_RULES = {
    "NETWORK_TIMEOUT": {
        "probability": 0.85,
        "action": "RETRY",
    },
    "UPI_TIMEOUT": {
        "probability": 0.80,
        "action": "RETRY",
    },
    "BANK_DECLINED": {
        "probability": 0.55,
        "action": "PAYMENT_LINK",
    },
    "INSUFFICIENT_FUNDS": {
        "probability": 0.45,
        "action": "PAYMENT_LINK",
    },
    "CARD_EXPIRED": {
        "probability": 0.15,
        "action": "CUSTOMER_NUDGE",
    },
    "CUSTOMER_CANCELLED": {
        "probability": 0.05,
        "action": "DO_NOT_CONTACT",
    },
    "AUTHENTICATION_FAILED": {
        "probability": 0.20,
        "action": "CUSTOMER_NUDGE",
    },
    "LIMIT_EXCEEDED": {
        "probability": 0.20,
        "action": "PAYMENT_LINK",
    },
}


def generate_customers(count=2000):
    customers = []

    for i in range(count):
        customer_type = random.choices(
            CUSTOMER_TYPES,
            weights=[40, 50, 10],
            k=1,
        )[0]

        total_orders = random.randint(1, 40)

        # VIPs tend to have stronger payment history.
        if customer_type == "vip":
            success_rate = random.uniform(0.90, 0.99)
        elif customer_type == "returning":
            success_rate = random.uniform(0.75, 0.95)
        else:
            success_rate = random.uniform(0.55, 0.90)

        successful = round(total_orders * success_rate)
        failed = total_orders - successful

        lifetime_value = round(
            random.uniform(500, 250000),
            2,
        )

        customers.append({
            "customer_id": f"CUST_{i + 1:05d}",
            "name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "customer_type": customer_type,
            "total_orders": total_orders,
            "successful_payments": successful,
            "failed_payments": failed,
            "lifetime_value": lifetime_value,
            "historical_success_rate": round(
                successful / total_orders,
                3,
            ),
        })

    return pd.DataFrame(customers)


def generate_orders(customers, count=10000):
    orders = []

    start_date = datetime.now() - timedelta(days=90)

    for i in range(count):
        customer = customers.sample(1).iloc[0]

        amount = round(
            random.choice([
                random.uniform(100, 1000),
                random.uniform(1000, 10000),
                random.uniform(10000, 100000),
            ]),
            2,
        )

        created_at = start_date + timedelta(
            seconds=random.randint(
                0,
                90 * 24 * 60 * 60,
            )
        )

        orders.append({
            "order_id": f"ORDER_{i + 1:07d}",
            "customer_id": customer["customer_id"],
            "amount": amount,
            "currency": "INR",
            "created_at": created_at,
        })

    return pd.DataFrame(orders)


def choose_failure(payment_method):
    if payment_method == "UPI":
        return random.choice([
            "UPI_TIMEOUT",
            "BANK_DECLINED",
            "NETWORK_TIMEOUT",
            "INSUFFICIENT_FUNDS",
        ])

    if payment_method == "CARD":
        return random.choice([
            "CARD_EXPIRED",
            "BANK_DECLINED",
            "INSUFFICIENT_FUNDS",
            "LIMIT_EXCEEDED",
            "AUTHENTICATION_FAILED",
        ])

    return random.choice(FAILURE_TYPES)


def generate_transactions(orders, customers):
    transactions = []
    attempts = []

    for _, order in orders.iterrows():

        customer = customers[
            customers["customer_id"] == order["customer_id"]
        ].iloc[0]

        payment_method = random.choice(PAYMENT_METHODS)
        bank = random.choice(BANKS)

        # Customer history affects payment success.
        historical_rate = customer["historical_success_rate"]

        success_probability = (
            0.55 * historical_rate +
            0.45 * 0.70
        )

        is_successful = (
            random.random() < success_probability
        )

        transaction_id = f"TXN_{uuid.uuid4().hex[:12]}"

        if is_successful:
            status = "SUCCESS"
            failure_reason = None

            transactions.append({
                "transaction_id": transaction_id,
                "order_id": order["order_id"],
                "customer_id": customer["customer_id"],
                "amount": order["amount"],
                "currency": "INR",
                "payment_method": payment_method,
                "bank": bank,
                "status": status,
                "failure_reason": failure_reason,
                "retry_count": 0,
                "created_at": order["created_at"],
                "is_recoverable": False,
                "optimal_action": "NONE",
                "recovery_probability": 0.0,
                "expected_outcome": "NO_RECOVERY_NEEDED",
            })

            attempts.append({
                "transaction_id": transaction_id,
                "attempt_number": 1,
                "status": "SUCCESS",
                "failure_reason": None,
                "attempted_at": order["created_at"],
            })

            continue

        # Failed payment
        failure_reason = choose_failure(payment_method)

        rule = RECOVERY_RULES[failure_reason]

        base_probability = rule["probability"]

        # Modify probability based on customer behavior.
        customer_factor = (
            0.75 +
            customer["historical_success_rate"] * 0.40
        )

        recovery_probability = min(
            base_probability * customer_factor,
            0.98,
        )

        recoverable = (
            random.random() < recovery_probability
        )

        optimal_action = (
            rule["action"]
            if recoverable
            else "DO_NOT_CONTACT"
        )

        transactions.append({
            "transaction_id": transaction_id,
            "order_id": order["order_id"],
            "customer_id": customer["customer_id"],
            "amount": order["amount"],
            "currency": "INR",
            "payment_method": payment_method,
            "bank": bank,
            "status": "FAILED",
            "failure_reason": failure_reason,
            "retry_count": 0,
            "created_at": order["created_at"],
            "is_recoverable": recoverable,
            "optimal_action": optimal_action,
            "recovery_probability": round(
                recovery_probability,
                3,
            ),
            "expected_outcome": (
                "RECOVERABLE"
                if recoverable
                else "NON_RECOVERABLE"
            ),
        })

        # Initial failed attempt
        attempts.append({
            "transaction_id": transaction_id,
            "attempt_number": 1,
            "status": "FAILED",
            "failure_reason": failure_reason,
            "attempted_at": order["created_at"],
        })

        # Simulate the eventual recovery outcome.
        if recoverable:
            recovery_delay = timedelta(
                minutes=random.randint(2, 120)
            )

            attempts.append({
                "transaction_id": transaction_id,
                "attempt_number": 2,
                "status": "SUCCESS",
                "failure_reason": None,
                "attempted_at": (
                    order["created_at"] +
                    recovery_delay
                ),
            })

    return (
        pd.DataFrame(transactions),
        pd.DataFrame(attempts),
    )


def generate_subscriptions(customers, count=1000):
    subscriptions = []

    plans = [
        ("BASIC", 499),
        ("PRO", 1499),
        ("BUSINESS", 4999),
        ("ENTERPRISE", 19999),
    ]

    for i in range(count):
        customer = customers.sample(1).iloc[0]

        plan, amount = random.choice(plans)

        subscriptions.append({
            "subscription_id": f"SUB_{i + 1:06d}",
            "customer_id": customer["customer_id"],
            "plan": plan,
            "amount": amount,
            "billing_cycle": random.choice([
                "MONTHLY",
                "YEARLY",
            ]),
            "status": random.choice([
                "ACTIVE",
                "ACTIVE",
                "PAST_DUE",
                "CANCELLED",
            ]),
            "next_payment_date": (
                datetime.now() +
                timedelta(days=random.randint(1, 30))
            ),
        })

    return pd.DataFrame(subscriptions)


def main():

    print("Generating customers...")
    customers = generate_customers(2000)

    print("Generating orders...")
    orders = generate_orders(
        customers,
        10000,
    )

    print("Generating transactions...")
    transactions, attempts = generate_transactions(
        orders,
        customers,
    )

    print("Generating subscriptions...")
    subscriptions = generate_subscriptions(
        customers,
        1000,
    )

    customers.to_csv(
        OUTPUT_DIR / "customers.csv",
        index=False,
    )

    orders.to_csv(
        OUTPUT_DIR / "orders.csv",
        index=False,
    )

    transactions.to_csv(
        OUTPUT_DIR / "transactions.csv",
        index=False,
    )

    attempts.to_csv(
        OUTPUT_DIR / "payment_attempts.csv",
        index=False,
    )

    subscriptions.to_csv(
        OUTPUT_DIR / "subscriptions.csv",
        index=False,
    )

    failed = transactions[
        transactions["status"] == "FAILED"
    ]

    print("\nGeneration complete!")
    print("-------------------")
    print(f"Customers:       {len(customers)}")
    print(f"Orders:          {len(orders)}")
    print(f"Transactions:    {len(transactions)}")
    print(f"Payment attempts: {len(attempts)}")
    print(f"Subscriptions:   {len(subscriptions)}")

    print("\nTransactions:")
    print(
        transactions["status"]
        .value_counts()
    )

    print("\nFailed payments:")
    print(
        failed["is_recoverable"]
        .value_counts()
    )

    print("\nOptimal actions:")
    print(
        failed["optimal_action"]
        .value_counts()
    )


if __name__ == "__main__":
    main()