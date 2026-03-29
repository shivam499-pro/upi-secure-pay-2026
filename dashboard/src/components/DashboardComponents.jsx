import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export const StatsBar = ({ stats }) => (
  <div className="stats-bar">
    <div className="stat-card">
      <div className="stat-value">{stats.total_transactions}</div>
      <div className="stat-label">Total Transactions</div>
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
);

export const FraudNetworkSection = ({ networkData, muleAccounts }) => {
  const getNodeColor = (type) => {
    switch (type) {
      case 'blocked': return '#ff4444'; 
      case 'alerted': return '#ffaa00';
      case 'mule': return '#ff4444';
      case 'suspicious': return '#ffaa00';
      default: return '#00ff88';
    }
  };

  return (
    <div className="network-section">
      <div className="section-header">
        <h2>Fraud Network Intelligence</h2>
      </div>
      <div className="network-content">
        <div className="network-graph">
          <svg width="100%" height={Math.max(300, (Math.ceil((networkData.nodes?.length || 0) / 8) * 80) + 50)}>
            {networkData.nodes?.map((node, i) => (
              <g key={i}>
                <circle
                  cx={50 + (i * 80) % 600}
                  cy={50 + Math.floor(i / 8) * 80}
                  r={node.type === 'blocked' ? 22 : node.type === 'mule' ? 20 : node.type === 'alerted' || node.type === 'suspicious' ? 15 : 10}
                  fill={getNodeColor(node.type)}
                  className={node.type === 'blocked' || node.type === 'mule' ? 'pulsing-node' : ''}
                >
                  <title>{node.id} - {node.type} ({node.worst_status || 'normal'})</title>
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
            <span className="legend-item"><span className="dot normal"></span> Normal/Approved</span>
            <span className="legend-item"><span className="dot suspicious"></span> Alerted</span>
            <span className="legend-item"><span className="dot mule"></span> Blocked</span>
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
  );
};

export const TransactionAnalyzerForm = ({ 
  formData, 
  handleInputChange, 
  handleFormFocus, 
  handleTyping, 
  handlePaste, 
  handleMouseMove, 
  handleSubmit,
  behavioralData
}) => (
  <div className="card analyzer-card">
    <h2>Real-Time Transaction Analyzer</h2>
    <div className="behavioral-dashboard">
      <div className="behavioral-stat">
        <span className="label">Typing Speed</span>
        <span className="value">{behavioralData.typingSpeed} ch/s</span>
      </div>
      <div className="behavioral-stat">
        <span className="label">Form Time</span>
        <span className="value">{behavioralData.formTime}s</span>
      </div>
      <div className="behavioral-stat">
        <span className="label">Confidence</span>
        <span className={`value ${behavioralData.behavioralStatus}`}>
          {behavioralData.behavioralScore}%
        </span>
      </div>
    </div>
    
    <form onSubmit={handleSubmit} className="analyzer-form" onMouseMove={handleMouseMove}>
      <div className="form-row">
        <div className="form-group">
          <label>Receiver UPI ID</label>
          <input
            type="text"
            name="receiver_upi"
            value={formData.receiver_upi}
            onChange={handleInputChange}
            onFocus={handleFormFocus}
            onKeyDown={handleTyping}
            onPaste={(e) => handlePaste('receiver_upi')}
            placeholder="merchant@upi"
            required
          />
        </div>
        <div className="form-group">
          <label>Amount (₹)</label>
          <input
            type="number"
            name="amount"
            value={formData.amount}
            onChange={handleInputChange}
            onFocus={handleFormFocus}
            onKeyDown={handleTyping}
            onPaste={(e) => handlePaste('amount')}
            placeholder="0.00"
            required
          />
        </div>
      </div>
      
      <div className="form-row">
        <div className="form-group">
          <label>Merchant Name</label>
          <input
            type="text"
            name="merchant_name"
            value={formData.merchant_name}
            onChange={handleInputChange}
            placeholder="Merchant Name"
          />
        </div>
        <div className="form-group">
          <label>Description</label>
          <input
            type="text"
            name="description"
            value={formData.description}
            onChange={handleInputChange}
            placeholder="Payment for..."
          />
        </div>
      </div>

      <div className="checkbox-grid">
        <label className="checkbox-item">
          <input type="checkbox" name="is_on_call" checked={formData.is_on_call} onChange={handleInputChange} />
          On Call Indicator
        </label>
        <label className="checkbox-item">
          <input type="checkbox" name="is_new_device" checked={formData.is_new_device} onChange={handleInputChange} />
          New Device
        </label>
        <label className="checkbox-item">
          <input type="checkbox" name="location_changed" checked={formData.location_changed} onChange={handleInputChange} />
          Location Shift
        </label>
        <label className="checkbox-item">
          <input type="checkbox" name="device_rooted" checked={formData.device_rooted} onChange={handleInputChange} />
          Rooted Device
        </label>
      </div>
      
      <button type="submit" className="analyze-button">ANALYZE TRANSACTION</button>
    </form>
  </div>
);

export const RiskTrendChart = ({ chartData }) => (
  <div className="card chart-card">
    <h2>Risk Analysis Trend</h2>
    <div style={{ width: '100%', height: 300 }}>
      <ResponsiveContainer>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#333" />
          <XAxis dataKey="name" stroke="#888" />
          <YAxis stroke="#888" domain={[0, 100]} />
          <Tooltip 
            contentStyle={{ background: '#111', border: '1px solid #444' }}
            itemStyle={{ color: '#00ff88' }}
          />
          <Line 
            type="monotone" 
            dataKey="risk" 
            stroke="#00ff88" 
            strokeWidth={3} 
            dot={{ r: 4, fill: '#00ff88' }}
            activeDot={{ r: 8 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  </div>
);

export const LiveTransactionFeed = ({ transactions }) => (
  <div className="card feed-card">
    <h2>Live Transaction Monitor</h2>
    <div className="transaction-list">
      {transactions.map((txn, index) => (
        <div key={index} className={`transaction-item ${txn.decision?.toLowerCase()}`}>
          <div className="txn-info">
            <div className="txn-main">
              <span className="txn-id">{txn.transaction_id}</span>
              <span className="txn-amount">₹{txn.amount}</span>
            </div>
            <div className="txn-secondary">
              <span className="txn-receiver">{txn.receiver_upi}</span>
              <span className="txn-time">{new Date(txn.timestamp).toLocaleTimeString()}</span>
            </div>
          </div>
          <div className="txn-risk">
            <div className="risk-score-display">{Math.round(txn.risk_score)}</div>
            <div className={`risk-badge ${txn.decision?.toLowerCase()}`}>{txn.decision}</div>
          </div>
        </div>
      ))}
    </div>
  </div>
);
