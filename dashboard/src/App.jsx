import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import UserDashboard from './UserDashboard';
import './App.css';

const API_BASE = 'http://127.0.0.1:8000';

function App() {
  // Tab state
  const [activeTab, setActiveTab] = useState('admin');
  
  // State
  const [stats, setStats] = useState({
    total_transactions: 0,
    blocked_transactions: 0,
    alerted_transactions: 0,
    approved_transactions: 0,
    average_risk_score: 0,
    recent_transactions: []
  });
  const [transactions, setTransactions] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [liveTransactions, setLiveTransactions] = useState([]);
  const [showResult, setShowResult] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [latency, setLatency] = useState(0);
  const wsRef = useRef(null);
  
  // Network Graph State
  const [networkData, setNetworkData] = useState({ nodes: [], edges: [] });
  const [muleAccounts, setMuleAccounts] = useState([]);
  
  // Fraud Report Modal State
  const [showFraudModal, setShowFraudModal] = useState(false);
  const [fraudReport, setFraudReport] = useState({
    fraud_upi_id: '',
    amount: '',
    description: '',
    reported_by: ''
  });
  const [fraudReportResult, setFraudReportResult] = useState(null);
  
  // User Profile State
  const [userProfile, setUserProfile] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    sender_upi: '',
    receiver_upi: '',
    amount: '',
    description: '',
    sender_name: '',
    receiver_name: '',
    is_new_merchant: false,
    is_new_device: false,
    is_on_call: false,
    device_rooted: false,
    location_changed: false,
    hour_of_day: 12,
    velocity_last_1hr: 0,
    user_avg_amount: 1000,
    swipe_confidence: 0.8
  });

  // Chart data
  const [chartData, setChartData] = useState([]);

  // Fetch stats
  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE}/dashboard-stats`);
      setStats(response.data);
      setTransactions(response.data.recent_transactions || []);
      
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

  // Fetch network data
  const fetchNetworkData = async () => {
    try {
      const response = await axios.get(`${API_BASE}/fraud-network`);
      setNetworkData(response.data);
      setMuleAccounts(response.data.mule_accounts || []);
    } catch (error) {
      console.error('Error fetching network data:', error);
    }
  };

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket('ws://127.0.0.1:8000/ws/live-feed');
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'transaction') {
          const transaction = data.data;
          setLiveTransactions(prev => [transaction, ...prev].slice(0, 50));
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setWsConnected(false);
        setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Auto refresh stats every 3 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchStats();
    }, 3000);
    const initialTimeout = setTimeout(fetchStats, 100);
    return () => {
      clearInterval(interval);
      clearTimeout(initialTimeout);
    };
  }, []);

  // Auto refresh network data every 5 seconds
  useEffect(() => {
    fetchNetworkData();
    const interval = setInterval(fetchNetworkData, 5000);
    return () => clearInterval(interval);
  }, []);

  // Handle form change
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({ 
      ...prev, 
      [name]: type === 'checkbox' ? checked : value 
    }));
  };

  // Handle form submit
  const handleSubmit = async (e) => {
    e.preventDefault();
    const startTime = Date.now();
    try {
      const payload = {
        transaction_id: "TXN" + Date.now(),
        amount: parseFloat(formData.amount),
        merchant_name: formData.receiver_name || "Unknown Merchant",
        merchant_upi_id: formData.receiver_upi,
        is_new_merchant: formData.is_new_merchant,
        hour_of_day: parseInt(formData.hour_of_day),
        is_new_device: formData.is_new_device,
        device_rooted: formData.device_rooted,
        is_on_call: formData.is_on_call,
        location_changed: formData.location_changed,
        velocity_last_1hr: parseInt(formData.velocity_last_1hr),
        user_avg_amount: parseFloat(formData.user_avg_amount),
        swipe_confidence: parseFloat(formData.swipe_confidence)
      };
      
      const response = await axios.post(`${API_BASE}/analyze-transaction`, payload);
      const endTime = Date.now();
      setLatency(endTime - startTime);
      setAnalysisResult(response.data);
      setShowResult(true);
      
      // Fetch user profile
      try {
        const profileResponse = await axios.get(`${API_BASE}/user-profile/user@upi`);
        setUserProfile(profileResponse.data);
      } catch (err) {
        console.log('User profile not available');
      }
      
      fetchStats();
      fetchNetworkData();
    } catch (error) {
      console.error('Error analyzing transaction:', error);
      alert('Error analyzing transaction. Please check if the backend is running.');
    }
  };

  // Handle fraud report submit
  const handleFraudReportSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        transaction_id: "RPT" + Date.now(),
        fraud_upi_id: fraudReport.fraud_upi_id,
        amount: parseFloat(fraudReport.amount) || 0,
        description: fraudReport.description,
        reported_by: fraudReport.reported_by || "user"
      };
      
      const response = await axios.post(`${API_BASE}/report-fraud`, payload);
      setFraudReportResult(response.data);
      fetchNetworkData();
    } catch (error) {
      console.error('Error submitting fraud report:', error);
      alert('Error submitting fraud report.');
    }
  };

  // Get status color
  const getStatusColor = (status) => {
    switch (status) {
      case 'blocked': return '#ff4444';
      case 'alerted': return '#ffaa00';
      case 'approved': return '#00ff88';
      default: return '#888';
    }
  };

  // Get risk level color
  const getRiskColor = (level) => {
    switch (level) {
      case 'critical': return '#ff4444';
      case 'high': return '#ff6644';
      case 'medium': return '#ffaa00';
      case 'low': return '#00ff88';
      default: return '#888';
    }
  };

  // Get node color for network
  const getNodeColor = (type) => {
    switch (type) {
      case 'mule': return '#ff4444';
      case 'suspicious': return '#ffaa00';
      default: return '#00ff88';
    }
  };

  // Get deviation color
  const getDeviationColor = (score) => {
    if (score >= 0.7) return '#ff4444';
    if (score >= 0.4) return '#ffaa00';
    return '#00ff88';
  };

  const allTransactions = [...liveTransactions, ...transactions].slice(0, 20);

  // Show user dashboard if that tab is active
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

  return (
    <div className="app">
      {/* Tab Navigation */}
      <div className="tab-navigation">
        <button className="tab-button active">📊 Admin Dashboard</button>
        <button className="tab-button" onClick={() => setActiveTab('user')}>🛡️ My Safety Dashboard</button>
      </div>
      
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <h1>UPI Secure Pay</h1>
          <span className="subtitle">Fraud Detection Dashboard</span>
        </div>
        <div className="header-right">
          <button 
            className="fraud-report-btn"
            onClick={() => setShowFraudModal(true)}
          >
            REPORT FRAUD
          </button>
          <div className={`live-indicator ${wsConnected ? 'connected' : ''}`}>
            <span className="live-dot"></span>
            <span className="live-text">LIVE</span>
          </div>
        </div>
      </header>

      {/* Stats Bar */}
      <div className="stats-bar">
        <div className="stat-card">
          <div className="stat-value">{stats.total_transactions}</div>
          <div className="stat-label">Total</div>
        </div>
        <div className="stat-card blocked">
          <div className="stat-value">{stats.blocked_transactions}</div>
          <div className="stat-label">Blocked</div>
        </div>
        <div className="stat-card alerted">
          <div className="stat-value">{stats.alerted_transactions}</div>
          <div className="stat-label">Alerted</div>
        </div>
        <div className="stat-card approved">
          <div className="stat-value">{stats.approved_transactions}</div>
          <div className="stat-label">Approved</div>
        </div>
        <div className="stat-card avg">
          <div className="stat-value">{stats.average_risk_score}</div>
          <div className="stat-label">Avg Risk Score</div>
        </div>
      </div>

      {/* Fraud Network Intelligence Section */}
      <div className="network-section">
        <div className="section-header">
          <h2>Fraud Network Intelligence</h2>
        </div>
        <div className="network-content">
          <div className="network-graph">
            <svg width="100%" height="300">
              {networkData.nodes?.map((node, i) => (
                <g key={i}>
                  <circle
                    cx={50 + (i * 80) % 600}
                    cy={50 + Math.floor(i / 8) * 80}
                    r={node.type === 'mule' ? 20 : node.type === 'suspicious' ? 15 : 10}
                    fill={getNodeColor(node.type)}
                    className={node.type === 'mule' ? 'pulsing-node' : ''}
                  >
                    <title>{node.id}</title>
                  </circle>
                  <text
                    x={50 + (i * 80) % 600}
                    y={85 + Math.floor(i / 8) * 80}
                    fill="#888"
                    fontSize="10"
                    textAnchor="middle"
                  >
                    {node.id?.substring(0, 8)}
                  </text>
                </g>
              ))}
              {networkData.edges?.map((edge, i) => {
                const sourceIndex = networkData.nodes?.findIndex(n => n.id === edge.source) || 0;
                const targetIndex = networkData.nodes?.findIndex(n => n.id === edge.target) || 0;
                return (
                  <line
                    key={i}
                    x1={50 + (sourceIndex * 80) % 600}
                    y1={50 + Math.floor(sourceIndex / 8) * 80}
                    x2={50 + (targetIndex * 80) % 600}
                    y2={50 + Math.floor(targetIndex / 8) * 80}
                    stroke="#444"
                    strokeWidth="1"
                  />
                );
              })}
            </svg>
            <div className="network-legend">
              <span className="legend-item"><span className="dot normal"></span> Normal</span>
              <span className="legend-item"><span className="dot suspicious"></span> Suspicious</span>
              <span className="legend-item"><span className="dot mule"></span> Mule</span>
            </div>
          </div>
          <div className="mule-accounts-panel">
            <h3>Detected Mule Accounts</h3>
            <table className="mule-table">
              <thead>
                <tr>
                  <th>UPI ID</th>
                  <th>Connections</th>
                  <th>Amount</th>
                </tr>
              </thead>
              <tbody>
                {muleAccounts.map((mule, i) => (
                  <tr key={i}>
                    <td>{mule.upi_id}</td>
                    <td>{mule.different_senders}</td>
                    <td>₹{mule.total_amount?.toLocaleString()}</td>
                  </tr>
                ))}
                {muleAccounts.length === 0 && (
                  <tr><td colSpan="3">No mule accounts detected</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Left Column */}
        <div className="left-column">
          {/* Transaction Analyzer Form */}
          <div className="card analyzer-card">
            <h2>Transaction Analyzer</h2>
            <form onSubmit={handleSubmit} className="analyzer-form">
              <div className="form-row">
                <div className="form-group">
                  <label>Amount (INR)</label>
                  <input
                    type="number"
                    name="amount"
                    value={formData.amount}
                    onChange={handleInputChange}
                    placeholder="0.00"
                    step="0.01"
                    min="0"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Merchant UPI ID</label>
                  <input
                    type="text"
                    name="receiver_upi"
                    value={formData.receiver_upi}
                    onChange={handleInputChange}
                    placeholder="merchant@upi"
                    required
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Merchant Name</label>
                  <input
                    type="text"
                    name="receiver_name"
                    value={formData.receiver_name}
                    onChange={handleInputChange}
                    placeholder="Merchant Name"
                  />
                </div>
                <div className="form-group">
                  <label>Hour of Day (0-23)</label>
                  <input
                    type="number"
                    name="hour_of_day"
                    value={formData.hour_of_day}
                    onChange={handleInputChange}
                    min="0"
                    max="23"
                  />
                </div>
              </div>
              
              {/* Toggle Switches */}
              <div className="toggle-row">
                <label className="toggle-label">
                  <input type="checkbox" name="is_new_merchant" checked={formData.is_new_merchant} onChange={handleInputChange} />
                  <span className="toggle-switch"></span>
                  New Merchant
                </label>
                <label className="toggle-label">
                  <input type="checkbox" name="is_new_device" checked={formData.is_new_device} onChange={handleInputChange} />
                  <span className="toggle-switch"></span>
                  New Device
                </label>
                <label className="toggle-label">
                  <input type="checkbox" name="is_on_call" checked={formData.is_on_call} onChange={handleInputChange} />
                  <span className="toggle-switch"></span>
                  On Call
                </label>
              </div>
              <div className="toggle-row">
                <label className="toggle-label">
                  <input type="checkbox" name="device_rooted" checked={formData.device_rooted} onChange={handleInputChange} />
                  <span className="toggle-switch"></span>
                  Rooted Device
                </label>
                <label className="toggle-label">
                  <input type="checkbox" name="location_changed" checked={formData.location_changed} onChange={handleInputChange} />
                  <span className="toggle-switch"></span>
                  Location Changed
                </label>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Velocity Last 1hr</label>
                  <input type="number" name="velocity_last_1hr" value={formData.velocity_last_1hr} onChange={handleInputChange} min="0" />
                </div>
                <div className="form-group">
                  <label>User Average Amount</label>
                  <input type="number" name="user_avg_amount" value={formData.user_avg_amount} onChange={handleInputChange} min="0" step="0.01" />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Swipe Confidence (0.0 - 1.0)</label>
                  <input type="number" name="swipe_confidence" value={formData.swipe_confidence} onChange={handleInputChange} min="0" max="1" step="0.1" />
                </div>
              </div>

              <button type="submit" className="analyze-btn">Analyze Transaction</button>
            </form>

            {/* User Behavioral Profile */}
            {userProfile && (
              <div className="user-profile-panel">
                <h3>Your Behavior Profile</h3>
                <div className="profile-stats">
                  <div className="profile-stat">
                    <span className="profile-label">Avg Amount:</span>
                    <span className="profile-value">₹{userProfile.avg_amount?.toFixed(0)}</span>
                  </div>
                  <div className="profile-stat">
                    <span className="profile-label">Usual Hours:</span>
                    <span className="profile-value">{userProfile.usual_hours?.slice(0, 5).join(', ')}</span>
                  </div>
                  <div className="profile-stat">
                    <span className="profile-label">Transactions:</span>
                    <span className="profile-value">{userProfile.transaction_count}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Analysis Result */}
            {showResult && analysisResult && (
              <div className="result-card">
                <div className="result-header">
                  <span className="result-badge" style={{ backgroundColor: analysisResult.is_blocked ? '#ff4444' : analysisResult.is_alert ? '#ffaa00' : '#00ff88' }}>
                    {analysisResult.is_blocked ? 'BLOCK' : analysisResult.is_alert ? 'ALERT' : 'APPROVE'}
                  </span>
                  <span className="result-id">ID: {analysisResult.transaction_id}</span>
                </div>
                <div className="result-details">
                  <div className="result-row">
                    <span>Risk Score:</span>
                    <span className="risk-score" style={{ color: getRiskColor(analysisResult.risk_level) }}>
                      {Math.round(analysisResult.risk_score)}%
                    </span>
                  </div>
                  <div className="result-message">{analysisResult.message}</div>
                  {analysisResult.risk_factors?.length > 0 && (
                    <div className="risk-factors">
                      <h4>Risk Factors:</h4>
                      {analysisResult.risk_factors.map((factor, idx) => (
                        <div key={idx} className="risk-factor" style={{ color: getRiskColor(factor.severity) }}>
                          • {factor.name} ({factor.severity})
                        </div>
                      ))}
                    </div>
                  )}
                  {latency > 0 && <div className="latency">Latency: {latency}ms</div>}
                </div>
                <button className="close-result" onClick={() => setShowResult(false)}>Close</button>
              </div>
            )}
          </div>

          {/* Risk Chart */}
          <div className="card chart-card">
            <h2>Risk Score Trend</h2>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="name" stroke="#888" />
                <YAxis stroke="#888" domain={[0, 100]} />
                <Tooltip contentStyle={{ backgroundColor: '#222', border: '1px solid #444' }} labelStyle={{ color: '#fff' }} />
                <Line type="monotone" dataKey="risk" stroke="#f5a623" strokeWidth={2} dot={{ fill: '#f5a623' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right Column - Transaction Feed */}
        <div className="right-column">
          <div className="card feed-card">
            <h2>
              Transaction Feed
              {liveTransactions.length > 0 && <span className="new-badge">{liveTransactions.length} new</span>}
            </h2>
            <div className="transactions-list">
              {allTransactions.map((tx, idx) => (
                <div key={tx.transaction_id + idx} className="transaction-item">
                  <div className="tx-header">
                    <span className="tx-id">{tx.transaction_id}</span>
                    <span className="tx-status" style={{ backgroundColor: getStatusColor(tx.status) }}>{tx.status}</span>
                  </div>
                  <div className="tx-details">
                    <div className="tx-parties">
                      <span className="tx-sender">{tx.sender_upi}</span>
                      <span className="tx-arrow">→</span>
                      <span className="tx-receiver">{tx.receiver_upi}</span>
                    </div>
                    <div className="tx-amount">₹{tx.amount.toLocaleString()}</div>
                  </div>
                  <div className="tx-footer">
                    <span className="tx-risk" style={{ color: getRiskColor(tx.risk_level) }}>
                      Risk: {tx.risk_score}/100 ({tx.risk_level})
                    </span>
                    <span className="tx-time">{new Date(tx.timestamp).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Fraud Report Modal */}
      {showFraudModal && (
        <div className="modal-overlay" onClick={() => { setShowFraudModal(false); setFraudReportResult(null); }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Report Fraudulent Transaction</h2>
            {fraudReportResult ? (
              <div className="fraud-success">
                <div className="success-icon">✓</div>
                <h3>Report Filed!</h3>
                <p className="case-id">Case ID: {fraudReportResult.case_reference}</p>
                <p>Fraud UPI ID has been blacklisted automatically.</p>
                <p>Report sent to NPCI + Bank + Cybercrime portal.</p>
                <button className="close-modal-btn" onClick={() => { setShowFraudModal(false); setFraudReportResult(null); }}>Close</button>
              </div>
            ) : (
              <form onSubmit={handleFraudReportSubmit} className="fraud-form">
                <div className="form-group">
                  <label>Fraud UPI ID</label>
                  <input
                    type="text"
                    value={fraudReport.fraud_upi_id}
                    onChange={(e) => setFraudReport({...fraudReport, fraud_upi_id: e.target.value})}
                    placeholder="fraud@upi"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Amount Lost (INR)</label>
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
                    placeholder="Describe the fraud..."
                    rows="3"
                  />
                </div>
                <div className="form-group">
                  <label>Your UPI ID</label>
                  <input
                    type="text"
                    value={fraudReport.reported_by}
                    onChange={(e) => setFraudReport({...fraudReport, reported_by: e.target.value})}
                    placeholder="your@upi"
                  />
                </div>
                <button type="submit" className="submit-fraud-btn">SUBMIT REPORT</button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
