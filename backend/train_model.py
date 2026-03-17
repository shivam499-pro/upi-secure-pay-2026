"""
UPI SECURE PAY - LightGBM Fraud Detection Model Training
Using PaySim Dataset (Synthetic Mobile Money Transactions)
"""

import pandas as pd
import numpy as np
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import lightgbm as lgb
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("UPI SECURE PAY - LightGBM Fraud Detection Model Training")
print("Using PaySim Dataset")
print("=" * 60)

# Load PaySim data
print("\nLoading PaySim data...")
data_path = r"C:\Users\sj998\OneDrive\Desktop\archive\PS_20174392719_1491204439457_log.csv"
df = pd.read_csv(data_path)
print(f"Total transactions: {len(df):,}")
print(f"Fraud cases: {df['isFraud'].sum():,} ({df['isFraud'].mean()*100:.2f}%)")

# Use a sample for faster training (500K transactions)
sample_size = 500000
if len(df) > sample_size:
    df = df.sample(n=sample_size, random_state=42).reset_index(drop=True)
    print(f"\nUsing sample of {sample_size:,} transactions")

# Feature Engineering for PaySim
print("\nEngineering features...")

# Encode transaction type
df['type_CASH_IN'] = (df['type'] == 'CASH_IN').astype(int)
df['type_CASH_OUT'] = (df['type'] == 'CASH_OUT').astype(int)
df['type_DEBIT'] = (df['type'] == 'DEBIT').astype(int)
df['type_PAYMENT'] = (df['type'] == 'PAYMENT').astype(int)
df['type_TRANSFER'] = (df['type'] == 'TRANSFER').astype(int)

# Balance change features
df['balance_change_orig'] = df['newbalanceOrig'] - df['oldbalanceOrg']
df['balance_change_dest'] = df['newbalanceDest'] - df['oldbalanceDest']
df['balance_error_orig'] = df['oldbalanceOrg'] - df['amount'] - df['newbalanceOrig']
df['balance_error_dest'] = df['oldbalanceDest'] + df['amount'] - df['newbalanceDest']

# Flagged fraud (system flag)
df['is_flagged'] = df['isFlaggedFraud']

# Amount features
df['log_amount'] = np.log1p(df['amount'])

# Transaction type numeric
type_map = {'CASH_IN': 0, 'CASH_OUT': 1, 'DEBIT': 2, 'PAYMENT': 3, 'TRANSFER': 4}
df['type_numeric'] = df['type'].map(type_map)

# Select features
feature_cols = [
    'type_CASH_IN', 'type_CASH_OUT', 'type_DEBIT', 'type_PAYMENT', 'type_TRANSFER',
    'amount', 'log_amount',
    'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest',
    'balance_change_orig', 'balance_change_dest',
    'balance_error_orig', 'balance_error_dest',
    'is_flagged', 'type_numeric', 'step'
]

X = df[feature_cols].copy()
y = df['isFraud'].copy()

# Handle any missing values
X = X.fillna(0)

print(f"\nFeature matrix shape: {X.shape}")
print(f"Positive samples (fraud): {y.sum()} ({y.mean()*100:.2f}%)")
print(f"Negative samples (legit): {(1-y).sum()} ({(1-y).mean()*100:.2f}%)")

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\nTraining set: {len(X_train):,} samples")
print(f"Test set: {len(X_test):,} samples")

# Train LightGBM with scale_pos_weight for imbalanced data
print("\nTraining LightGBM model...")
scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
print(f"Scale pos weight: {scale_pos_weight:.2f}")

params = {
    'objective': 'binary',
    'metric': 'binary_logloss',
    'boosting_type': 'gbdt',
    'n_estimators': 300,
    'learning_rate': 0.05,
    'max_depth': 8,
    'num_leaves': 64,
    'scale_pos_weight': scale_pos_weight,
    'random_state': 42,
    'verbose': -1
}

model = lgb.LGBMClassifier(**params)
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=True)]
)

# Predictions
y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)[:, 1]

# Metrics
print("\n" + "=" * 60)
print("MODEL EVALUATION METRICS")
print("=" * 60)

accuracy = accuracy_score(y_test, y_pred) * 100
precision = precision_score(y_test, y_pred) * 100
recall = recall_score(y_test, y_pred) * 100
f1 = f1_score(y_test, y_pred) * 100

print(f"Accuracy:  {accuracy:.2f}%")
print(f"Precision: {precision:.2f}%")
print(f"Recall:    {recall:.2f}%")
print(f"F1 Score:  {f1:.2f}%")

# Confusion Matrix
cm = confusion_matrix(y_test, y_pred)
print(f"\nConfusion Matrix:")
print(f"              Predicted")
print(f"              Legit   Fraud")
print(f"Actual Legit  {cm[0,0]:5d}  {cm[0,1]:5d}")
print(f"       Fraud  {cm[1,0]:5d}  {cm[1,1]:5d}")

# Feature Importance
print(f"\nFeature Importance:")
importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

for idx, row in importance.head(10).iterrows():
    print(f"  {row['feature']:25s}: {row['importance']}")

# Save model
model_path = 'model.pkl'
with open(model_path, 'wb') as f:
    pickle.dump({
        'model': model,
        'feature_cols': feature_cols,
        'type_map': type_map,
        'data_source': 'PaySim'
    }, f)

file_size = os.path.getsize(model_path) / (1024 * 1024)
print(f"\n{'=' * 60}")
print(f"TRAINING COMPLETE!")
print(f"{'=' * 60}")
print(f"Model saved to: {model_path}")
print(f"Model file size: {file_size:.2f} MB")
print(f"Data source: PaySim (6.3M transactions)")
print(f"\n✅ Ready for real-time fraud detection!")
