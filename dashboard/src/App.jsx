import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './App.css';

const API_BASE = 'http://127.0.0.1:8000';

function App() {
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

  // Form state
  const [formData, setFormData] = useState({
    sender_upi: '',
    receiver_upi: '',
    amount: '',
    description: '',
    sender_name: '',
    receiver_name: '',
    // New fields
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
      
      // Update chart data
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
        // Reconnect after 3 seconds
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
    // Initial fetch
    const initialTimeout = setTimeout(fetchStats, 100);
    return () => {
      clearInterval(interval);
      clearTimeout(initialTimeout);
    };
  }, []);

  // Handle form change
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({ 
      ...prev, 
      [name]: type === 'checkbox' ? checked : value 
    }));
  };

  // Handle toggle switch change
  const handleToggleChange = (name) => {
    setFormData(prev => ({ ...prev, [name]: !prev[name] }));
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
      fetchStats();
    } catch (error) {
      console.error('Error analyzing transaction:', error);
      alert('Error analyzing transaction. Please check if the backend is running.');
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

  // Combine live and regular transactions for display
  const allTransactions = [...liveTransactions, ...transactions].slice(0, 20);

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <h1>UPI Secure Pay</h1>
          <span className="subtitle">Fraud Detection Dashboard</span>
        </div>
        <div className="header-right">
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
                <div className="toggle-group">
                  <label className="toggle-label">
                    <input
                      type="checkbox"
                      name="is_new_merchant"
                      checked={formData.is_new_merchant}
                      onChange={handleInputChange}
                    />
                    <span className="toggle-switch"></span>
                    New Merchant
                  </label>
                </div>
                <div className="toggle-group">
                  <label className="toggle-label">
                    <input
                      type="checkbox"
                      name="is_new_device"
                      checked={formData.is_new_device}
                      onChange={handleInputChange}
                    />
                    <span className="toggle-switch"></span>
                    New Device
                  </label>
                </div>
                <div className="toggle-group">
                  <label className="toggle-label">
                    <input
                      type="checkbox"
                      name="is_on_call"
                      checked={formData.is_on_call}
                      onChange={handleInputChange}
                    />
                    <span className="toggle-switch"></span>
                    On Call
                  </label>
                </div>
              </div>
              <div className="toggle-row">
                <div className="toggle-group">
                  <label className="toggle-label">
                    <input
                      type="checkbox"
                      name="device_rooted"
                      checked={formData.device_rooted}
                      onChange={handleInputChange}
                    />
                    <span className="toggle-switch"></span>
                    Rooted Device
                  </label>
                </div>
                <div className="toggle-group">
                  <label className="toggle-label">
                    <input
                      type="checkbox"
                      name="location_changed"
                      checked={formData.location_changed}
                      onChange={handleInputChange}
                    />
                    <span className="toggle-switch"></span>
                    Location Changed
                  </label>
                </div>
              </div>

              {/* Number Inputs */}
              <div className="form-row">
                <div className="form-group">
                  <label>Velocity Last 1hr</label>
                  <input
                    type="number"
                    name="velocity_last_1hr"
                    value={formData.velocity_last_1hr}
                    onChange={handleInputChange}
                    min="0"
                  />
                </div>
                <div className="form-group">
                  <label>User Average Amount</label>
                  <input
                    type="number"
                    name="user_avg_amount"
                    value={formData.user_avg_amount}
                    onChange={handleInputChange}
                    min="0"
                    step="0.01"
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Swipe Confidence (0.0 - 1.0)</label>
                  <input
                    type="number"
                    name="swipe_confidence"
                    value={formData.swipe_confidence}
                    onChange={handleInputChange}
                    min="0"
                    max="1"
                    step="0.1"
                  />
                </div>
              </div>

              <button type="submit" className="analyze-btn">Analyze Transaction</button>
            </form>

            {/* Analysis Result */}
            {showResult && analysisResult && (
              <div className="result-card">
                <div className="result-header">
                  <span 
                    className="result-badge" 
                    style={{ 
                      backgroundColor: analysisResult.is_blocked ? '#ff4444' : analysisResult.is_alert ? '#ffaa00' : '#00ff88' 
                    }}
                  >
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
                  <div className="result-row">
                    <span>Risk Level:</span>
                    <span style={{ color: getRiskColor(analysisResult.risk_level) }}>
                      {analysisResult.risk_level.toUpperCase()}
                    </span>
                  </div>
                  <div className="result-message">{analysisResult.message}</div>
                  {analysisResult.risk_factors && analysisResult.risk_factors.length > 0 && (
                    <div className="risk-factors">
                      <h4>Risk Factors:</h4>
                      {analysisResult.risk_factors.map((factor, idx) => (
                        <div key={idx} className="risk-factor" style={{ color: getRiskColor(factor.severity) }}>
                          • {factor.name} ({factor.severity})
                        </div>
                      ))}
                    </div>
                  )}
                  {latency > 0 && (
                    <div className="latency">
                      Latency: {latency}ms
                    </div>
                  )}
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
                <Tooltip 
                  contentStyle={{ backgroundColor: '#222', border: '1px solid #444' }}
                  labelStyle={{ color: '#fff' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="risk" 
                  stroke="#f5a623" 
                  strokeWidth={2}
                  dot={{ fill: '#f5a623' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right Column - Transaction Feed */}
        <div className="right-column">
          <div className="card feed-card">
            <h2>
              Transaction Feed
              {liveTransactions.length > 0 && (
                <span className="new-badge">{liveTransactions.length} new</span>
              )}
            </h2>
            <div className="transactions-list">
              {allTransactions.map((tx, idx) => (
                <div key={tx.transaction_id + idx} className="transaction-item">
                  <div className="tx-header">
                    <span className="tx-id">{tx.transaction_id}</span>
                    <span 
                      className="tx-status" 
                      style={{ backgroundColor: getStatusColor(tx.status) }}
                    >
                      {tx.status}
                    </span>
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
                    <span className="tx-time">
                      {new Date(tx.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
