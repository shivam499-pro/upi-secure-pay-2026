from typing import List, Tuple
from schemas import TransactionInput, RiskFactor, TransactionResult
from rules import SafetyRuleEngine
import uuid
from datetime import datetime
import hashlib


class RiskEngine:
    """
    Risk Score Calculator using rule-based scoring and ML model simulation.
    Calculates risk scores based on multiple factors.
    """
    
    def __init__(self):
        self.rule_engine = SafetyRuleEngine()
        # Maximum possible risk score
        self.MAX_RISK_SCORE = 100.0
        # Thresholds for risk levels
        self.BLOCK_THRESHOLD = 75.0
        self.ALERT_THRESHOLD = 50.0
    
    def calculate_base_risk_score(self, risk_factors: List[RiskFactor]) -> float:
        """
        Calculate base risk score from identified risk factors.
        Uses weighted summation of all factors.
        """
        if not risk_factors:
            return 0.0
        
        total_weight = sum(factor.weight for factor in risk_factors)
        
        # Cap at max score
        return min(total_weight, self.MAX_RISK_SCORE)
    
    def apply_ml_adjustment(self, base_score: float, transaction: TransactionInput) -> float:
        """
        Apply ML model-based adjustment to the risk score.
        This simulates a LightGBM model prediction.
        In production, this would load and use an actual trained model.
        """
        # Simulated ML model features and adjustments
        # Feature: Amount relative to typical transaction
        amount_factor = 1.0
        if transaction.amount > 100000:
            amount_factor = 1.2
        elif transaction.amount > 50000:
            amount_factor = 1.1
        elif transaction.amount < 1000:
            amount_factor = 0.9
        
        # Feature: Transaction velocity factor
        velocity_factor = 1.0
        if transaction.velocity_last_1hr > 10:
            velocity_factor = 1.3
        elif transaction.velocity_last_1hr > 5:
            velocity_factor = 1.15
        
        # Feature: Swipe confidence factor
        confidence_factor = 1.0
        if transaction.swipe_confidence < 0.3:
            confidence_factor = 1.4
        elif transaction.swipe_confidence < 0.5:
            confidence_factor = 1.2
        elif transaction.swipe_confidence > 0.9:
            confidence_factor = 0.9
        
        # Feature: Time of day factor
        time_factor = 1.0
        if transaction.hour_of_day in [0, 1, 2, 3, 4, 5]:
            time_factor = 1.15
        
        # Feature: New merchant factor
        merchant_factor = 1.0
        if transaction.is_new_merchant:
            merchant_factor = 1.1
        
        # Feature: Device factor
        device_factor = 1.0
        if transaction.is_new_device:
            device_factor = 1.05
        if transaction.device_rooted:
            device_factor = 1.3
        
        # Calculate adjusted score
        adjusted_score = base_score * amount_factor * velocity_factor * confidence_factor * time_factor * merchant_factor * device_factor
        
        return min(adjusted_score, self.MAX_RISK_SCORE)
    
    def determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level based on score"""
        if risk_score >= self.BLOCK_THRESHOLD:
            return "critical"
        elif risk_score >= 60:
            return "high"
        elif risk_score >= 30:
            return "medium"
        else:
            return "low"
    
    def determine_action(self, risk_score: float) -> Tuple[bool, bool, str]:
        """
        Determine if transaction should be blocked or alerted.
        Returns: (is_blocked, is_alert, message)
        """
        if risk_score >= self.BLOCK_THRESHOLD:
            return True, False, "Transaction blocked: High fraud risk detected"
        elif risk_score >= self.ALERT_THRESHOLD:
            return False, True, "Transaction flagged for review: Elevated risk detected"
        else:
            return False, False, "Transaction approved: Low risk"
    
    def analyze_transaction(self, transaction: TransactionInput) -> TransactionResult:
        """
        Complete transaction analysis returning full result.
        """
        # Get timestamp
        timestamp = datetime.now().isoformat()
        
        # Run rule engine to get risk factors
        risk_factors = self.rule_engine.analyze_transaction(transaction)
        
        # Calculate base risk score from rules
        base_score = self.calculate_base_risk_score(risk_factors)
        
        # Apply ML adjustment
        final_score = self.apply_ml_adjustment(base_score, transaction)
        
        # Round to 2 decimal places
        final_score = round(final_score, 2)
        
        # Determine risk level
        risk_level = self.determine_risk_level(final_score)
        
        # Determine action
        is_blocked, is_alert, message = self.determine_action(final_score)
        
        # Use provided transaction_id or generate new one
        transaction_id = transaction.transaction_id or f"TXN{hashlib.sha256(timestamp.encode()).hexdigest()[:10].upper()}"
        
        # Determine status
        if is_blocked:
            status = "blocked"
        elif is_alert:
            status = "alerted"
        else:
            status = "approved"
        
        return TransactionResult(
            transaction_id=transaction_id,
            sender_upi="user@upi",  # Default since not provided
            receiver_upi=transaction.merchant_upi_id,
            amount=transaction.amount,
            risk_score=final_score,
            risk_level=risk_level,
            is_blocked=is_blocked,
            is_alert=is_alert,
            message=message,
            risk_factors=risk_factors,
            timestamp=timestamp,
            status=status
        )
