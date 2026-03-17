"""
UPI SECURE PAY - LightGBM Fraud Detection Model Training
Training on BOTH IEEE-CIS + PaySim Datasets Combined
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
print("UPI SECURE PAY - LightGBM Training on IEEE-CIS + PaySim Combined")
print("=" * 70)

# ============================================================
# STEP 1: Load FULL IEEE-CIS Dataset
# ============================================================
print("\n" + "=" * 70)
print("STEP 1: Loading FULL IEEE-CIS Dataset")
print("=" * 70)

ieee_transaction_path = "C:/Users/sj998/Downloads/ieee-fraud-detection/train_transaction.csv"
ieee_identity_path = "C:/Users/sj998/Downloads/ieee-fraud-detection/train_identity.csv"

print("Loading train_transaction.csv...")
ieee_trans = pd.read_csv(ieee_transaction_path)
print(f"  Loaded {len(ieee_trans):,} transactions")

print("Loading train_identity.csv...")
ieee_id = pd.read_csv(ieee_identity_path)
print(f"  Loaded {len(ieee_id):,} identity records")

print("Merging on TransactionID...")
ieee_df = ieee_trans.merge(ieee_id, on='TransactionID', how='left')
print(f"  IEEE-CIS total after merge: {len(ieee_df):,} rows")

# Feature engineering for IEEE-CIS
ieee_df['amount'] = ieee_df['TransactionAmt']
ieee_df['hour_of_day'] = (ieee_df['TransactionDT'] / 3600) % 24
ieee_df['amount_ratio'] = ieee_df['TransactionAmt'] / ieee_df['TransactionAmt'].mean()
ieee_df['user_avg_amount'] = ieee_df['TransactionAmt'].mean()
ieee_df['is_new_device'] = ieee_df['DeviceType'].isnull().astype(int)
ieee_df['is_new_merchant'] = ieee_df['P_emaildomain'].isnull().astype(int)
ieee_df['location_changed'] = ((ieee_df['addr1'] != ieee_df['addr2']) & 
                                 ieee_df['addr1'].notnull() & 
                                 ieee_df['addr2'].notnull()).astype(int)

# Normalize V1 to 0-1 range for swipe_confidence
v1_max = ieee_df['V1'].max()
ieee_df['swipe_confidence'] = ieee_df['V1'].fillna(0.5) / v1_max if v1_max != 0 else 0.5

# Fill velocity with D1
ieee_df['velocity_last_1hr'] = ieee_df['D1'].fillna(0)
ieee_df['device_rooted'] = 0
ieee_df['is_on_call'] = 0
ieee_df['label'] = ieee_df['isFraud']

ieee_features = ieee_df[['amount', 'hour_of_day', 'amount_ratio', 'user_avg_amount',
                          'is_new_device', 'is_new_merchant', 'location_changed',
                          'swipe_confidence', 'velocity_last_1hr', 
                          'device_rooted', 'is_on_call', 'label']].copy()

ieee_rows = len(ieee_features)
ieee_fraud = ieee_features['label'].sum()
print(f"IEEE-CIS: {ieee_rows:,} rows, {ieee_fraud:,} fraud ({ieee_fraud/ieee_rows*100:.2f}%)")

# ============================================================
# STEP 2: Load FULL PaySim Dataset
# ============================================================
print("\n" + "=" * 70)
print("STEP 2: Loading FULL PaySim Dataset")
print("=" * 70)

paysim_path = "C:/Users/sj998/OneDrive/Desktop/archive/paysim.csv"

print(f"Loading {paysim_path}...")
paysim_df = pd.read_csv(paysim_path)
print(f"  Loaded {len(paysim_df):,} transactions")

# Feature engineering for PaySim
paysim_df['amount'] = paysim_df['amount']
paysim_df['hour_of_day'] = paysim_df['step'] % 24
paysim_df['amount_ratio'] = paysim_df['amount'] / paysim_df['amount'].mean()
paysim_df['user_avg_amount'] = paysim_df['amount'].mean()
paysim_df['is_new_device'] = 0
paysim_df['is_new_merchant'] = 0
paysim_df['location_changed'] = 0
paysim_df['swipe_confidence'] = 0.8
paysim_df['velocity_last_1hr'] = 0
paysim_df['device_rooted'] = 0
paysim_df['is_on_call'] = 0
paysim_df['label'] = paysim_df['isFraud']

# Transaction type encoding
paysim_df['is_transfer'] = (paysim_df['type'] == 'TRANSFER').astype(int)
paysim_df['is_cashout'] = (paysim_df['type'] == 'CASH_OUT').astype(int)

paysim_features = paysim_df[['amount', 'hour_of_day', 'amount_ratio', 'user_avg_amount',
                             'is_new_device', 'is_new_merchant', 'location_changed',
                             'swipe_confidence', 'velocity_last_1hr',
                             'device_rooted', 'is_on_call', 'is_transfer', 'is_cashout', 'label']].copy()

paysim_rows = len(paysim_features)
paysim_fraud = paysim_features['label'].sum()
print(f"PaySim: {paysim_rows:,} rows, {paysim_fraud:,} fraud ({paysim_fraud/paysim_rows*100:.2f}%)")

# ============================================================
# STEP 3: Combine Both Datasets
# ============================================================
print("\n" + "=" * 70)
print("STEP 3: Combining Both Datasets")
print("=" * 70)

# Align columns - add missing columns to IEEE
ieee_features['is_transfer'] = 0
ieee_features['is_cashout'] = 0

# Ensure same column order
common_cols = ['amount', 'hour_of_day', 'amount_ratio', 'user_avg_amount',
               'is_new_device', 'is_new_merchant', 'location_changed',
               'swipe_confidence', 'velocity_last_1hr',
               'device_rooted', 'is_on_call', 'is_transfer', 'is_cashout', 'label']

ieee_features = ieee_features[common_cols]
paysim_features = paysim_features[common_cols]

# Combine
df = pd.concat([ieee_features, paysim_features], ignore_index=True)

total_transactions = len(df)
total_fraud = df['label'].sum()
fraud_rate = total_fraud / total_transactions * 100

print(f"Total transactions: {total_transactions:,}")
print(f"IEEE-CIS rows: {ieee_rows:,}")
print(f"PaySim rows: {paysim_rows:,}")
print(f"Total fraud cases: {total_fraud:,}")
print(f"Fraud rate: {fraud_rate:.2f}%")

# ============================================================
# STEP 4: Fix Class Imbalance
# ============================================================
print("\n" + "=" * 70)
print("STEP 4: Handling Class Imbalance")
print("=" * 70)

fraud_count = df['label'].sum()
legit_count = len(df) - fraud_count
scale_pos_weight = legit_count / fraud_count

print(f"Fraud cases: {fraud_count:,}")
print(f"Legitimate cases: {legit_count:,}")
print(f"Scale pos weight: {scale_pos_weight:.2f}")

# ============================================================
# STEP 5: Train LightGBM
# ============================================================
print("\n" + "=" * 70)
print("STEP 5: Training LightGBM Model")
print("=" * 70)

feature_cols = ['amount', 'hour_of_day', 'amount_ratio', 'user_avg_amount',
                'is_new_device', 'is_new_merchant', 'location_changed',
                'swipe_confidence', 'velocity_last_1hr',
                'device_rooted', 'is_on_call', 'is_transfer', 'is_cashout']

X = df[feature_cols].fillna(0)
y = df['label']

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Training set: {len(X_train):,} samples")
print(f"Test set: {len(X_test):,} samples")
print(f"Fraud in training: {y_train.sum():,}")

params = {
    'objective': 'binary',
    'metric': 'binary_logloss',
    'boosting_type': 'gbdt',
    'n_estimators': 500,
    'learning_rate': 0.05,
    'max_depth': 8,
    'num_leaves': 127,
    'scale_pos_weight': scale_pos_weight,
    'min_child_samples': 20,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'random_state': 42,
    'verbose': -1,
    'n_jobs': -1
}

print(f"\nLightGBM Parameters:")
print(f"  n_estimators: {params['n_estimators']}")
print(f"  learning_rate: {params['learning_rate']}")
print(f"  max_depth: {params['max_depth']}")
print(f"  num_leaves: {params['num_leaves']}")
print(f"  early_stopping_rounds: 50")

model = lgb.LGBMClassifier(**params)
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=True)]
)

# ============================================================
# STEP 6: Model Evaluation
# ============================================================
print("\n" + "=" * 70)
print("STEP 6: MODEL EVALUATION METRICS")
print("=" * 70)

y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred) * 100
precision = precision_score(y_test, y_pred) * 100
recall = recall_score(y_test, y_pred) * 100
f1 = f1_score(y_test, y_pred) * 100

print(f"\n{'Metric':<15} {'Value':>10}")
print(f"{'-'*25}")
print(f"{'Accuracy':<15} {accuracy:>9.2f}%")
print(f"{'Precision':<15} {precision:>9.2f}%")
print(f"{'Recall':<15} {recall:>9.2f}%")
print(f"{'F1 Score':<15} {f1:>9.2f}%")

# Confusion Matrix
cm = confusion_matrix(y_test, y_pred)
print(f"\nConfusion Matrix:")
print(f"{' '*12} Predicted")
print(f"{' '*12} Legit    Fraud")
print(f"Actual Legit   {cm[0,0]:5d}   {cm[0,1]:5d}")
print(f"       Fraud   {cm[1,0]:5d}   {cm[1,1]:5d}")

# Feature Importance
print(f"\nTop 10 Feature Importance:")
importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

for idx, (_, row) in enumerate(importance.head(10).iterrows()):
    print(f"  {idx+1}. {row['feature']:20s}: {row['importance']:5d}")

# Training time
training_time = (time.time() - start_time) / 60

# ============================================================
# STEP 7: Save Model
# ============================================================
print("\n" + "=" * 70)
print("STEP 7: Saving Model")
print("=" * 70)

model_path = 'model.pkl'
with open(model_path, 'wb') as f:
    pickle.dump({
        'model': model,
        'feature_cols': feature_cols,
        'data_source': 'IEEE-CIS + PaySim Combined',
        'ieee_rows': ieee_rows,
        'paysim_rows': paysim_rows,
        'total_rows': total_transactions,
        'fraud_rate': fraud_rate
    }, f)

file_size = os.path.getsize(model_path) / (1024 * 1024)

print(f"\n{'=' * 70}")
print(f"TRAINING COMPLETE!")
print(f"{'=' * 70}")
print(f"Model saved to: {model_path}")
print(f"Model file size: {file_size:.2f} MB")
print(f"Total training time: {training_time:.1f} minutes")
print(f"\n✅ Ready for real-time fraud detection!")
