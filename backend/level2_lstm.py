"""
Level 2 LSTM Sequence Analyzer
Analyzes user's transaction sequence to detect unusual patterns
that single-transaction analysis misses.
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import numpy as np
import random
from typing import List, Dict, Tuple, Optional
from datetime import datetime

# ==================== STEP 1: Data Preparation ====================

class TransactionSequenceDataset(Dataset):
    """PyTorch Dataset for transaction sequences"""
    def __init__(self, X, y):
        self.X = torch.FloatTensor(X)
        self.y = torch.FloatTensor(y)
    
    def __len__(self):
        return len(self.y)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


def prepare_sequence_data(transactions: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create sequences of last 10 transactions with features.
    Each sequence labeled as fraud if ANY transaction was fraud.
    
    Features per transaction:
    - amount (normalized)
    - hour_of_day (normalized 0-23)
    - is_new_merchant (0/1)
    - is_new_device (0/1)
    - velocity_last_1hr (normalized)
    - amount_ratio (current/avg)
    - swipe_confidence
    """
    SEQUENCE_LENGTH = 10
    sequences = []
    labels = []
    
    for txn in transactions:
        # Get the transaction features
        features = [
            min(txn.get('amount', 0) / 100000, 1.0),  # Normalize amount
            txn.get('hour_of_day', 12) / 23.0,  # Normalize hour
            1.0 if txn.get('is_new_merchant', False) else 0.0,
            1.0 if txn.get('is_new_device', False) else 0.0,
            min(txn.get('velocity_last_1hr', 0) / 20.0, 1.0),  # Normalize velocity
            min(txn.get('amount_ratio', 1.0), 5.0) / 5.0,  # Normalize ratio
            txn.get('swipe_confidence', 0.8)
        ]
        sequences.append(features)
        labels.append(1.0 if txn.get('is_fraud', False) else 0.0)
    
    # Pad sequences if needed
    while len(sequences) < SEQUENCE_LENGTH:
        sequences.insert(0, [0.0] * 7)
        labels.insert(0, 0.0)
    
    # Take last 10
    sequences = sequences[-SEQUENCE_LENGTH:]
    labels = labels[-SEQUENCE_LENGTH:]
    
    # Label sequence as fraud if ANY transaction was fraud
    sequence_label = 1.0 if any(labels) else 0.0
    
    return np.array([sequences]), np.array([sequence_label])


# ==================== STEP 2: Build LSTM Model ====================

class LSTMSequenceAnalyzer(nn.Module):
    """
    LSTM model for transaction sequence analysis.
    Input: sequence of 10 transactions × 7 features
    """
    def __init__(self, input_size=7, hidden_size=64, num_layers=2, dropout=0.3):
        super(LSTMSequenceAnalyzer, self).__init__()
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        # x shape: (batch, seq_len, features)
        lstm_out, (hidden, cell) = self.lstm(x)
        # Use the last hidden state
        last_hidden = hidden[-1]
        output = self.fc(last_hidden)
        return output


def build_lstm_model(input_size=7, hidden_size=64, num_layers=2, dropout=0.3):
    """Build and return the LSTM model"""
    model = LSTMSequenceAnalyzer(
        input_size=input_size,
        hidden_size=hidden_size,
        num_layers=num_layers,
        dropout=dropout
    )
    
    print(f"\n=== LSTM Model Architecture ===")
    print(f"Input: 10 transactions × {input_size} features")
    print(f"LSTM: hidden_size={hidden_size}, num_layers={num_layers}, dropout={dropout}")
    print(f"FC: Linear({hidden_size}) → ReLU → Dropout → Linear(1) → Sigmoid")
    print(f"Output: Fraud probability (0-1)")
    print("=" * 35)
    
    return model


# ==================== STEP 3: Generate Training Data ====================

def generate_sequence_training_data(num_users=50000):
    """
    Generate synthetic user transaction sequences.
    - Normal users: consistent amounts, times, merchants
    - Fraud sequences: sudden amount spike, new device, late night, new merchant
    """
    print(f"\nGenerating {num_users} user transaction sequences...")
    
    all_sequences = []
    all_labels = []
    
    for _ in range(num_users):
        num_txns = random.randint(10, 50)
        transactions = []
        
        # Determine if this is a fraud user (15% fraud rate)
        is_fraud_user = random.random() < 0.15
        
        # Generate transaction history
        for i in range(num_txns):
            if is_fraud_user:
                # Fraud: sudden anomalies
                if i >= num_txns - 3:  # Last 3 transactions are suspicious
                    txn = {
                        'amount': random.uniform(50000, 200000),  # High amount
                        'hour_of_day': random.randint(0, 5),  # Late night
                        'is_new_merchant': True,
                        'is_new_device': random.random() < 0.7,
                        'velocity_last_1hr': random.randint(5, 15),
                        'amount_ratio': random.uniform(3.0, 10.0),
                        'swipe_confidence': random.uniform(0.2, 0.5),
                        'is_fraud': True
                    }
                else:
                    # Normal transactions before fraud
                    txn = {
                        'amount': random.uniform(100, 5000),
                        'hour_of_day': random.randint(8, 20),
                        'is_new_merchant': False,
                        'is_new_device': False,
                        'velocity_last_1hr': random.randint(0, 3),
                        'amount_ratio': random.uniform(0.5, 1.5),
                        'swipe_confidence': random.uniform(0.7, 1.0),
                        'is_fraud': False
                    }
            else:
                # Normal user: consistent patterns
                txn = {
                    'amount': random.uniform(100, 8000),
                    'hour_of_day': random.choices(
                        [random.randint(8, 20), random.randint(0, 5)],
                        weights=[95, 5]
                    )[0],
                    'is_new_merchant': random.random() < 0.1,
                    'is_new_device': random.random() < 0.05,
                    'velocity_last_1hr': random.randint(0, 4),
                    'amount_ratio': random.uniform(0.5, 2.0),
                    'swipe_confidence': random.uniform(0.7, 1.0),
                    'is_fraud': False
                }
            
            transactions.append(txn)
        
        # Create sequence from last 10 transactions
        seq_data = prepare_sequence_data(transactions[-10:])
        all_sequences.append(seq_data[0][0])  # Just the sequence features
        all_labels.append(seq_data[1][0])     # Just the sequence label
    
    X = np.array(all_sequences)
    y = np.array(all_labels)
    
    print(f"Generated {len(X)} sequences")
    print(f"Fraud sequences: {int(sum(y))} ({100*sum(y)/len(y):.1f}%)")
    print(f"Normal sequences: {int(len(y) - sum(y))} ({100*(1-sum(y)/len(y)):.1f}%)")
    
    return X, y


def get_data_loader(X, y, batch_size=256):
    """Create PyTorch DataLoader"""
    dataset = TransactionSequenceDataset(X, y)
    return DataLoader(dataset, batch_size=batch_size, shuffle=True)


# ==================== STEP 4: Train the Model ====================

def train_lstm_model(model, train_loader, epochs=20, lr=0.001):
    """Train the LSTM model"""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nTraining on: {device}")
    
    model = model.to(device)
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    
    best_accuracy = 0
    best_model_state = None
    
    print(f"\n=== Training LSTM Model ===")
    print(f"Epochs: {epochs}, Batch Size: {train_loader.batch_size}")
    print(f"Optimizer: Adam, LR: {lr}, Loss: BCE")
    print("=" * 35)
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        for batch_X, batch_y in train_loader:
            batch_X = batch_X.to(device)
            batch_y = batch_y.to(device)
            
            optimizer.zero_grad()
            outputs = model(batch_X).squeeze()
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            predictions = (outputs > 0.5).float()
            correct += (predictions == batch_y).sum().item()
            total += batch_y.size(0)
        
        accuracy = correct / total
        avg_loss = total_loss / len(train_loader)
        
        # Save best model
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_model_state = model.state_dict().copy()
        
        if (epoch + 1) % 5 == 0 or epoch == 0:
            # Calculate recall for fraud class
            model.eval()
            tp = 0
            fp = 0
            fn = 0
            tn = 0
            with torch.no_grad():
                for batch_X, batch_y in train_loader:
                    batch_X = batch_X.to(device)
                    outputs = model(batch_X).squeeze()
                    predictions = (outputs > 0.5).float()
                    tp += ((predictions == 1) & (batch_y == 1)).sum().item()
                    fp += ((predictions == 1) & (batch_y == 0)).sum().item()
                    fn += ((predictions == 0) & (batch_y == 1)).sum().item()
                    tn += ((predictions == 0) & (batch_y == 0)).sum().item()
            
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            print(f"Epoch {epoch+1:2d}/{epochs} | Loss: {avg_loss:.4f} | "
                  f"Acc: {accuracy*100:.2f}% | Recall: {recall*100:.2f}% | F1: {f1*100:.2f}%")
    
    # Save best model
    if best_model_state:
        torch.save(best_model_state, 'lstm_model.pth')
        print(f"\n✓ Best model saved: lstm_model.pth (Accuracy: {best_accuracy*100:.2f}%)")
    
    return model


# ==================== STEP 5: Inference Function ====================

# Global model and device
lstm_model = None
lstm_device = None
lstm_loaded = False


def load_lstm_model():
    """Load the trained LSTM model"""
    global lstm_model, lstm_device, lstm_loaded
    
    if lstm_loaded:
        return
    
    lstm_device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    lstm_model = build_lstm_model()
    
    try:
        lstm_model.load_state_dict(torch.load('lstm_model.pth', map_location=lstm_device))
        lstm_model.eval()
        print(f"\n✓ LSTM model loaded successfully")
    except FileNotFoundError:
        print("\n⚠ LSTM model not found. Training a new model...")
        train_model()
    
    lstm_loaded = True


def predict_sequence_risk(user_transactions: List[Dict], current_transaction: Dict = None) -> Tuple[float, Optional[str]]:
    """
    Predict fraud probability based on user's transaction sequence.
    
    Args:
        user_transactions: List of user's recent transactions (last 10)
        current_transaction: Current transaction to include in sequence
    
    Returns:
        Tuple of (fraud_probability, anomaly_reason)
        - fraud_probability: 0-1 float
        - anomaly_reason: str if score > 0.5, else None
    """
    load_lstm_model()
    
    # If current transaction provided, add it to sequence
    if current_transaction:
        user_transactions = user_transactions + [current_transaction]
    
    # If insufficient data
    if len(user_transactions) < 3:
        return 0.3, None
    
    # Prepare sequence
    if len(user_transactions) < 10:
        # Pad with zeros
        padded = user_transactions.copy()
        for _ in range(10 - len(user_transactions)):
            padded.insert(0, {
                'amount': 0,
                'hour_of_day': 12,
                'is_new_merchant': False,
                'is_new_device': False,
                'velocity_last_1hr': 0,
                'amount_ratio': 1.0,
                'swipe_confidence': 0.8
            })
        user_transactions = padded
    
    # Take last 10
    user_transactions = user_transactions[-10:]
    
    # Extract features
    sequence = []
    for txn in user_transactions:
        features = [
            min(txn.get('amount', 0) / 100000, 1.0),
            txn.get('hour_of_day', 12) / 23.0,
            1.0 if txn.get('is_new_merchant', False) else 0.0,
            1.0 if txn.get('is_new_device', False) else 0.0,
            min(txn.get('velocity_last_1hr', 0) / 20.0, 1.0),
            min(txn.get('amount_ratio', 1.0), 5.0) / 5.0,
            txn.get('swipe_confidence', 0.8)
        ]
        sequence.append(features)
    
    # Convert to tensor
    sequence_tensor = torch.FloatTensor([sequence]).to(lstm_device)
    
    # Predict
    with torch.no_grad():
        probability = lstm_model(sequence_tensor).item()
    
    # Generate explanation if high risk
    anomaly_reason = None
    if probability > 0.5:
        # Analyze patterns for explanation
        recent_3 = user_transactions[-3:]
        
        # Check for amount spike
        amounts = [t.get('amount', 0) for t in recent_3]
        if amounts and max(amounts) > 30000:
            anomaly_reason = "Sudden amount spike detected in transaction sequence"
        # Check for late night
        elif any(t.get('hour_of_day', 12) < 6 for t in recent_3):
            anomaly_reason = "Unusual late-night pattern in recent transactions"
        # Check for multiple new merchants
        elif sum(1 for t in recent_3 if t.get('is_new_merchant', False)) >= 2:
            anomaly_reason = "Multiple new merchants in recent sequence"
        # Check for new device
        elif any(t.get('is_new_device', False) for t in recent_3):
            anomaly_reason = "New device usage detected in transaction sequence"
        else:
            anomaly_reason = "Unusual transaction pattern detected in sequence"
    
    return probability, anomaly_reason


def analyze_sequence_patterns(user_transactions: List[Dict]) -> Dict:
    """
    Analyze transaction sequence patterns and return detailed analysis.
    """
    if len(user_transactions) < 3:
        return {
            'insufficient_data': True,
            'risk_score': 0.3,
            'patterns': []
        }
    
    patterns = []
    recent = user_transactions[-10:]
    
    # Check for amount changes
    amounts = [t.get('amount', 0) for t in recent if t.get('amount', 0) > 0]
    if len(amounts) >= 2:
        avg_amount = sum(amounts) / len(amounts)
        recent_amount = amounts[-1]
        if recent_amount > avg_amount * 3:
            patterns.append('amount_spike')
    
    # Check for time anomalies
    late_night = sum(1 for t in recent if t.get('hour_of_day', 12) < 6)
    if late_night >= 2:
        patterns.append('late_night_activity')
    
    # Check for new merchants
    new_merchants = sum(1 for t in recent if t.get('is_new_merchant', False))
    if new_merchants >= 3:
        patterns.append('multiple_new_merchants')
    
    # Check for device issues
    new_devices = sum(1 for t in recent if t.get('is_new_device', False))
    if new_devices >= 2:
        patterns.append('new_device_pattern')
    
    # Check for velocity
    high_velocity = sum(1 for t in recent if t.get('velocity_last_1hr', 0) > 5)
    if high_velocity >= 2:
        patterns.append('high_velocity')
    
    return {
        'insufficient_data': False,
        'risk_score': 0.5 if patterns else 0.2,
        'patterns': patterns,
        'num_transactions': len(recent)
    }


# ==================== Main Training Function ====================

def train_model():
    """Main function to train and save the LSTM model"""
    print("\n" + "="*50)
    print("LEVEL 2 LSTM SEQUENCE ANALYZER - TRAINING")
    print("="*50)
    
    # Generate training data
    X, y = generate_sequence_training_data(50000)
    
    # Create data loader
    train_loader = get_data_loader(X, y, batch_size=256)
    
    # Build model
    model = build_lstm_model()
    
    # Train
    train_lstm_model(model, train_loader, epochs=20, lr=0.001)
    
    print("\n✓ Training complete!")
    print(f"Model saved as: {os.getenv('LSTM_MODEL_PATH', 'lstm_model.pth')}")


if __name__ == "__main__":
    train_model()
