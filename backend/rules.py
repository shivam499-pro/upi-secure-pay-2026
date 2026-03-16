from typing import List, Dict
from schemas import TransactionInput, RiskFactor


class SafetyRuleEngine:
    """
    Safety Rule Engine for fraud detection and scam prevention.
    Implements blacklist checking and keyword-based scam detection.
    """
    
    # Known fraudulent UPI IDs (blacklist)
    BLACKLIST: List[str] = [
        "fraud@upi",
        "scam@upi",
        "fake@upi",
        "cheat@upi",
        "kon@upi",
        "money@upi",
        "win@upi",
        "prize@upi",
        "gift@upi",
        "reward@upi",
        "free@upi",
        "cash@upi",
        "bonus@upi",
        "offer@upi",
        "deal@upi",
        "limited@upi",
        "urgent@upi",
        "act@upi",
        "now@upi",
        "hurry@upi",
    ]
    
    # Scam-related keywords in transaction description
    SCAM_KEYWORDS: Dict[str, float] = {
        # Prize/Lottery scams
        "prize": 25.0,
        "lottery": 30.0,
        "winner": 25.0,
        "won": 20.0,
        "congratulations": 15.0,
        "selected": 15.0,
        
        # Investment scams
        "investment": 20.0,
        "returns": 15.0,
        "double": 20.0,
        "guaranteed": 25.0,
        "profit": 15.0,
        "100%": 25.0,
        "double money": 30.0,
        
        # Urgency/Fear tactics
        "urgent": 15.0,
        "act now": 20.0,
        "limited time": 15.0,
        "expire": 15.0,
        "last chance": 20.0,
        "hurry": 15.0,
        
        # KYC/Account scams
        "kyc": 20.0,
        "verify account": 25.0,
        "account blocked": 25.0,
        "suspended": 20.0,
        "update kyc": 25.0,
        
        # Refund scams
        "refund": 15.0,
        "money back": 20.0,
        "claim": 10.0,
        
        # Gift/Offer scams
        "free gift": 25.0,
        "free money": 30.0,
        "bonus": 15.0,
        "cashback": 10.0,
        "reward": 10.0,
        "offer": 10.0,
        
        # Tech support scams
        "support": 10.0,
        "customer care": 15.0,
        "helpdesk": 15.0,
        
        # Impersonation
        "govt": 20.0,
        "government": 20.0,
        "bank": 15.0,
        "police": 20.0,
        "court": 20.0,
    }
    
    # High amount thresholds
    HIGH_AMOUNT_THRESHOLD: float = 50000.0
    SUSPICIOUS_AMOUNT_THRESHOLD: float = 100000.0
    
    # Suspicious patterns in UPI IDs
    SUSPICIOUS_UPI_PATTERNS: List[str] = [
        "999999",
        "888888",
        "777777",
        "000000",
        "123456",
        "fake",
        "test",
    ]
    
    # New merchant risk
    NEW_MERCHANT_ADDED_RISK: float = 20.0
    
    # New device risk
    NEW_DEVICE_ADDED_RISK: float = 15.0
    
    # Device rooted risk
    ROOTED_DEVICE_ADDED_RISK: float = 35.0
    
    # On call risk
    ON_CALL_ADDED_RISK: float = 25.0
    
    # Location changed risk
    LOCATION_CHANGED_ADDED_RISK: float = 15.0
    
    # Suspicious hours (late night/early morning)
    SUSPICIOUS_HOURS: List[int] = [0, 1, 2, 3, 4, 5]
    
    # High velocity threshold
    HIGH_VELOCITY_THRESHOLD: int = 5
    
    # Low confidence threshold
    LOW_CONFIDENCE_THRESHOLD: float = 0.5
    
    def check_blacklist(self, upi_id: str) -> List[RiskFactor]:
        """Check if UPI ID is in the blacklist"""
        risk_factors = []
        upi_lower = upi_id.lower()
        
        for blacklisted in self.BLACKLIST:
            if blacklisted in upi_lower:
                risk_factors.append(RiskFactor(
                    name="Blacklisted UPI ID",
                    description=f"UPI ID '{upi_id}' matches known fraudulent account",
                    severity="critical",
                    weight=50.0
                ))
                break
        
        return risk_factors
    
    def check_scam_keywords(self, description: str) -> List[RiskFactor]:
        """Check for scam keywords in transaction description"""
        risk_factors = []
        desc_lower = description.lower()
        
        for keyword, weight in self.SCAM_KEYWORDS.items():
            if keyword in desc_lower:
                risk_factors.append(RiskFactor(
                    name=f"Suspicious keyword: '{keyword}'",
                    description=f"Transaction description contains potentially fraudulent keyword '{keyword}'",
                    severity="high" if weight >= 25 else "medium",
                    weight=weight
                ))
        
        return risk_factors
    
    def check_suspicious_upi_pattern(self, upi_id: str) -> List[RiskFactor]:
        """Check for suspicious patterns in UPI ID"""
        risk_factors = []
        upi_lower = upi_id.lower()
        
        for pattern in self.SUSPICIOUS_UPI_PATTERNS:
            if pattern in upi_lower:
                risk_factors.append(RiskFactor(
                    name="Suspicious UPI ID pattern",
                    description=f"UPI ID contains suspicious pattern '{pattern}'",
                    severity="medium",
                    weight=15.0
                ))
                break
        
        return risk_factors
    
    def check_amount_threshold(self, amount: float) -> List[RiskFactor]:
        """Check for unusually high transaction amounts"""
        risk_factors = []
        
        if amount >= self.SUSPICIOUS_AMOUNT_THRESHOLD:
            risk_factors.append(RiskFactor(
                name="Very High Amount",
                description=f"Transaction amount ₹{amount:,.2f} exceeds suspicious threshold",
                severity="high",
                weight=30.0
            ))
        elif amount >= self.HIGH_AMOUNT_THRESHOLD:
            risk_factors.append(RiskFactor(
                name="High Amount",
                description=f"Transaction amount ₹{amount:,.2f} is above typical threshold",
                severity="medium",
                weight=15.0
            ))
        
        return risk_factors
    
    def check_new_merchant(self, is_new_merchant: bool) -> List[RiskFactor]:
        """Check if merchant is new"""
        risk_factors = []
        if is_new_merchant:
            risk_factors.append(RiskFactor(
                name="New Merchant",
                description="Transaction to a new merchant",
                severity="medium",
                weight=self.NEW_MERCHANT_ADDED_RISK
            ))
        return risk_factors
    
    def check_new_device(self, is_new_device: bool) -> List[RiskFactor]:
        """Check if device is new"""
        risk_factors = []
        if is_new_device:
            risk_factors.append(RiskFactor(
                name="New Device",
                description="Transaction from a new device",
                severity="medium",
                weight=self.NEW_DEVICE_ADDED_RISK
            ))
        return risk_factors
    
    def check_device_rooted(self, device_rooted: bool) -> List[RiskFactor]:
        """Check if device is rooted"""
        risk_factors = []
        if device_rooted:
            risk_factors.append(RiskFactor(
                name="Rooted Device",
                description="Device appears to be rooted/jailbroken",
                severity="critical",
                weight=self.ROOTED_DEVICE_ADDED_RISK
            ))
        return risk_factors
    
    def check_on_call(self, is_on_call: bool) -> List[RiskFactor]:
        """Check if user is on call during transaction"""
        risk_factors = []
        if is_on_call:
            risk_factors.append(RiskFactor(
                name="On Call",
                description="User is on a call during transaction (common scam indicator)",
                severity="high",
                weight=self.ON_CALL_ADDED_RISK
            ))
        return risk_factors
    
    def check_location_changed(self, location_changed: bool) -> List[RiskFactor]:
        """Check if location has changed"""
        risk_factors = []
        if location_changed:
            risk_factors.append(RiskFactor(
                name="Location Changed",
                description="Device location changed since last transaction",
                severity="medium",
                weight=self.LOCATION_CHANGED_ADDED_RISK
            ))
        return risk_factors
    
    def check_suspicious_hours(self, hour_of_day: int) -> List[RiskFactor]:
        """Check for suspicious transaction hours"""
        risk_factors = []
        if hour_of_day in self.SUSPICIOUS_HOURS:
            risk_factors.append(RiskFactor(
                name="Suspicious Hour",
                description=f"Transaction at {hour_of_day}:00 (late night/early morning)",
                severity="medium",
                weight=15.0
            ))
        return risk_factors
    
    def check_velocity(self, velocity: int) -> List[RiskFactor]:
        """Check transaction velocity"""
        risk_factors = []
        if velocity >= self.HIGH_VELOCITY_THRESHOLD:
            risk_factors.append(RiskFactor(
                name="High Velocity",
                description=f"{velocity} transactions in the last hour",
                severity="high",
                weight=min(velocity * 5, 30.0)
            ))
        return risk_factors
    
    def check_amount_deviation(self, amount: float, avg_amount: float) -> List[RiskFactor]:
        """Check if amount significantly deviates from user's average"""
        risk_factors = []
        if avg_amount > 0:
            ratio = amount / avg_amount
            if ratio >= 5:
                risk_factors.append(RiskFactor(
                    name="High Amount Deviation",
                    description=f"Amount is {ratio:.1f}x higher than user's average",
                    severity="high",
                    weight=25.0
                ))
            elif ratio >= 3:
                risk_factors.append(RiskFactor(
                    name="Amount Deviation",
                    description=f"Amount is {ratio:.1f}x higher than user's average",
                    severity="medium",
                    weight=15.0
                ))
        return risk_factors
    
    def check_swipe_confidence(self, confidence: float) -> List[RiskFactor]:
        """Check swipe confidence score"""
        risk_factors = []
        if confidence <= self.LOW_CONFIDENCE_THRESHOLD:
            risk_factors.append(RiskFactor(
                name="Low Swipe Confidence",
                description=f"Swipe confidence score {confidence} is very low",
                severity="high",
                weight=20.0
            ))
        elif confidence < 0.7:
            risk_factors.append(RiskFactor(
                name="Below Average Confidence",
                description=f"Swipe confidence score {confidence} is below average",
                severity="medium",
                weight=10.0
            ))
        return risk_factors
    
    def analyze_transaction(self, transaction: TransactionInput) -> List[RiskFactor]:
        """
        Analyze a transaction and return all identified risk factors.
        """
        all_risk_factors = []
        
        # Check merchant UPI against blacklist
        all_risk_factors.extend(self.check_blacklist(transaction.merchant_upi_id))
        
        # Check suspicious UPI patterns
        all_risk_factors.extend(self.check_suspicious_upi_pattern(transaction.merchant_upi_id))
        
        # Check amount thresholds
        all_risk_factors.extend(self.check_amount_threshold(transaction.amount))
        
        # Check new merchant
        all_risk_factors.extend(self.check_new_merchant(transaction.is_new_merchant))
        
        # Check new device
        all_risk_factors.extend(self.check_new_device(transaction.is_new_device))
        
        # Check rooted device
        all_risk_factors.extend(self.check_device_rooted(transaction.device_rooted))
        
        # Check on call
        all_risk_factors.extend(self.check_on_call(transaction.is_on_call))
        
        # Check location changed
        all_risk_factors.extend(self.check_location_changed(transaction.location_changed))
        
        # Check suspicious hours
        all_risk_factors.extend(self.check_suspicious_hours(transaction.hour_of_day))
        
        # Check velocity
        all_risk_factors.extend(self.check_velocity(transaction.velocity_last_1hr))
        
        # Check amount deviation from average
        all_risk_factors.extend(self.check_amount_deviation(transaction.amount, transaction.user_avg_amount))
        
        # Check swipe confidence
        all_risk_factors.extend(self.check_swipe_confidence(transaction.swipe_confidence))
        
        return all_risk_factors
