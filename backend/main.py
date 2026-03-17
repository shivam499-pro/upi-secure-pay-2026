from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import asyncio
import json
import random
from datetime import datetime
from schemas import TransactionInput, TransactionResult, DashboardStats
from risk_engine import RiskEngine
from fraud_report import FraudReport, fraud_report_manager
from network_graph import fraud_network
from user_profile import UserProfile, user_profile_manager
from level2_lstm import predict_sequence_risk
import database

app = FastAPI(title="UPI Secure Pay API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize risk engine
risk_engine = RiskEngine()

# In-memory storage for transactions
transactions_store: List[TransactionResult] = []

# Database connection
db_session = None
db_engine = None
db_initialized = False

# WebSocket connections
active_connections: List[WebSocket] = []

# Sample UPI IDs for simulation
SAMPLE_SENDERS = [
    "rahul@upi",
    "priya@upi",
    "amit@upi",
    "sneha@upi",
    "vikram@upi",
    "anita@upi",
    "raj@upi",
    "meera@upi",
]

SAMPLE_RECEIVERS = [
    "shop@upi",
    "merchant@upi",
    "friend@upi",
    "family@upi",
    "utility@upi",
    "hospital@upi",
    "school@upi",
    "restaurant@upi",
]

SAMPLE_DESCRIPTIONS = [
    "Monthly groceries",
    "Dinner payment",
    "Bill payment",
    "Gift for friend",
    "Shopping",
    "EMI payment",
    "Recharge",
    "Transport",
    "Medical expenses",
    "Prize lottery winner",  # Scam keyword
    "Investment double returns",  # Scam keyword
    "KYC verify account",  # Scam keyword
]


def generate_sample_transaction() -> TransactionInput:
    """Generate a random sample transaction for live feed"""
    return TransactionInput(
        transaction_id="TXN" + str(int(datetime.now().timestamp() * 1000)),
        amount=round(random.uniform(100, 150000), 2),
        merchant_name="Merchant " + random.choice("ABCDEFGH"),
        merchant_upi_id=random.choice(SAMPLE_RECEIVERS),
        is_new_merchant=random.choice([True, False]),
        hour_of_day=random.randint(0, 23),
        is_new_device=random.choice([True, False]),
        device_rooted=random.choice([True, False, False]),  # Rare
        is_on_call=random.choice([True, False, False]),  # Rare
        location_changed=random.choice([True, False]),
        velocity_last_1hr=random.randint(0, 10),
        user_avg_amount=round(random.uniform(500, 5000), 2),
        swipe_confidence=round(random.uniform(0.5, 1.0), 2)
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "UPI Secure Pay API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/analyze-transaction", response_model=TransactionResult)
async def analyze_transaction(transaction: TransactionInput):
    """
    Analyze a transaction for fraud risk.
    Returns risk score, level, and blocking decision.
    Includes Safety Engine, LightGBM, LSTM Sequence, behavioral deviation and network risk scoring.
    """
    try:
        # Get user ID (using a default if not provided)
        user_id = "user@upi"  # In production, get from auth
        
        # Get user's recent transactions for LSTM sequence analysis
        user_profile = user_profile_manager.get_or_create_profile(user_id)
        user_transactions = user_profile.recent_transactions if hasattr(user_profile, 'recent_transactions') else []
        
        # Convert current transaction to dict format for LSTM
        current_txn = {
            'amount': transaction.amount,
            'hour_of_day': transaction.hour_of_day,
            'is_new_merchant': transaction.is_new_merchant,
            'is_new_device': transaction.is_new_device,
            'velocity_last_1hr': transaction.velocity_last_1hr,
            'amount_ratio': transaction.amount / user_profile.avg_amount if user_profile.avg_amount > 0 else 1.0,
            'swipe_confidence': transaction.swipe_confidence
        }
        
        # Get LSTM sequence risk score (Level 2)
        lstm_sequence_score = 0.0
        lstm_anomaly_reason = None
        if len(user_transactions) >= 3:
            lstm_sequence_score, lstm_anomaly_reason = predict_sequence_risk(
                user_transactions, current_txn
            )
        
        # Calculate behavioral deviation
        behavioral_deviation = user_profile_manager.get_behavioral_deviation(
            user_id=user_id,
            amount=transaction.amount,
            merchant_upi=transaction.merchant_upi_id,
            hour_of_day=transaction.hour_of_day
        )
        
        # Get network risk score
        network_risk_score = fraud_network.get_network_risk_score(transaction.merchant_upi_id)
        
        # Analyze with enhanced scoring (includes LSTM)
        result = risk_engine.analyze_transaction_enhanced(
            transaction=transaction,
            lstm_sequence_score=lstm_sequence_score,
            behavioral_deviation_score=behavioral_deviation.deviation_score,
            network_risk_score=network_risk_score
        )
        
        # Add LSTM anomaly reason to risk factors if high
        if lstm_sequence_score > 0.5 and lstm_anomaly_reason:
            from schemas import RiskFactor
            result.risk_factors.append(RiskFactor(
                name="LSTM Sequence Anomaly",
                description=lstm_anomaly_reason,
                severity="high",
                weight=25.0 * lstm_sequence_score
            ))
        
        # Add Level 2 LSTM fields to result
        result.sequence_risk_score = lstm_sequence_score
        result.level2_active = len(user_transactions) >= 3
        
        # Update user profile with this transaction
        user_profile_manager.update_user_profile(
            user_id=user_id,
            amount=transaction.amount,
            merchant_upi=transaction.merchant_upi_id,
            hour_of_day=transaction.hour_of_day,
            risk_score=result.risk_score
        )
        
        # Add transaction to network graph
        fraud_network.add_transaction_to_graph(
            sender_upi=user_id,
            receiver_upi=transaction.merchant_upi_id,
            amount=transaction.amount,
            timestamp=result.timestamp,
            transaction_id=result.transaction_id
        )
        
        # Store transaction
        transactions_store.insert(0, result)
        
        # Keep only last 100 transactions
        if len(transactions_store) > 100:
            transactions_store.pop()
        
        # Save to database if available
        global db_session, db_initialized
        if db_initialized and db_session:
            try:
                # Get reasons from risk_factors or message
                reasons_str = result.message if result.message else ""
                if hasattr(result, 'risk_factors') and result.risk_factors:
                    reasons_list = [str(r) for r in result.risk_factors[:3]]
                    reasons_str = ", ".join(reasons_list)
                
                txn_data = {
                    "transaction_id": result.transaction_id,
                    "amount": result.amount,
                    "merchant_name": transaction.merchant_name,
                    "merchant_upi_id": transaction.merchant_upi_id,
                    "decision": "BLOCK" if result.is_blocked else ("ALERT" if result.is_alert else "APPROVE"),
                    "risk_score": result.risk_score,
                    "reasons": reasons_str,
                    "level_reached": result.risk_level,
                    "latency_ms": 0.0,
                    "behavioral_deviation": behavioral_deviation.deviation_score,
                    "network_risk_score": network_risk_score
                }
                database.save_transaction(db_session, txn_data)
            except Exception as e:
                print(f"Error saving to DB: {e}")
        
        # Broadcast to all WebSocket clients
        await broadcast_transaction(result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard-stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """
    Get dashboard statistics including totals and recent transactions.
    """
    global db_session, db_initialized, transactions_store
    
    # Try to get from database first
    if db_initialized and db_session:
        try:
            db_stats = database.get_dashboard_stats(db_session)
            if db_stats:
                # Get recent from database
                recent_txns = database.get_all_transactions(db_session, limit=10)
                recent = []
                for t in recent_txns:
                    # Create RiskFactor objects
                    from schemas import RiskFactor
                    risk_factors = []
                    if t.get("reasons"):
                        for reason in t.get("reasons", "").split(", ")[:3]:
                            if reason:
                                risk_factors.append(RiskFactor(
                                    name=reason[:50],
                                    description=reason,
                                    severity="medium",
                                    weight=10.0
                                ))
                    
                    recent.append(TransactionResult(
                        transaction_id=t["transaction_id"],
                        sender_upi=t.get("merchant_upi_id", ""),
                        receiver_upi=t.get("merchant_upi_id", ""),
                        amount=t["amount"],
                        risk_score=t["risk_score"],
                        risk_level=t.get("level_reached", "low"),
                        is_blocked=t["decision"] == "BLOCK",
                        is_alert=t["decision"] == "ALERT",
                        message=t.get("reasons", ""),
                        risk_factors=risk_factors,
                        timestamp=t.get("created_at", ""),
                        status="blocked" if t["decision"] == "BLOCK" else ("alerted" if t["decision"] == "ALERT" else "approved")
                    ))
                
                avg_risk = 0
                if db_stats["total"] > 0 and recent:
                    avg_risk = sum(t.risk_score or 0 for t in recent) / len(recent)
                
                return DashboardStats(
                    total_transactions=db_stats["total"],
                    blocked_transactions=db_stats["blocked"],
                    alerted_transactions=db_stats["alerted"],
                    approved_transactions=db_stats["approved"],
                    average_risk_score=round(avg_risk, 2),
                    recent_transactions=recent
                )
        except Exception as e:
            print(f"DB stats error: {e}")
    
    # Fallback to in-memory
    if not transactions_store:
        for _ in range(5):
            sample = generate_sample_transaction()
            result = risk_engine.analyze_transaction(sample)
            transactions_store.append(result)
    
    total = len(transactions_store)
    blocked = sum(1 for t in transactions_store if t.is_blocked)
    alerted = sum(1 for t in transactions_store if t.is_alert)
    approved = sum(1 for t in transactions_store if not t.is_blocked and not t.is_alert)
    
    avg_risk = sum(t.risk_score for t in transactions_store) / total if total > 0 else 0
    
    return DashboardStats(
        total_transactions=total,
        blocked_transactions=blocked,
        alerted_transactions=alerted,
        approved_transactions=approved,
        average_risk_score=round(avg_risk, 2),
        recent_transactions=transactions_store[:10]
    )


@app.get("/transactions", response_model=List[TransactionResult])
async def get_transactions(limit: int = 20):
    """
    Get recent transactions.
    """
    global db_session, db_initialized, transactions_store
    
    # Try database first
    if db_initialized and db_session:
        try:
            txns = database.get_all_transactions(db_session, limit=limit)
            if txns:
                results = []
                from schemas import RiskFactor
                for t in txns:
                    risk_factors = []
                    if t.get("reasons"):
                        for reason in t.get("reasons", "").split(", ")[:3]:
                            if reason:
                                risk_factors.append(RiskFactor(
                                    name=reason[:50],
                                    description=reason,
                                    severity="medium",
                                    weight=10.0
                                ))
                    
                    results.append(TransactionResult(
                        transaction_id=t["transaction_id"],
                        sender_upi=t.get("merchant_upi_id", ""),
                        receiver_upi=t.get("merchant_upi_id", ""),
                        amount=t["amount"],
                        risk_score=t["risk_score"],
                        risk_level=t.get("level_reached", "low"),
                        is_blocked=t["decision"] == "BLOCK",
                        is_alert=t["decision"] == "ALERT",
                        message=t.get("reasons", ""),
                        risk_factors=risk_factors,
                        timestamp=t.get("created_at", ""),
                        status="blocked" if t["decision"] == "BLOCK" else ("alerted" if t["decision"] == "ALERT" else "approved")
                    ))
                return results
        except Exception as e:
            print(f"DB fetch error: {e}")
    
    # Fallback to in-memory
    return transactions_store[:limit]


@app.websocket("/ws/live-feed")
async def websocket_live_feed(websocket: WebSocket):
    """
    WebSocket endpoint for live transaction feed.
    """
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to live feed",
            "timestamp": datetime.now().isoformat()
        })
        
        # Simulate live transactions
        counter = 0
        while True:
            # Generate a random transaction every 3-8 seconds
            await asyncio.sleep(random.randint(3, 8))
            
            # Generate sample transaction
            sample = generate_sample_transaction()
            result = risk_engine.analyze_transaction(sample)
            
            # Store transaction
            transactions_store.insert(0, result)
            if len(transactions_store) > 100:
                transactions_store.pop()
            
            # Broadcast to WebSocket
            await websocket.send_json({
                "type": "transaction",
                "data": json.loads(result.model_dump_json())
            })
            
            counter += 1
            
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)


async def broadcast_transaction(transaction: TransactionResult):
    """Broadcast transaction to all connected WebSocket clients"""
    message = {
        "type": "transaction",
        "data": json.loads(transaction.model_dump_json())
    }
    
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            disconnected.append(connection)
    
    # Remove disconnected clients
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


# Generate initial sample data on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and generate sample data"""
    global db_session, db_engine, db_initialized
    
    # Initialize database
    db_initialized, db_engine, db_session = database.init_db()
    
    # Generate initial sample data
    for _ in range(10):
        sample = generate_sample_transaction()
        # Occasionally add high risk factors
        if random.random() < 0.3:
            sample.device_rooted = True
            sample.is_on_call = True
        result = risk_engine.analyze_transaction(sample)
        transactions_store.append(result)
        
        # Save to database if available
        if db_initialized and db_session:
            try:
                reasons_str = result.message if result.message else ""
                if hasattr(result, 'risk_factors') and result.risk_factors:
                    reasons_list = [str(r) for r in result.risk_factors[:3]]
                    reasons_str = ", ".join(reasons_list)
                
                txn_data = {
                    "transaction_id": result.transaction_id,
                    "amount": result.amount,
                    "merchant_name": sample.merchant_name,
                    "merchant_upi_id": sample.merchant_upi_id,
                    "decision": "BLOCK" if result.is_blocked else ("ALERT" if result.is_alert else "APPROVE"),
                    "risk_score": result.risk_score,
                    "reasons": reasons_str,
                    "level_reached": result.risk_level,
                    "latency_ms": 0.0,
                    "behavioral_deviation": None,
                    "network_risk_score": None
                }
                database.save_transaction(db_session, txn_data)
            except Exception as e:
                print(f"Startup DB save error: {e}")


# ========== NEW ENDPOINTS ==========

# UPGRADE 1: Fraud Report Endpoint
@app.post("/report-fraud")
async def report_fraud(report: FraudReport):
    """
    Report a fraudulent transaction.
    Adds fraud UPI to blacklist and returns case reference.
    """
    global db_session, db_initialized
    
    result = fraud_report_manager.process_fraud_report(report)
    
    # Save to database if available
    if db_initialized and db_session:
        try:
            report_data = {
                "case_reference": result.case_reference,
                "fraud_upi_id": report.fraud_upi_id,
                "amount_lost": report.amount,
                "description": report.description,
                "reported_by": report.reported_by
            }
            database.save_fraud_report(db_session, report_data)
        except Exception as e:
            print(f"Error saving fraud report to DB: {e}")
    
    return {
        "success": True,
        "case_reference": result.case_reference,
        "message": f"Fraud report registered. UPI {report.fraud_upi_id} added to blacklist.",
        "timestamp": result.timestamp
    }


# UPGRADE 2: Fraud Network Graph Endpoint
@app.get("/fraud-network")
async def get_fraud_network():
    """
    Get fraud network graph data for visualization.
    Returns nodes and edges with suspicious nodes marked.
    """
    return fraud_network.get_fraud_network_data()


# UPGRADE 3: User Profile Endpoint
@app.get("/user-profile/{user_id}")
async def get_user_profile(user_id: str):
    """
    Get user behavioral profile.
    Shows user's normal transaction patterns.
    """
    profile = user_profile_manager.get_profile(user_id)
    if not profile:
        return {
            "user_id": user_id,
            "message": "New user - no profile yet",
            "avg_amount": 1000.0,
            "usual_hours": [10, 11, 12, 13, 14, 15, 16, 17, 18],
            "transaction_count": 0
        }
    return profile


# UPGRADE 3: Mule Accounts Endpoint
@app.get("/mule-accounts")
async def get_mule_accounts():
    """
    Get list of detected mule accounts.
    Accounts receiving money from 3+ different senders.
    """
    return {
        "mule_accounts": fraud_network.detect_mule_accounts(),
        "count": len(fraud_network.detect_mule_accounts())
    }


# UPGRADE 1: Fraud Reports Endpoint
@app.get("/fraud-reports")
async def get_fraud_reports():
    """
    Get all fraud reports.
    """
    return {
        "reports": fraud_report_manager.get_all_reports(),
        "count": len(fraud_report_manager.get_all_reports())
    }


# UPGRADE 5: Health Check Endpoint
@app.get("/health")
async def health_check():
    """
    System health check.
    """
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "risk_engine": "running",
            "fraud_network": "running",
            "user_profiles": "running",
            "fraud_reports": "running"
        },
        "stats": {
            "total_transactions": len(transactions_store),
            "mule_accounts": len(fraud_network.detect_mule_accounts()),
            "fraud_reports": len(fraud_report_manager.get_all_reports()),
            "user_profiles": len(user_profile_manager.get_all_profiles())
        },
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
