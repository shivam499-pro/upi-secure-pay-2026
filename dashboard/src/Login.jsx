import { useState } from 'react';
import axios from 'axios';
import { saveAuth } from './auth';

const API_BASE = 'http://127.0.0.1:8000';

function Login({ onLoginSuccess }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      params.append('username', email);
      params.append('password', password);
      const res = await axios.post(`${API_BASE}/api/auth/login`, params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      saveAuth(res.data.access_token, {
        user_id: res.data.user_id,
        email: email,
        role: res.data.role
      });
      onLoginSuccess(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await axios.post(`${API_BASE}/api/auth/register`, {
        email, password, name
      });
      setMode('login');
      setError('');
      alert('Registered successfully! Please login.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0a0a0a',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'monospace'
    }}>
      <div style={{
        background: '#111',
        border: '1px solid #333',
        borderRadius: '12px',
        padding: '40px',
        width: '380px'
      }}>
        <h1 style={{ color: '#f5a623', margin: '0 0 8px', fontSize: '22px' }}>
          UPI Secure Pay
        </h1>
        <p style={{ color: '#888', margin: '0 0 28px', fontSize: '13px' }}>
          AI Fraud Detection System
        </p>

        <div style={{ display: 'flex', marginBottom: '24px', gap: '8px' }}>
          <button
            onClick={() => { setMode('login'); setError(''); }}
            style={{
              flex: 1, padding: '8px',
              background: mode === 'login' ? '#f5a623' : '#222',
              color: mode === 'login' ? '#000' : '#888',
              border: '1px solid #333', borderRadius: '6px',
              cursor: 'pointer', fontFamily: 'monospace', fontWeight: 'bold'
            }}
          >Login</button>
          <button
            onClick={() => { setMode('register'); setError(''); }}
            style={{
              flex: 1, padding: '8px',
              background: mode === 'register' ? '#f5a623' : '#222',
              color: mode === 'register' ? '#000' : '#888',
              border: '1px solid #333', borderRadius: '6px',
              cursor: 'pointer', fontFamily: 'monospace', fontWeight: 'bold'
            }}
          >Register</button>
        </div>

        {error && (
          <div style={{
            background: '#2a0000', border: '1px solid #ff4444',
            borderRadius: '6px', padding: '10px 14px',
            color: '#ff4444', fontSize: '13px', marginBottom: '16px'
          }}>{error}</div>
        )}

        <form onSubmit={mode === 'login' ? handleLogin : handleRegister}>
          {mode === 'register' && (
            <div style={{ marginBottom: '14px' }}>
              <label style={{ color: '#888', fontSize: '12px', display: 'block', marginBottom: '6px' }}>
                Full Name
              </label>
              <input
                type="text" value={name} onChange={e => setName(e.target.value)}
                placeholder="Shivam Jaiswal" required
                style={{
                  width: '100%', padding: '10px 12px', background: '#1a1a1a',
                  border: '1px solid #333', borderRadius: '6px',
                  color: '#fff', fontFamily: 'monospace', fontSize: '14px',
                  boxSizing: 'border-box'
                }}
              />
            </div>
          )}
          <div style={{ marginBottom: '14px' }}>
            <label style={{ color: '#888', fontSize: '12px', display: 'block', marginBottom: '6px' }}>
              Email
            </label>
            <input
              type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder="admin@sentinel.com" required
              style={{
                width: '100%', padding: '10px 12px', background: '#1a1a1a',
                border: '1px solid #333', borderRadius: '6px',
                color: '#fff', fontFamily: 'monospace', fontSize: '14px',
                boxSizing: 'border-box'
              }}
            />
          </div>
          <div style={{ marginBottom: '20px' }}>
            <label style={{ color: '#888', fontSize: '12px', display: 'block', marginBottom: '6px' }}>
              Password
            </label>
            <input
              type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••" required
              style={{
                width: '100%', padding: '10px 12px', background: '#1a1a1a',
                border: '1px solid #333', borderRadius: '6px',
                color: '#fff', fontFamily: 'monospace', fontSize: '14px',
                boxSizing: 'border-box'
              }}
            />
          </div>
          <button
            type="submit" disabled={loading}
            style={{
              width: '100%', padding: '12px',
              background: loading ? '#666' : '#f5a623',
              color: '#000', border: 'none', borderRadius: '6px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontFamily: 'monospace', fontWeight: 'bold', fontSize: '14px'
            }}
          >
            {loading ? 'Please wait...' : mode === 'login' ? 'LOGIN' : 'REGISTER'}
          </button>
        </form>

        <p style={{ color: '#555', fontSize: '11px', textAlign: 'center', marginTop: '20px' }}>
          Sentinel Squad — HackHustle 2.0
        </p>
      </div>
    </div>
  );
}

export default Login;
