"""
UPI SECURE PAY - PostgreSQL Database Connection
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Database URL
DATABASE_URL = "postgresql://postgres:Shivam%4012345@localhost:5432/upi-secure-pay"

# Create engine
engine = None
SessionLocal = None
Base = declarative_base()

# Database tables
class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String, unique=True, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    merchant_name = Column(String)
    merchant_upi_id = Column(String)
    decision = Column(String)
    risk_score = Column(Float)
    reasons = Column(Text)
    level_reached = Column(String)
    latency_ms = Column(Float)
    behavioral_deviation = Column(Float, nullable=True)
    network_risk_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FraudReportDB(Base):
    __tablename__ = "fraud_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_reference = Column(String, unique=True, nullable=False, index=True)
    fraud_upi_id = Column(String, nullable=False)
    amount_lost = Column(Float)
    description = Column(Text)
    reported_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


# Initialize database
def init_db():
    """Create tables if they don't exist"""
    global engine, SessionLocal
    
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Test connection and return a session
        session = SessionLocal()
        session.execute(text("SELECT 1"))
        session.close()
        
        print("✅ PostgreSQL connected - Tables created")
        return True, engine, SessionLocal
    except SQLAlchemyError as e:
        print(f"⚠️ Database connection failed: {e}")
        print("   Continuing with in-memory storage")
        return False, None, None


# Save transaction to database
def save_transaction(session_maker, txn_data):
    """Save transaction to database"""
    session = session_maker()
    try:
        txn = Transaction(
            transaction_id=txn_data.get("transaction_id"),
            amount=txn_data.get("amount"),
            merchant_name=txn_data.get("merchant_name"),
            merchant_upi_id=txn_data.get("merchant_upi_id"),
            decision=txn_data.get("decision"),
            risk_score=txn_data.get("risk_score"),
            reasons=txn_data.get("reasons"),
            level_reached=txn_data.get("level_reached"),
            latency_ms=txn_data.get("latency_ms"),
            behavioral_deviation=txn_data.get("behavioral_deviation"),
            network_risk_score=txn_data.get("network_risk_score")
        )
        session.add(txn)
        session.commit()
        return True
    except SQLAlchemyError as e:
        print(f"Error saving transaction: {e}")
        session.rollback()
        return False
    finally:
        session.close()


# Save fraud report to database
def save_fraud_report(session_maker, report_data):
    """Save fraud report to database"""
    session = session_maker()
    try:
        report = FraudReportDB(
            case_reference=report_data.get("case_reference"),
            fraud_upi_id=report_data.get("fraud_upi_id"),
            amount_lost=report_data.get("amount_lost"),
            description=report_data.get("description"),
            reported_by=report_data.get("reported_by")
        )
        session.add(report)
        session.commit()
        return True
    except SQLAlchemyError as e:
        print(f"Error saving fraud report: {e}")
        session.rollback()
        return False
    finally:
        session.close()


# Get all transactions from database
def get_all_transactions(session_maker, limit=100):
    """Get transactions from database"""
    session = session_maker()
    try:
        txns = session.query(Transaction).order_by(Transaction.created_at.desc()).limit(limit).all()
        return [
            {
                "transaction_id": t.transaction_id,
                "amount": t.amount,
                "merchant_name": t.merchant_name,
                "merchant_upi_id": t.merchant_upi_id,
                "decision": t.decision,
                "risk_score": t.risk_score,
                "reasons": t.reasons,
                "level_reached": t.level_reached,
                "latency_ms": t.latency_ms,
                "behavioral_deviation": t.behavioral_deviation,
                "network_risk_score": t.network_risk_score,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in txns
        ]
    except SQLAlchemyError as e:
        print(f"Error fetching transactions: {e}")
        return []
    finally:
        session.close()


# Get dashboard stats from database
def get_dashboard_stats(session_maker):
    """Get stats from database"""
    session = session_maker()
    try:
        total = session.query(Transaction).count()
        blocked = session.query(Transaction).filter(Transaction.decision == "BLOCK").count()
        alerted = session.query(Transaction).filter(Transaction.decision == "ALERT").count()
        approved = session.query(Transaction).filter(Transaction.decision == "APPROVE").count()
        
        return {
            "total": total,
            "blocked": blocked,
            "alerted": alerted,
            "approved": approved
        }
    except SQLAlchemyError as e:
        print(f"Error fetching stats: {e}")
        return None
    finally:
        session.close()
