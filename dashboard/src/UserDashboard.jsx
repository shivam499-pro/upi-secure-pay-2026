import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './UserDashboard.css';

const API_BASE = 'http://127.0.0.1:8000';

function UserDashboard() {
  const [upiId, setUpiId] = useState('');
  const [amount, setAmount] = useState('');
  const [checkResult, setCheckResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [userProfile, setUserProfile] = useState(null);
  const [showFraudModal, setShowFraudModal] = useState(false);
  const [fraudForm, setFraudForm] = useState({
    transaction_id: '',
    fraud_upi_id: '',
    amount: 0,
    description: '',
    reported_by: 'user',
    user_email: ''
  });
  const [expandedReasons, setExpandedReasons] = useState({});

  // Fetch user profile
  useEffect(() => {
    fetchUserProfile();
    fetchTransactions();
    const interval = setInterval(fetchTransactions, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchUserProfile = async () => {
    try {
      const res = await axios.get(`${API_BASE}/user-profile/user@upi`);
      setUserProfile(res.data);
    } catch (err) {
      console.error('Error fetching profile:', err);
    }
  };

  const fetchTransactions = async () => {
    try {
      const res = await axios.get(`${API_BASE}/transactions?limit=8`);
      setTransactions(res.data);
    } catch (err) {
      console.error('Error fetching transactions:', err);
    }
  };

  const checkRisk = async () => {
    if (!upiId || !amount) {
      alert('Please enter both UPI ID and amount');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        transaction_id: 'CHECK_' + Date.now(),
        amount: parseFloat(amount),
        merchant_name: 'Unknown Merchant',
        merchant_upi_id: upiId,
        is_new_merchant: true,
        hour_of_day: new Date().getHours(),
        is_new_device: false,
        device_rooted: false,
        is_on_call: false,
        location_changed: false,
        velocity_last_1hr: 0,
        user_avg_amount: 1000,
        swipe_confidence: 0.8
      };

      const res = await axios.post(`${API_BASE}/analyze-transaction`, payload);
      setCheckResult(res.data);
    } catch (err) {
      console.error('Error checking risk:', err);
      alert('Error checking risk. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const submitFraudReport = async () => {
    try {
      await axios.post(`${API_BASE}/report-fraud`, {
        ...fraudForm,
        transaction_id: 'REPORT_' + Date.now(),
        amount: parseFloat(fraudForm.amount) || 0
      });
      alert('Fraud report submitted successfully!');
      setShowFraudModal(false);
      setFraudForm({
        transaction_id: '',
        fraud_upi_id: '',
        amount: 0,
        description: '',
        reported_by: 'user',
        user_email: ''
      });
    } catch (err) {
      alert('Error submitting report. Please try again.');
    }
  };

  const toggleReasons = (txnId) => {
    setExpandedReasons(prev => ({
      ...prev,
      [txnId]: !prev[txnId]
    }));
  };

  const getDecisionColor = (status) => {
    if (status === 'BLOCK' || status === 'blocked') return '#ff4444';
    if (status === 'ALERT' || status === 'alerted') return '#ffaa00';
    return '#00cc66';
  };

  return (
    <div className="user-dashboard">
      {/* SECTION 1: Personal Header */}
      <div className="user-header">
        <div className="user-header-content">
          <h1 className="user-title">🛡️ Your Payment Guardian</h1>
          <p className="user-name">Welcome, Shivam</p>
        </div>
        <div className="safety-score-card">
          <div className="safety-score-circle">
            <span className="safety-score-number">94</span>
            <span className="safety-score-label">/100</span>
          </div>
          <div className="safety-status">
            <span className="blinking-dot"></span>
            <span className="status-text">PROTECTED</span>
          </div>
          <p className="status-message">Your payments are protected</p>
        </div>
      </div>

      {/* SECTION 2: AI Behavior Profile */}
      <div className="profile-card">
        <h2 className="section-title">🤖 What Our AI Learned About You</h2>
        {userProfile ? (
          <div className="profile-stats">
            <div className="profile-stat">
              <span className="stat-label">Usual Amount</span>
              <span className="stat-value">₹{userProfile.avg_amount?.toFixed(0) || '200'} - ₹{(userProfile.avg_amount * 7.5)?.toFixed(0) || '1,500'}</span>
            </div>
            <div className="profile-stat">
              <span className="stat-label">Usual Time</span>
              <span className="stat-value">{userProfile.common_hours?.[0] || '10'}am - {userProfile.common_hours?.[userProfile.common_hours?.length-1] || '10'}pm</span>
            </div>
            <div className="profile-stat">
              <span className="stat-label">Transactions</span>
              <span className="stat-value">{userProfile.transaction_count || 0} payments analyzed</span>
            </div>
            <div className="profile-stat">
              <span className="stat-label">Avg Risk Score</span>
              <span className="stat-value">{userProfile.avg_risk_score?.toFixed(1) || '0'}%</span>
            </div>
          </div>
        ) : (
          <p>Loading your profile...</p>
        )}
        <p className="ai-note"><em>Our AI analyzes your patterns to protect you</em></p>
      </div>

      {/* SECTION 3: Pre-Payment Risk Checker */}
      <div className="risk-checker-card">
        <h2 className="section-title">🔒 Check Before You Pay</h2>
        <p className="checker-subtitle">Know if a payment is safe BEFORE sending money</p>
        
        <div className="checker-form">
          <input
            type="text"
            placeholder="merchant@upi"
            value={upiId}
            onChange={(e) => setUpiId(e.target.value)}
            className="checker-input"
          />
          <input
            type="number"
            placeholder="Enter amount"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="checker-input"
          />
          <button 
            onClick={checkRisk} 
            disabled={loading}
            className="checker-button"
          >
            {loading ? 'Checking...' : 'CHECK RISK NOW'}
          </button>
        </div>

        {checkResult && (
          <div className={`result-card ${checkResult.status}`}>
            {checkResult.status === 'approved' && (
              <>
                <div className="result-header approved">
                  <span className="result-icon">✅</span>
                  <span className="result-title">SAFE TO PAY</span>
                </div>
                <p className="result-score">Risk Score: {checkResult.risk_score?.toFixed(1)}%</p>
                <p className="result-message">This transaction matches your normal pattern</p>
                <button className="proceed-button">Proceed with Payment</button>
              </>
            )}
            
            {checkResult.status === 'alerted' && (
              <>
                <div className="result-header alerted">
                  <span className="result-icon">⚠️</span>
                  <span className="result-title">PROCEED WITH CAUTION</span>
                </div>
                <p className="result-score">Risk Score: {checkResult.risk_score?.toFixed(1)}%</p>
                {checkResult.risk_factors && checkResult.risk_factors.length > 0 && (
                  <ul className="result-reasons">
                    {checkResult.risk_factors.map((rf, idx) => (
                      <li key={idx}>{rf.name || rf.description}</li>
                    ))}
                  </ul>
                )}
                <p className="result-message">Verify this merchant before paying</p>
                <button className="caution-button">Verify & Proceed</button>
              </>
            )}
            
            {checkResult.status === 'blocked' && (
              <>
                <div className="result-header blocked">
                  <span className="result-icon">🚨</span>
                  <span className="result-title">DO NOT PAY — FRAUD DETECTED</span>
                </div>
                <p className="result-score">Risk Score: {checkResult.risk_score?.toFixed(1)}%</p>
                {checkResult.risk_factors && checkResult.risk_factors.length > 0 && (
                  <ul className="result-reasons danger">
                    {checkResult.risk_factors.map((rf, idx) => (
                      <li key={idx}>{rf.name || rf.description}</li>
                    ))}
                  </ul>
                )}
                <p className="result-message danger-text">Our AI detected fraud patterns</p>
                <p className="result-warning">Do NOT proceed with this payment</p>
                <button className="danger-button">DO NOT PROCEED</button>
              </>
            )}
          </div>
        )}
      </div>

      {/* SECTION 4: Recent Transactions */}
      <div className="transactions-card">
        <h2 className="section-title">📜 Your Recent Transactions</h2>
        <div className="transactions-grid">
          {transactions.map((txn) => (
            <div key={txn.transaction_id} className="transaction-card">
              <div className="txn-header">
                <span className="txn-merchant">{txn.merchant_name || txn.receiver_upi}</span>
                <span 
                  className="txn-badge"
                  style={{ backgroundColor: getDecisionColor(txn.status || txn.decision) }}
                >
                  {txn.status || txn.decision}
                </span>
              </div>
              <p className="txn-upi">{txn.merchant_upi_id || txn.receiver_upi}</p>
              <p className="txn-amount">₹{txn.amount?.toFixed(2)}</p>
              <p className="txn-risk">Risk: {txn.risk_score?.toFixed(1)}%</p>
              <button 
                className="why-button"
                onClick={() => toggleReasons(txn.transaction_id)}
              >
                Why? {expandedReasons[txn.transaction_id] ? '▲' : '▼'}
              </button>
              {expandedReasons[txn.transaction_id] && (
                <div className="txn-reasons">
                  {txn.message || (txn.risk_factors && txn.risk_factors.map((rf, idx) => (
                    <p key={idx}>• {rf.name || rf.description}</p>
                  )))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* SECTION 5: Safety Tips */}
      <div className="safety-tips-card">
        <h2 className="section-title">🛡️ Stay Protected</h2>
        <div className="tips-grid">
          <div className="tip-card danger">
            <span className="tip-icon">🚫</span>
            <span className="tip-text">Never share OTP</span>
          </div>
          <div className="tip-card warning">
            <span className="tip-icon">🔍</span>
            <span className="tip-text">Check UPI ID before paying</span>
          </div>
          <div className="tip-card orange">
            <span className="tip-icon">📞</span>
            <span className="tip-text">Beware of calls asking for payments</span>
          </div>
          <div className="tip-card success">
            <span className="tip-icon">✅</span>
            <span className="tip-text">Use Risk Checker before large payments</span>
          </div>
        </div>
      </div>

      {/* SECTION 6: Report Fraud Button */}
      <div className="report-fraud-section">
        <button 
          className="report-fraud-button"
          onClick={() => setShowFraudModal(true)}
        >
          🚨 REPORT FRAUD
        </button>
      </div>

      {/* Fraud Report Modal */}
      {showFraudModal && (
        <div className="modal-overlay" onClick={() => setShowFraudModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">🚨 Report Fraud</h2>
            <input
              type="text"
              placeholder="Fraud UPI ID"
              value={fraudForm.fraud_upi_id}
              onChange={(e) => setFraudForm({...fraudForm, fraud_upi_id: e.target.value})}
              className="modal-input"
            />
            <input
              type="number"
              placeholder="Amount Lost (₹)"
              value={fraudForm.amount}
              onChange={(e) => setFraudForm({...fraudForm, amount: e.target.value})}
              className="modal-input"
            />
            <textarea
              placeholder="Description of fraud"
              value={fraudForm.description}
              onChange={(e) => setFraudForm({...fraudForm, description: e.target.value})}
              className="modal-textarea"
            />
            <input
              type="email"
              placeholder="Your Email (for confirmation)"
              value={fraudForm.user_email}
              onChange={(e) => setFraudForm({...fraudForm, user_email: e.target.value})}
              className="modal-input"
            />
            <div className="modal-buttons">
              <button onClick={() => setShowFraudModal(false)} className="cancel-button">Cancel</button>
              <button onClick={submitFraudReport} className="submit-button">Submit Report</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default UserDashboard;
