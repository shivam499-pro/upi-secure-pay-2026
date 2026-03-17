from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from rules import SafetyRuleEngine


def send_fraud_confirmation_email(
    to_email: str,
    case_reference: str,
    fraud_upi_id: str,
    amount_lost: float,
    reported_by: str = "user"
) -> bool:
    """
    Standalone function to send fraud confirmation email.
    Creates a FraudReport object and sends email.
    """
    # Create a mock report for the email
    report = FraudReport(
        transaction_id="N/A",
        fraud_upi_id=fraud_upi_id,
        amount=amount_lost,
        description="",
        reported_by=reported_by,
        user_email=to_email,
        case_reference=case_reference,
        timestamp=datetime.now().isoformat()
    )
    
    # Use the manager to send email
    manager = FraudReportManager()
    return manager.send_fraud_confirmation_email(report)


class FraudReport(BaseModel):
    """Model for fraud report"""
    transaction_id: str = Field(..., description="Related transaction ID")
    fraud_upi_id: str = Field(..., description="UPI ID suspected of fraud")
    amount: float = Field(..., description="Transaction amount")
    description: str = Field(default="", description="Description of fraud")
    reported_by: str = Field(default="user", description="Who reported the fraud")
    user_email: str = Field(default="", description="User email for confirmation")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    case_reference: Optional[str] = Field(None, description="Case reference number")


class FraudReportManager:
    """
    Manages fraud reports and adds fraudulent UPI IDs to blacklist.
    """
    
    # Email configuration (Demo - use environment variables in production)
    SMTP_EMAIL = "sj9988789@gmail.com"  # Replace with your Gmail
    SMTP_PASSWORD = "lmtnbtauffbtvaxr"  # Replace with App Password
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    
    def __init__(self):
        self.reports: List[FraudReport] = []
        self.rule_engine = SafetyRuleEngine()
    
    def send_fraud_confirmation_email(self, report: FraudReport) -> bool:
        """
        Send confirmation email when fraud report is filed.
        Returns True if email sent successfully, False otherwise.
        """
        if not report.user_email:
            print("No user email provided, skipping confirmation email")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.SMTP_EMAIL
            msg['To'] = report.user_email
            msg['Subject'] = "Fraud Report Filed - UPI Secure Pay"
            
            # Email body
            body = f"""Your fraud report has been successfully filed.

Case Reference: {report.case_reference}
Reported UPI ID: {report.fraud_upi_id}
Amount Lost: ₹{report.amount}
Date: {report.timestamp}

Actions taken automatically:
✅ UPI ID blacklisted in our system
✅ Report logged to our fraud database
✅ Future transactions to this UPI will be BLOCKED

Next steps:
• Share Case ID with your bank
• File complaint at cybercrime.gov.in
• Call 1930 helpline

Powered by UPI Secure Pay - Sentinel Squad
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT)
            server.starttls()
            server.login(self.SMTP_EMAIL, self.SMTP_PASSWORD)
            server.sendmail(self.SMTP_EMAIL, report.user_email, msg.as_string())
            server.quit()
            
            print(f"Confirmation email sent to {report.user_email}")
            return True
            
        except Exception as e:
            print(f"Failed to send confirmation email: {e}")
            return False
    
    def process_fraud_report(self, report: FraudReport) -> dict:
        """
        Process a fraud report:
        1. Add the fraud UPI ID to blacklist
        2. Store the report
        3. Generate case reference number
        4. Send confirmation email
        Returns dict with report and email status
        """
        # Generate case reference number
        case_ref = f"UPI-2026-{uuid.uuid4().hex[:8].upper()}"
        
        # Add fraud UPI to blacklist
        fraud_upi_lower = report.fraud_upi_id.lower()
        if fraud_upi_lower not in [upi.lower() for upi in self.rule_engine.BLACKLIST]:
            self.rule_engine.BLACKLIST.append(fraud_upi_lower)
        
        # Store the report with case reference
        report.case_reference = case_ref
        self.reports.append(report)
        
        # Send confirmation email
        email_sent = self.send_fraud_confirmation_email(report)
        
        return {
            "report": report,
            "email_sent": email_sent,
            "message": "Fraud report filed successfully"
        }
    
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
