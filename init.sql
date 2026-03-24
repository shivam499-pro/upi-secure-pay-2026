CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user'
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(255) UNIQUE NOT NULL,
    amount FLOAT NOT NULL,
    merchant_name VARCHAR(255),
    merchant_upi_id VARCHAR(255),
    decision VARCHAR(20) DEFAULT 'PENDING',
    fraud_score FLOAT,
    risk_level VARCHAR(10),
    risk_score FLOAT,
    reasons TEXT,
    level_reached VARCHAR(255),
    latency_ms FLOAT,
    behavioral_deviation FLOAT,
    network_risk_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fraud_reports (
    id SERIAL PRIMARY KEY,
    case_reference VARCHAR(255) UNIQUE NOT NULL,
    fraud_upi_id VARCHAR(255) NOT NULL,
    amount_lost FLOAT,
    description TEXT,
    reported_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
