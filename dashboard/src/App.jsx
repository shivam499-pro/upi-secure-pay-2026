import { useState, useEffect } from 'react';
import axios from 'axios';
import UserDashboard from './UserDashboard';
import Login from './Login';
import { isLoggedIn, getUser, logout } from './auth';
import './App.css';

// Custom Hooks
import { useWebSocket } from './hooks/useWebSocket';
import { useBiometrics } from './hooks/useBiometrics';

// Modular Components
import { 
  StatsBar, 
  FraudNetworkSection, 
  TransactionAnalyzerForm, 
  RiskTrendChart, 
  LiveTransactionFeed 
} from './components/DashboardComponents';

const API_BASE = 'http://localhost:8000';

function App() {
  const [activeTab, setActiveTab] = useState('admin');
  const [loggedIn, setLoggedIn] = useState(isLoggedIn());
  const [currentUser, setCurrentUser] = useState(getUser());
  
  // Dashboard Data State
  const [stats, setStats] = useState({
    total_transactions: 0,
    blocked_transactions: 0,
    alerted_transactions: 0,
    approved_transactions: 0,
    average_risk_score: 0,
    recent_transactions: []
  });
  const [chartData, setChartData] = useState([]);
  const [networkData, setNetworkData] = useState({ nodes: [], edges: [] });
  const [muleAccounts, setMuleAccounts] = useState([]);
  
  // Analysis State
  const [showResult, setShowResult] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [latency, setLatency] = useState(0);
  
  // Form State
  const [formData, setFormData] = useState({
    receiver_upi: '',
    amount: '',
    description: '',
    merchant_name: '',
    is_on_call: false,
    is_new_device: false,
    location_changed: false,
    device_rooted: false,
    hour_of_day: new Date().getHours(),
    velocity_last_1hr: 0,
    user_avg_amount: 2000,
  });

  // Modal State
  const [showFraudModal, setShowFraudModal] = useState(false);
  const [fraudReport, setFraudReport] = useState({
    fraud_upi_id: '',
    amount: '',
    description: '',
    reported_by: '',
    user_email: ''
  });

  // Custom Hooks
  const { wsConnected, liveTransactions } = useWebSocket();
  const { 
    behavioralData, 
    handleFormFocus, 
    handleTyping, 
    handlePaste, 
    handleMouseMove, 
    calculateScore,
    resetBiometrics 
  } = useBiometrics();

  // Data Fetching
  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE}/dashboard-stats`);
      setStats(response.data);
      
      const newChartData = response.data.recent_transactions?.slice(0, 10).reverse().map((t, i) => ({
        name: `T${i + 1}`,
        risk: t.risk_score,
        amount: t.amount
      })) || [];
      setChartData(newChartData);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const fetchNetworkData = async () => {
    try {
      const response = await axios.get(`${API_BASE}/fraud-network`);
      setNetworkData(response.data);
      setMuleAccounts(response.data.mule_accounts || []);
    } catch (error) {
      console.error('Error fetching network data:', error);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchNetworkData();
    const intervalStats = setInterval(fetchStats, 3000);
    const intervalNetwork = setInterval(fetchNetworkData, 5000);
    return () => {
      clearInterval(intervalStats);
      clearInterval(intervalNetwork);
    };
  }, []);

  // Handlers
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({ 
      ...prev, 
      [name]: type === 'checkbox' ? checked : value 
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const startTime = Date.now();
    const behavioralScore = calculateScore();
    
    try {
      const payload = {
        transaction_id: "TXN" + Date.now(),
        amount: parseFloat(formData.amount),
        merchant_name: formData.merchant_name || "Unknown Merchant",
        merchant_upi_id: formData.receiver_upi,
        is_new_merchant: true,
        hour_of_day: formData.hour_of_day,
        is_new_device: formData.is_new_device,
        device_rooted: formData.device_rooted,
        is_on_call: formData.is_on_call,
        location_changed: formData.location_changed,
        velocity_last_1hr: formData.velocity_last_1hr,
        user_avg_amount: formData.user_avg_amount,
        swipe_confidence: behavioralScore
      };
      
      const response = await axios.post(`${API_BASE}/analyze-transaction`, payload);
      setLatency(Date.now() - startTime);
      setAnalysisResult(response.data);
      setShowResult(true);
      fetchStats();
      fetchNetworkData();
      resetBiometrics();
    } catch (error) {
      console.error('Error analyzing transaction:', error);
    }
  };

  const handleFraudReportSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_BASE}/report-fraud`, fraudReport);
      setShowFraudModal(false);
      fetchNetworkData();
      alert('Fraud reported successfully!');
    } catch (error) {
      console.error('Error reporting fraud:', error);
    }
  };

  if (activeTab === 'user') {
    return (
      <div className="app">
        <div className="tab-navigation">
          <button className="tab-button" onClick={() => setActiveTab('admin')}>📊 Admin Dashboard</button>
          <button className="tab-button active">🛡️ My Safety Dashboard</button>
        </div>
        <UserDashboard />
      </div>
    );
  }

  if (!loggedIn) {
    return <Login onLoginSuccess={() => {
      setLoggedIn(true);
      setCurrentUser(getUser());
    }} />;
  }

  return (
    <div className="app">
      <div className="tab-navigation">
        <button className="tab-button active">📊 Admin Dashboard</button>
        <button className="tab-button" onClick={() => setActiveTab('user')}>🛡️ My Safety Dashboard</button>
      </div>
      
      <header className="header">
        <div className="header-left">
          <h1>UPI Secure Pay</h1>
          <span className="subtitle">Sentinel AI Fraud Prevention</span>
        </div>
        <div className="header-right">
          <button className="fraud-report-btn" onClick={() => setShowFraudModal(true)}>REPORT FRAUD</button>
          <button className="logout-btn" onClick={() => { logout(); setLoggedIn(false); }}>LOGOUT ({currentUser?.role})</button>
          <div className={`live-indicator ${wsConnected ? 'connected' : ''}`}>
            <span className="live-dot"></span>
            <span className="live-text">LIVE</span>
          </div>
        </div>
      </header>

      <StatsBar stats={stats} />
      
      <FraudNetworkSection networkData={networkData} muleAccounts={muleAccounts} />

      <div className="main-content">
        <div className="left-column">
          <TransactionAnalyzerForm 
            formData={formData}
            handleInputChange={handleInputChange}
            handleFormFocus={handleFormFocus}
            handleTyping={handleTyping}
            handlePaste={handlePaste}
            handleMouseMove={handleMouseMove}
            handleSubmit={handleSubmit}
            behavioralData={behavioralData}
          />
          <RiskTrendChart chartData={chartData} />
        </div>

        <div className="right-column">
          <LiveTransactionFeed transactions={liveTransactions} />
        </div>
      </div>

      {/* Result Modal */}
      {showResult && analysisResult && (
        <div className="modal-overlay">
          <div className="modal-content result-modal">
            <div className={`result-header ${analysisResult.decision?.toLowerCase()}`}>
              <h2>Transaction {analysisResult.decision}ed</h2>
              <span className="risk-badge">{Math.round(analysisResult.risk_score)}% Risk Score</span>
            </div>
            <div className="result-body">
              <p className="result-message">{analysisResult.message}</p>
              <div className="risk-factors">
                <h3>Detected Risk Factors</h3>
                {analysisResult.risk_factors.map((factor, i) => (
                  <div key={i} className={`factor-item ${factor.severity}`}>
                    <span className="factor-name">{factor.name}</span>
                    <span className="factor-desc">{factor.description}</span>
                  </div>
                ))}
              </div>
              <div className="metrics">
                <span>Latency: {latency}ms</span>
                <span>ID: {analysisResult.transaction_id}</span>
              </div>
            </div>
            <button className="close-btn" onClick={() => setShowResult(false)}>DISMISS</button>
          </div>
        </div>
      )}

      {/* Fraud Report Modal */}
      {showFraudModal && (
        <div className="modal-overlay">
          <div className="modal-content fraud-modal">
            <h2>Report UPI Fraud</h2>
            <form onSubmit={handleFraudReportSubmit}>
              <div className="form-group">
                <label>Fraudulent UPI ID</label>
                <input 
                  type="text" 
                  value={fraudReport.fraud_upi_id} 
                  onChange={(e) => setFraudReport({...fraudReport, fraud_upi_id: e.target.value})}
                  placeholder="fraud@upi"
                  required 
                />
              </div>
              <div className="form-group">
                <label>Amount Lost (₹)</label>
                <input 
                  type="number" 
                  value={fraudReport.amount} 
                  onChange={(e) => setFraudReport({...fraudReport, amount: e.target.value})}
                  placeholder="0.00"
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea 
                  value={fraudReport.description} 
                  onChange={(e) => setFraudReport({...fraudReport, description: e.target.value})}
                  placeholder="How did it happen?"
                />
              </div>
              <div className="modal-actions">
                <button type="button" onClick={() => setShowFraudModal(false)}>CANCEL</button>
                <button type="submit" className="submit-report">SUBMIT REPORT</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
