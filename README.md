# UPI Secure Pay 🛡️

## AI-Powered Real-Time Fraud Prevention System

UPI Secure Pay is an enterprise-grade fraud detection system designed specifically for India's UPI (Unified Payments Interface) payment ecosystem. Using advanced machine learning and behavioral analysis, it provides real-time protection against fraudulent transactions.

---

### Live Demo

- **Backend API**: http://127.0.0.1:8000/docs
- **Dashboard**: http://127.0.0.1:5173
- **WebSocket Live Feed**: ws://127.0.0.1:8000/ws/live-feed

---

### Model Performance

| Metric | Score |
|--------|-------|
| **F1 Score** | 91.83% |
| **Recall** | 99.88% |
| **Precision** | 84.86% |
| **Training Data** | PaySim 6.3M transactions |
| **Test Data** | IEEE-CIS 590K transactions |

---

### Tech Stack

#### Backend
- **Python** - Core programming language
- **FastAPI** - High-performance REST API
- **LightGBM** - Gradient boosting ML model
- **PostgreSQL** - Transaction database
- **Redis** - Caching and real-time data
- **NetworkX** - Graph-based fraud network analysis
- **PyTorch** - Deep learning for advanced fraud detection

#### Frontend
- **React** - UI framework
- **Tailwind CSS** - Styling
- **D3.js** - Network visualization
- **Recharts** - Charts and graphs
- **WebSocket** - Real-time updates

---

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      INPUT LAYER                            │
│  API Client (Google Pay, PhonePe, Bank)                    │
│  Behavioral Data (Swipe, Touch, Device, Call Detection)    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   FASTAPI GATEWAY                           │
│  JWT Auth • Pydantic Validation • Redis Cache               │
│  Rate Limiting • CORS                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 ML CASCADE ENGINE                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Safety Eng. │→ │ LightGBM    │→ │ Transformer + GNN   │ │
│  │ (<1ms)      │  │ (<10ms)     │  │ + LLaMA (<50ms)     │ │
│  │ Blacklist   │  │ 91.83% F1   │  │ Deep Analysis       │ │
│  │ Scam Words  │  │ 70% exit    │  │ 5-10% escalated     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              RISK SCORE ENGINE + XAI                        │
│  Composite Score = Safety(40%) + ML(30%) + Behavioral(20%) │
│  + Network(10%)                                            │
│  APPROVE / ALERT / BLOCK + Explainable Reasons             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      OUTPUT LAYER                           │
│  API Response (<200ms)  •  Live Dashboard (WebSocket)     │
└─────────────────────────────────────────────────────────────┘
```

See full UML diagrams: [docs/uml_diagram.html](docs/uml_diagram.html)

---

### Key Features

#### 1. ML Cascade Engine
A three-tier machine learning system that progressively escalates suspicious transactions:
- **Level 1**: LightGBM model processes 70% of transactions in <10ms
- **Level 2**: Transformer model analyzes temporal patterns
- **Level 3**: GNN + LLaMA for deep fraud network and NLP analysis

#### 2. AI Scam-Call Detection
Analyzes behavioral signals during transactions:
- Device sensor data (accelerometer, gyroscope)
- On-call detection during payment (common scam indicator)
- Touch/swipe pattern analysis
- Location change detection

#### 3. Fraud Network Intelligence
Graph-based detection of fraud rings:
- NetworkX integration for transaction graph analysis
- Fraudulent merchant clustering detection
- Velocity and pattern-based network scoring

#### 4. Explainable AI (XAI)
Every decision comes with explainable reasons:
- Individual risk factor breakdown
- Severity-weighted scoring
- User-friendly explanations

#### 5. One-Tap Fraud Report
Users can instantly report fraudulent transactions:
- Automatic UPI blacklist update
- Case reference generation
- Fraud network graph update

#### 6. Personal AI Guardian
Behavioral profiling for each user:
- Transaction pattern learning
- Personalized risk thresholds
- Anomaly detection against personal baseline

#### 7. Real-time Dashboard
Live monitoring and analytics:
- WebSocket-powered live transaction feed
- D3.js fraud network visualization
- Recharts analytics and trends
- Admin and User views

---

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API status |
| `/analyze-transaction` | POST | Analyze transaction for fraud |
| `/dashboard-stats` | GET | Dashboard statistics |
| `/transactions` | GET | Recent transactions |
| `/ws/live-feed` | WebSocket | Real-time transaction feed |
| `/report-fraud` | POST | Report fraudulent transaction |
| `/fraud-network` | GET | Fraud network graph data |
| `/user-profile/{user_id}` | GET | User behavioral profile |

---

### Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/upi-secure-pay.git
cd upi-secure-pay

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../dashboard
npm install
npm install axios recharts

# Start backend
cd ../backend
python -m uvicorn main:app --reload --port 8000

# Start frontend (in new terminal)
cd ../dashboard
npm run dev
```

---

### Project Structure

```
upi-secure-pay/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── schemas.py           # Pydantic models
│   ├── rules.py            # Safety rule engine
│   ├── risk_engine.py      # Risk score calculator
│   ├── database.py         # PostgreSQL integration
│   ├── lgbm_model.py       # LightGBM predictions
│   ├── train_paysim_model.py # Model training
│   ├── network_graph.py    # Fraud network analysis
│   ├── user_profile.py     # User behavioral profiling
│   └── fraud_report.py     # Fraud reporting
├── dashboard/
│   ├── src/
│   │   ├── App.jsx        # Main React component
│   │   └── ...
│   └── package.json
├── docs/
│   └── uml_diagram.html   # UML diagrams
└── README.md
```

---

### License

MIT License

---

### Author

Built with 🔒 by UPI Secure Pay Team
