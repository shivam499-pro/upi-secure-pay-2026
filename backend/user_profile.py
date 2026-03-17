from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from collections import Counter


class UserProfile(BaseModel):
    """Model for user behavioral profile"""
    user_id: str = Field(..., description="User identifier (UPI ID)")
    avg_amount: float = Field(default=1000.0, description="Average transaction amount")
    usual_hours: List[int] = Field(default_factory=lambda: [10, 11, 12, 13, 14, 15, 16, 17, 18], 
                                     description="Usual hours for transactions")
    usual_merchants: List[str] = Field(default_factory=list, description="Frequently used merchants")
    transaction_count: int = Field(default=0, description="Total transaction count")
    risk_score_history: List[float] = Field(default_factory=list, description="History of risk scores")
    recent_transactions: List[Dict] = Field(default_factory=list, description="Recent transactions for LSTM")
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())


class BehavioralDeviation(BaseModel):
    """Model for behavioral deviation analysis"""
    deviation_score: float = Field(..., ge=0.0, le=1.0, description="Overall deviation score")
    amount_deviation: bool = Field(default=False, description="Is amount abnormal?")
    time_deviation: bool = Field(default=False, description="Is transaction time abnormal?")
    merchant_deviation: bool = Field(default=False, description="Is merchant unusual?")
    amount_details: Optional[str] = None
    time_details: Optional[str] = None
    merchant_details: Optional[str] = None


class UserProfileManager:
    """
    Manages user behavioral profiles and detects anomalies.
    """
    
    def __init__(self):
        self.profiles: Dict[str, UserProfile] = {}
        # Learning rate for profile updates
        self.learning_rate = 0.1
    
    def get_or_create_profile(self, user_id: str) -> UserProfile:
        """Get existing profile or create new one"""
        if user_id not in self.profiles:
            self.profiles[user_id] = UserProfile(user_id=user_id)
        return self.profiles[user_id]
    
    def update_user_profile(self, user_id: str, amount: float, merchant_upi: str, 
                           hour_of_day: int, risk_score: float):
        """
        Learn from each transaction and update user profile.
        Uses exponential moving average for smooth updates.
        """
        profile = self.get_or_create_profile(user_id)
        
        # Update average amount
        profile.avg_amount = (1 - self.learning_rate) * profile.avg_amount + \
                            self.learning_rate * amount
        
        # Update usual hours (add to list if common)
        if hour_of_day not in profile.usual_hours:
            # Add hour if it appears frequently
            hour_count = profile.usual_hours.count(hour_of_day)
            if hour_count > 2:
                profile.usual_hours.append(hour_of_day)
        
        # Update usual merchants
        if merchant_upi not in profile.usual_merchants:
            if len(profile.usual_merchants) < 20:  # Keep top 20 merchants
                profile.usual_merchants.append(merchant_upi)
            else:
                # Replace least frequent merchant
                profile.usual_merchants[-1] = merchant_upi
        
        # Update transaction count
        profile.transaction_count += 1
        
        # Update risk score history (keep last 100)
        profile.risk_score_history.append(risk_score)
        if len(profile.risk_score_history) > 100:
            profile.risk_score_history.pop(0)
        
        # Update recent transactions for LSTM sequence analysis
        recent_txn = {
            'amount': amount,
            'hour_of_day': hour_of_day,
            'merchant_upi': merchant_upi,
            'is_new_merchant': merchant_upi not in profile.usual_merchants,
            'is_new_device': False,  # Not tracked in profile
            'velocity_last_1hr': 0,  # Not tracked in profile
            'amount_ratio': amount / profile.avg_amount if profile.avg_amount > 0 else 1.0,
            'swipe_confidence': 0.8  # Default
        }
        profile.recent_transactions.append(recent_txn)
        if len(profile.recent_transactions) > 50:
            profile.recent_transactions.pop(0)
        
        # Update last timestamp
        profile.last_updated = datetime.now().isoformat()
        
        return profile
    
    def get_behavioral_deviation(self, user_id: str, amount: float, 
                                 merchant_upi: str, hour_of_day: int) -> BehavioralDeviation:
        """
        Compare current transaction to user normal behavior.
        Returns deviation score 0-1 and specific deviations found.
        """
        profile = self.get_or_create_profile(user_id)
        
        # If new user with no history, return moderate deviation
        if profile.transaction_count < 5:
            return BehavioralDeviation(
                deviation_score=0.3,
                amount_deviation=False,
                time_deviation=False,
                merchant_deviation=False,
                amount_details="New user - limited history",
                time_details="New user - limited history",
                merchant_details="New user - limited history"
            )
        
        deviation_score = 0.0
        amount_deviation = False
        time_deviation = False
        merchant_deviation = False
        
        # Check amount deviation (if > 3x average, it's significant)
        amount_ratio = amount / profile.avg_amount if profile.avg_amount > 0 else 1
        if amount_ratio > 3:
            deviation_score += 0.4
            amount_deviation = True
            amount_details = f"Amount {amount_ratio:.1f}x higher than average ₹{profile.avg_amount:.0f}"
        elif amount_ratio > 2:
            deviation_score += 0.2
            amount_deviation = True
            amount_details = f"Amount {amount_ratio:.1f}x higher than average"
        
        # Check time deviation
        if hour_of_day not in profile.usual_hours:
            deviation_score += 0.3
            time_deviation = True
            time_details = f"Unusual hour: {hour_of_day}:00 (usual: {profile.usual_hours[:5]}...)"
        
        # Check merchant deviation
        if merchant_upi not in profile.usual_merchants:
            deviation_score += 0.3
            merchant_deviation = True
            merchant_details = f"New merchant: {merchant_upi}"
        
        # Cap deviation score at 1.0
        deviation_score = min(deviation_score, 1.0)
        
        return BehavioralDeviation(
            deviation_score=round(deviation_score, 2),
            amount_deviation=amount_deviation,
            time_deviation=time_deviation,
            merchant_deviation=merchant_deviation,
            amount_details=amount_details if amount_deviation else None,
            time_details=time_details if time_deviation else None,
            merchant_details=merchant_details if merchant_deviation else None
        )
    
    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile"""
        return self.profiles.get(user_id)
    
    def get_all_profiles(self) -> List[UserProfile]:
        """Get all user profiles"""
        return list(self.profiles.values())


# Global instance
user_profile_manager = UserProfileManager()
