from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import asyncio
import json
import random
from datetime import datetime
from schemas import TransactionInput, TransactionResult, DashboardStats
from risk_engine import RiskEngine

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
    """
    try:
        result = risk_engine.analyze_transaction(transaction)
        
        # Store transaction
        transactions_store.insert(0, result)
        
        # Keep only last 100 transactions
        if len(transactions_store) > 100:
            transactions_store.pop()
        
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
    if not transactions_store:
        # Generate some sample data if no transactions yet
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
    """Generate initial sample data"""
    for _ in range(10):
        sample = generate_sample_transaction()
        # Occasionally add high risk factors
        if random.random() < 0.3:
            sample.device_rooted = True
            sample.is_on_call = True
        result = risk_engine.analyze_transaction(sample)
        transactions_store.append(result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
