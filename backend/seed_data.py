import os
import random
import uuid
from datetime import datetime, timedelta
import sys

# Add current directory to path so we can import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_db, save_transaction, Transaction
from risk_engine import RiskEngine
from schemas import TransactionInput, RiskFactor
from level3_gnn_nlp import add_transaction_to_graph

def generate_random_upi():
    names = ["rahul", "priya", "amit", "sneha", "vikram", "anita", "raj", "meera", "kapil", "sita", "arjun", "deepa"]
    providers = ["okaxis", "okicici", "okhdfc", "oksbi", "paytm", "apl"]
    return f"{random.choice(names)}{random.randint(10, 99)}@{random.choice(providers)}"

def get_scam_description():
    scams = [
        "Lucky Draw Winner - Claim Prize",
        "Lottery Jackpot 500k",
        "KYC Update Required Urgently",
        "Investment Double Returns 24h",
        "Govt Subsidy Claim",
        "Customer Care Refund",
        "Electricity Bill Payment Pending",
        "Amazon Gift Card Reward"
    ]
    return random.choice(scams)

def seed_data(count=100):
    print(f"🚀 Initializing Database seeding for {count} transactions...")
    success, engine, SessionLocal = init_db()
    
    if not success:
        print("❌ Database connection failed. Exiting.")
        return

    risk_engine = RiskEngine()
    
    # Pre-define some "Mule" accounts
    mule_accounts = [f"mule_{i}@upi" for i in range(5)]
    mule_receivers = [f"scammer_{i}@upi" for i in range(2)]
    
    # Transaction storage for graph consistency
    all_results = []

    for i in range(count):
        # Determine scenario
        scenario = random.choices(
            ["normal", "scam_keyword", "on_call", "mule_pattern", "high_amount"],
            weights=[60, 15, 10, 10, 5]
        )[0]
        
        # 30-day spread
        days_ago = random.randint(0, 30)
        seconds_ago = random.randint(0, 86400)
        timestamp = datetime.utcnow() - timedelta(days=days_ago, seconds=seconds_ago)
        
        # Base input
        txn_id = f"SEED{int(timestamp.timestamp())}{i}"
        amount = round(random.uniform(50, 5000), 2)
        merchant_upi = generate_random_upi()
        merchant_name = "Merchant " + random.choice("ABCDEFGHIJKL")
        
        is_on_call = False
        description = "Regular Payment"
        device_rooted = False
        velocity = random.randint(0, 3)
        
        if scenario == "scam_keyword":
            description = get_scam_description()
            amount = round(random.uniform(5000, 50000), 2)
        elif scenario == "on_call":
            is_on_call = True
            amount = round(random.uniform(10000, 80000), 2)
            description = "Urgent Secure Pay"
        elif scenario == "mule_pattern":
            merchant_upi = random.choice(mule_accounts)
            description = "Transfer"
            velocity = random.randint(5, 15)
        elif scenario == "high_amount":
            amount = round(random.uniform(100000, 200000), 2)
            description = "Investment"

        txn_input = TransactionInput(
            transaction_id=txn_id,
            amount=amount,
            merchant_name=merchant_name,
            merchant_upi_id=merchant_upi,
            is_new_merchant=random.choice([True, False]),
            hour_of_day=timestamp.hour,
            is_new_device=random.choice([True, False]),
            device_rooted=device_rooted,
            is_on_call=is_on_call,
            location_changed=random.choice([True, False]),
            velocity_last_1hr=velocity,
            user_avg_amount=2000.0,
            swipe_confidence=round(random.uniform(0.3, 0.9), 2)
        )
        
        # Analyze using Risk Engine (Standard)
        # We use a bit of manual override for "scam keyword" as the logic is in rules.py
        result = risk_engine.analyze_transaction(txn_input)
        
        # Manually set timestamp to our spread timestamp
        result.timestamp = timestamp.isoformat()
        
        # Save to DB
        session = SessionLocal()
        try:
            # Create Transaction object
            db_txn = Transaction(
                transaction_id=result.transaction_id,
                amount=result.amount,
                merchant_name=txn_input.merchant_name,
                merchant_upi_id=result.receiver_upi,
                decision=result.decision,
                fraud_score=getattr(result, 'fraud_score', 0.1),
                risk_level=result.risk_level,
                risk_score=result.risk_score,
                reasons=result.message,
                level_reached=result.risk_level,
                latency_ms=0.5,
                created_at=timestamp
            )
            session.add(db_txn)
            session.commit()
            
            # Add to graph for networking viz
            add_transaction_to_graph(
                sender="user@upi",
                receiver=result.receiver_upi,
                amount=result.amount,
                timestamp=result.timestamp
            )
            
        except Exception as e:
            print(f"Error seeding transaction {i}: {e}")
            session.rollback()
        finally:
            session.close()

    print(f"✅ Seeding complete! Added {count} transactions spread over 30 days.")

if __name__ == "__main__":
    seed_data(100)
