"""
LightGBM Fraud Detection Model Trainer
Trains a model on IEEE-CIS, PaySim, or synthetic data
"""

import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import lightgbm as lgb
from joblib import dump
import warnings
warnings.filterwarnings('ignore')

# Data paths
IEEE_PATH = "C:\\UPI_SECURE_PAY\\Data\\ieee_fraud.csv"
PAYSIM_PATH = "C:\\UPI_SECURE_PAY\\Data\\paysim.csv"

# Feature columns we need
FEATURE_COLUMNS = [
    'amount',
    'is_new_merchant',
    'hour_of_day',
    'is_new_device',
    'device_rooted',
    'is_on_call',
    'location_changed',
    'velocity_last_1hr',
    'user_avg_amount',
    'swipe_confidence',
    'amount_ratio'
]

def load_ieee_data():
    """Load IEEE-CIS fraud data"""
    print("Loading IEEE-CIS data...")
    df = pd.read_csv(IEEE_PATH, nrows=10000)
    
    # Map IEEE columns to our features
    data = pd.DataFrame()
    data['amount'] = df['TransactionAmt'].fillna(0)
    data['is_new_merchant'] = (df['card1'].astype(str).str.len() > 5).astype(int).head(len(df))
    data['hour_of_day'] = np.random.randint(0, 24, len(df))
    data['is_new_device'] = np.random.randint(0, 2, len(df))
    data['device_rooted'] = np.random.randint(0, 2, len(df))
    data['is_on_call'] = np.random.randint(0, 2, len(df))
    data['location_changed'] = np.random.randint(0, 2, len(df))
    data['velocity_last_1hr'] = np.random.randint(0, 11, len(df))
    data['user_avg_amount'] = df['TransactionAmt'].fillna(1000).clip(100, 5000)
    data['swipe_confidence'] = np.random.uniform(0.5, 1.0, len(df))
    data['amount_ratio'] = data['amount'] / data['user_avg_amount']
    data['label'] = df['isFraud'].fillna(0)
    
    print(f"IEEE-CIS: Loaded {len(data)} transactions")
    return data

def load_paysim_data():
    """Load PaySim data"""
    print("Loading PaySim data...")
    df = pd.read_csv(PAYSIM_PATH, nrows=10000)
    
    # Map PaySim columns to our features
    data = pd.DataFrame()
    data['amount'] = df['amount'].fillna(0)
    data['is_new_merchant'] = np.random.randint(0, 2, len(df))
    data['hour_of_day'] = np.random.randint(0, 24, len(df))
    data['is_new_device'] = np.random.randint(0, 2, len(df))
    data['device_rooted'] = np.random.randint(0, 2, len(df))
    data['is_on_call'] = np.random.randint(0, 2, len(df))
    data['location_changed'] = np.random.randint(0, 2, len(df))
    data['velocity_last_1hr'] = np.random.randint(0, 11, len(df))
    data['user_avg_amount'] = df['amount'].fillna(1000).clip(100, 5000)
    data['swipe_confidence'] = np.random.uniform(0.5, 1.0, len(df))
    data['amount_ratio'] = data['amount'] / data['user_avg_amount']
    data['label'] = df['isFraud'].fillna(0)
    
    print(f"PaySim: Loaded {len(data)} transactions")
    return data

def generate_synthetic_data(n_samples=50000):
    """Generate synthetic transaction data for training"""
    print(f"Generating {n_samples} synthetic transactions...")
    
    np.random.seed(42)
    
    # Generate features
    data = pd.DataFrame()
    
    # Amount - lognormal distribution (typical for transactions)
    data['amount'] = np.random.lognormal(mean=5, sigma=1.5, size=n_samples).clip(10, 500000)
    
    # Transaction characteristics
    data['is_new_merchant'] = np.random.randint(0, 2, n_samples)
    data['hour_of_day'] = np.random.randint(0, 24, n_samples)
    data['is_new_device'] = np.random.randint(0, 2, n_samples)
    data['device_rooted'] = np.random.choice([0, 0, 0, 1], n_samples)  # ~25% rooted
    data['is_on_call'] = np.random.choice([0, 0, 0, 1], n_samples)  # ~25% on call
    data['location_changed'] = np.random.randint(0, 2, n_samples)
    data['velocity_last_1hr'] = np.random.randint(0, 11, n_samples)
    
    # User behavior
    data['user_avg_amount'] = np.random.uniform(100, 5000, n_samples)
    data['swipe_confidence'] = np.random.uniform(0.5, 1.0, n_samples)
    data['amount_ratio'] = data['amount'] / data['user_avg_amount']
    
    # Generate fraud labels based on risk factors
    # Fraud probability increases with risk factors
    fraud_prob = np.zeros(n_samples)
    
    # High amount ratio = higher fraud risk
    fraud_prob += np.where(data['amount_ratio'] > 3, 0.15, 0)
    fraud_prob += np.where(data['amount_ratio'] > 5, 0.2, 0)
    
    # Device issues = higher fraud risk
    fraud_prob += np.where(data['device_rooted'] == 1, 0.2, 0)
    fraud_prob += np.where(data['is_on_call'] == 1, 0.15, 0)
    
    # New merchant = higher fraud risk
    fraud_prob += np.where(data['is_new_merchant'] == 1, 0.1, 0)
    
    # New device = higher fraud risk
    fraud_prob += np.where(data['is_new_device'] == 1, 0.1, 0)
    
    # High velocity = higher fraud risk
    fraud_prob += np.where(data['velocity_last_1hr'] > 5, 0.15, 0)
    
    # Suspicious hours = higher fraud risk
    fraud_prob += np.where((data['hour_of_day'] >= 0) & (data['hour_of_day'] <= 5), 0.1, 0)
    
    # Low confidence = higher fraud risk
    fraud_prob += np.where(data['swipe_confidence'] < 0.6, 0.15, 0)
    
    # Cap probability at 0.95
    fraud_prob = np.clip(fraud_prob, 0, 0.95)
    
    # Generate labels
    data['label'] = (np.random.random(n_samples) < fraud_prob).astype(int)
    
    print(f"Synthetic: Generated {n_samples} transactions with {data['label'].sum()} frauds ({data['label'].mean()*100:.2f}%)")
    
    return data

def load_data():
    """Load data from available sources"""
    data_frames = []
    
    # Try IEEE-CIS
    if os.path.exists(IEEE_PATH):
        try:
            df = load_ieee_data()
            data_frames.append(df)
        except Exception as e:
            print(f"Error loading IEEE data: {e}")
    
    # Try PaySim
    if os.path.exists(PAYSIM_PATH):
        try:
            df = load_paysim_data()
            data_frames.append(df)
        except Exception as e:
            print(f"Error loading PaySim data: {e}")
    
    # If no data loaded, generate synthetic
    if not data_frames:
        print("No external data found. Using synthetic data.")
        return generate_synthetic_data(50000)
    
    # Combine all data
    combined = pd.concat(data_frames, ignore_index=True)
    print(f"Combined data: {len(combined)} transactions")
    
    return combined

def train_model():
    """Train the LightGBM model"""
    print("=" * 60)
    print("UPI SECURE PAY - LightGBM Fraud Detection Model Training")
    print("=" * 60)
    
    # Load data
    data = load_data()
    
    # Prepare features and labels
    X = data[FEATURE_COLUMNS].fillna(0)
    y = data['label']
    
    print(f"\nFeature matrix shape: {X.shape}")
    print(f"Positive samples (fraud): {y.sum()} ({y.mean()*100:.2f}%)")
    print(f"Negative samples (legit): {(y==0).sum()} ({(1-y.mean())*100:.2f}%)")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\nTraining set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    
    # Create LightGBM dataset
    train_data = lgb.Dataset(X_train, label=y_train)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
    
    # LightGBM parameters
    params = {
        'objective': 'binary',
        'metric': 'binary_logloss',
        'boosting_type': 'gbdt',
        'n_estimators': 200,
        'learning_rate': 0.05,
        'max_depth': 6,
        'num_leaves': 31,
        'min_child_samples': 20,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'verbose': -1
    }
    
    print("\nTraining LightGBM model...")
    print(f"Parameters: n_estimators={params['n_estimators']}, learning_rate={params['learning_rate']}, max_depth={params['max_depth']}")
    
    # Train model
    model = lgb.train(
        params,
        train_data,
        num_boost_round=200,
        valid_sets=[train_data, test_data],
        valid_names=['train', 'test'],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(50)]
    )
    
    # Predictions
    y_pred_proba = model.predict(X_test)
    y_pred = (y_pred_proba > 0.5).astype(int)
    
    # Metrics
    print("\n" + "=" * 60)
    print("MODEL EVALUATION METRICS")
    print("=" * 60)
    
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    
    print(f"Accuracy:  {accuracy*100:.2f}%")
    print(f"Precision: {precision*100:.2f}%")
    print(f"Recall:    {recall*100:.2f}%")
    print(f"F1 Score: {f1*100:.2f}%")
    
    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"              Predicted")
    print(f"              Legit   Fraud")
    print(f"Actual Legit  {cm[0,0]:5d}  {cm[0,1]:5d}")
    print(f"       Fraud {cm[1,0]:5d}  {cm[1,1]:5d}")
    
    # Feature importance
    print("\nFeature Importance:")
    importance = pd.DataFrame({
        'feature': FEATURE_COLUMNS,
        'importance': model.feature_importance()
    }).sort_values('importance', ascending=False)
    
    for _, row in importance.iterrows():
        print(f"  {row['feature']:25s}: {row['importance']}")
    
    # Save model
    model_path = 'model.pkl'
    dump(model, model_path)
    
    # Get file size
    file_size = os.path.getsize(model_path)
    file_size_mb = file_size / (1024 * 1024)
    
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE!")
    print("=" * 60)
    print(f"Model saved to: {model_path}")
    print(f"Model file size: {file_size_mb:.2f} MB")
    print("\n✅ Ready for real data upgrade!")
    
    return model

if __name__ == "__main__":
    train_model()
