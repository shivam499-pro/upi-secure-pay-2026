from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid
from rules import SafetyRuleEngine


class FraudReport(BaseModel):
    """Model for fraud report"""
    transaction_id: str = Field(..., description="Related transaction ID")
    fraud_upi_id: str = Field(..., description="UPI ID suspected of fraud")
    amount: float = Field(..., description="Transaction amount")
    description: str = Field(default="", description="Description of fraud")
    reported_by: str = Field(default="user", description="Who reported the fraud")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    case_reference: Optional[str] = Field(None, description="Case reference number")


class FraudReportManager:
    """
    Manages fraud reports and adds fraudulent UPI IDs to blacklist.
    """
    
    def __init__(self):
        self.reports: List[FraudReport] = []
        self.rule_engine = SafetyRuleEngine()
    
    def process_fraud_report(self, report: FraudReport) -> FraudReport:
        """
        Process a fraud report:
        1. Add the fraud UPI ID to blacklist
        2. Store the report
        3. Generate case reference number
        """
        # Generate case reference number
        case_ref = f"FR-{uuid.uuid4().hex[:8].upper()}"
        
        # Add fraud UPI to blacklist
        fraud_upi_lower = report.fraud_upi_id.lower()
        if fraud_upi_lower not in [upi.lower() for upi in self.rule_engine.BLACKLIST]:
            self.rule_engine.BLACKLIST.append(fraud_upi_lower)
        
        # Store the report with case reference
        report.case_reference = case_ref
        self.reports.append(report)
        
        return report
    
    def get_all_reports(self) -> List[FraudReport]:
        """Get all fraud reports"""
        return self.reports
    
    def get_report_by_reference(self, case_reference: str) -> Optional[FraudReport]:
        """Get a specific report by case reference"""
        for report in self.reports:
            if report.case_reference == case_reference:
                return report
        return None


# Global instance
fraud_report_manager = FraudReportManager()
