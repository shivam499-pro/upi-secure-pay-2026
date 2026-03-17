from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TransactionInput(BaseModel):
    """Input schema for transaction analysis"""
    transaction_id: str = Field(..., description="Transaction ID")
    amount: float = Field(..., gt=0, description="Transaction amount in INR")
    merchant_name: str = Field(default="Unknown Merchant", description="Merchant name")
    merchant_upi_id: str = Field(..., description="Merchant's UPI ID")
    is_new_merchant: bool = Field(default=False, description="Is this a new merchant")
    hour_of_day: int = Field(default=12, ge=0, le=23, description="Hour of day (0-23)")
    is_new_device: bool = Field(default=False, description="Is this a new device")
    device_rooted: bool = Field(default=False, description="Is device rooted")
    is_on_call: bool = Field(default=False, description="Is user on call during transaction")
    location_changed: bool = Field(default=False, description="Has location changed")
    velocity_last_1hr: int = Field(default=0, description="Number of transactions in last hour")
    user_avg_amount: float = Field(default=1000.0, description="User's average transaction amount")
    swipe_confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Swipe confidence score")


class RiskFactor(BaseModel):
    """Individual risk factor details"""
    name: str
    description: str
    severity: str  # low, medium, high, critical
    weight: float


class TransactionResult(BaseModel):
    """Output schema for transaction analysis result"""
    transaction_id: str
    sender_upi: str
    receiver_upi: str
    amount: float
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: str  # low, medium, high, critical
    is_blocked: bool
    is_alert: bool
    message: str
    risk_factors: List[RiskFactor]
    timestamp: str
    status: str  # approved, blocked, alerted
    sequence_risk_score: Optional[float] = None  # Level 2 LSTM score
    level2_active: Optional[bool] = False  # Is Level 2 LSTM active


class DashboardStats(BaseModel):
    """Dashboard statistics"""
    total_transactions: int
    blocked_transactions: int
    alerted_transactions: int
    approved_transactions: int
    average_risk_score: float
    recent_transactions: List[TransactionResult]
