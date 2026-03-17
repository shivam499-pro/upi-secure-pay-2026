"""
UPI SECURE PAY - IEEE-CIS LightGBM Model Training
Full IEEE-CIS Dataset (~590K transactions)
Target: F1 > 85%
"""

import pandas as pd
import numpy as np
import pickle
import os
import time
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import lightgbm as lgb
import warnings
warnings.filterwarnings('ignore')

start_time = time.time()

print("=" * 70)
print("MODEL 2: IEEE-CIS LightGBM Training")
print("Target: F1 > 85%")
print("=" * 70)

# Load FULL IEEE-CIS dataset
print("\n[1/5] Loading FULL IEEE-CIS dataset...")

# Load transactions
trans_path = "C:/Users/sj998/Downloads/ieee-fraud-detection/train_transaction.csv"
id_path = "C:/Users/sj998/Downloads/ieee-fraud-detection/train_identity.csv"

print("Loading train_transaction.csv...")
ieee_trans = pd.read_csv(trans_path)
print(f"  Loaded {len(ieee_trans):,} transactions")

print("Loading train_identity.csv...")
ieee_id = pd.read_csv(id_path)
print(f"  Loaded {len(ieee_id):,} identity records")

print("Merging on TransactionID...")
df = ieee_trans.merge(ieee_id, on='TransactionID', how='left')
print(f"  Combined: {len(df):,} rows")

# Feature engineering
print("\n[2/5] Engineering features...")

df['amount'] = df['TransactionAmt']
df['hour_of_day'] = (df['TransactionDT'] / 3600) % 24
df['amount_ratio'] = df['TransactionAmt'] / df['TransactionAmt'].mean()
df['user_avg_amount'] = df['TransactionAmt'].mean()
df['is_new_device'] = df['DeviceType'].isnull().astype(int)
df['is_new_merchant'] = df['P_emaildomain'].isnull().astype(int)
df['location_changed'] = ((df['addr1'] != df['addr2']) & df['addr1'].notnull() & df['addr2'].notnull()).astype(int)

v1_max = df['V1'].max()
df['swipe_confidence'] = df['V1'].fillna(0.5) / v1_max if v1_max != 0 else 0.5
df['velocity_last_1hr'] = df['D1'].fillna(0)
df['device_rooted'] = 0
df['is_on_call'] = 0
df['label'] = df['isFraud']

# Features
feature_cols = ['amount', 'hour_of_day', 'amount_ratio', 'user_avg_amount',
                'is_new_device', 'is_new_merchant', 'location_changed',
                'swipe_confidence', 'velocity_last_1hr', 'device_rooted', 'is_on_call']

X = df[feature_cols].fillna(0)
y = df['label']

fraud_count = y.sum()
legit_count = len(y) - fraud_count
scale_pos_weight = legit_count / fraud_count

print(f"Total: {len(df):,} | Fraud: {fraud_count:,} ({fraud_count/len(df)*100:.2f}%)")
print(f"Scale pos weight: {scale_pos_weight:.2f}")

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f"\nTrain: {len(X_train):,} | Test: {len(X_test):,}")

# Train LightGBM
print("\n[3/5] Training LightGBM...")
params = {
    'objective': 'binary',
    'metric': 'binary_logloss',
    'boosting_type': 'gbdt',
    'n_estimators': 500,
    'learning_rate': 0.05,
    'max_depth': 8,
    'num_leaves': 63,
    'scale_pos_weight': scale_pos_weight,
    'min_child_samples': 20,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'random_state': 42,
    'verbose': -1,
    'n_jobs': -1,
    'force_col_wise': True
}

model = lgb.LGBMClassifier(**params)
model.fit(X_train, y_train)

# Evaluate
print("\n[4/5] Evaluating...")
y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred) * 100
precision = precision_score(y_test, y_pred) * 100
recall = recall_score(y_test, y_pred) * 100
f1 = f1_score(y_test, y_pred) * 100

print(f"\n{'='*50}")
print("IEEE-CIS MODEL METRICS")
print(f"{'='*50}")
print(f"Accuracy:  {accuracy:.2f}%")
print(f"Precision: {precision:.2f}%")
print(f"Recall:    {recall:.2f}%")
print(f"F1 Score: {f1:.2f}%")

cm = confusion_matrix(y_test, y_pred)
print(f"\nConfusion Matrix:")
print(f"              Legit    Fraud")
print(f"Actual Legit  {cm[0,0]:5d}   {cm[0,1]:5d}")
print(f"       Fraud  {cm[1,0]:5d}   {cm[1,1]:5d}")

print(f"\nTop Features:")
imp = pd.DataFrame({'f': feature_cols, 'i': model.feature_importances_}).sort_values('i', ascending=False)
for _, r in imp.head(5).iterrows():
    print(f"  {r['f']:25s}: {r['i']}")

# Save model
print("\n[5/5] Saving model...")
model_path = 'ieee_model.pkl'
with open(model_path, 'wb') as f:
    pickle.dump({'model': model, 'feature_cols': feature_cols, 'data_source': 'IEEE-CIS'}, f)

file_size = os.path.getsize(model_path) / (1024 * 1024)
training_time = (time.time() - start_time) / 60

print(f"\n{'='*50}")
print(f"IEEE-CIS MODEL COMPLETE!")
print(f"{'='*50}")
print(f"Saved: {model_path} ({file_size:.2f} MB)")
print(f"Time: {training_time:.1f} minutes")
print(f"F1 Score: {f1:.2f}%")
