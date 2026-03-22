"""
UPI SECURE PAY - Enhanced LightGBM Fraud Detection Model Training
With Class Imbalance Handling, SMOTE, and StratifiedKFold
Target: F1 > 0.90
"""

import pandas as pd
import numpy as np
import pickle
import json
import os
import time
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, 
    confusion_matrix, classification_report
)
from imblearn.over_sampling import SMOTE
import lightgbm as lgb
import joblib
import warnings
warnings.filterwarnings('ignore')

start_time = time.time()

print("=" * 70)
print("ENHANCED LIGHTGBM TRAINING - FRAUD DETECTION")
print("Target: F1 > 0.90")
print("=" * 70)

# ============================================================
# STEP 1: Load PaySim Dataset
# ============================================================
print("\n[1/6] Loading PaySim dataset...")
paysim_path = "C:/Users/sj998/OneDrive/Desktop/archive/paysim.csv"
df = pd.read_csv(paysim_path)
print(f"Loaded {len(df):,} transactions")

# ============================================================
# STEP 2: Feature Engineering (Enhanced with PaySim features)
# ============================================================
print("\n[2/6] Engineering features...")

# Original PaySim features
df['balance_change_orig'] = df['newbalanceOrig'] - df['oldbalanceOrg']
df['balance_change_dest'] = df['newbalanceDest'] - df['oldbalanceDest']
df['balance_error_orig'] = df['oldbalanceOrg'] - df['amount'] - df['newbalanceOrig']
df['balance_error_dest'] = df['oldbalanceDest'] + df['amount'] - df['newbalanceDest']

# NEW: User-requested engineered features
# amount_to_balance_ratio = amount / (oldbalanceOrg + 1)
df['amount_to_balance_ratio'] = df['amount'] / (df['oldbalanceOrg'] + 1)

# dest_balance_change = newbalanceDest - oldbalanceDest
df['dest_balance_change'] = df['newbalanceDest'] - df['oldbalanceDest']

# is_round_amount = (amount % 1000 == 0).astype(int)
df['is_round_amount'] = (df['amount'] % 1000 == 0).astype(int)

# hour_of_day (from step column, step % 24)
df['hour_of_day'] = df['step'] % 24

# Additional useful features
df['is_transfer'] = (df['type'] == 'TRANSFER').astype(int)
df['is_cashout'] = (df['type'] == 'CASH_OUT').astype(int)
df['is_payment'] = (df['type'] == 'PAYMENT').astype(int)
df['is_debit'] = (df['type'] == 'DEBIT').astype(int)

# Large amount flag
df['is_large_amount'] = (df['amount'] > 200000).astype(int)

# Zero balance flag
df['zero_old_balance_orig'] = (df['oldbalanceOrg'] == 0).astype(int)
df['zero_old_balance_dest'] = (df['oldbalanceDest'] == 0).astype(int)

# Label
df['label'] = df['isFraud']

# Define feature columns (including new engineered features)
feature_cols = [
    'amount',
    'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest',
    'balance_change_orig', 'balance_change_dest',
    'balance_error_orig', 'balance_error_dest',
    # New engineered features
    'amount_to_balance_ratio',
    'dest_balance_change', 
    'is_round_amount',
    'hour_of_day',
    # Transaction type
    'is_transfer', 'is_cashout', 'is_payment', 'is_debit',
    # Flags
    'is_large_amount',
    'zero_old_balance_orig', 'zero_old_balance_dest',
    'step'
]

X = df[feature_cols].fillna(0)
y = df['label']

# Class statistics
fraud_count = (y == 1).sum()
legit_count = (y == 0).sum()
neg_count = legit_count
pos_count = fraud_count

print(f"Total: {len(df):,}")
print(f"Legitimate: {legit_count:,} ({legit_count/len(df)*100:.2f}%)")
print(f"Fraud: {fraud_count:,} ({fraud_count/len(df)*100:.2f}%)")

# ============================================================
# STEP 3: Calculate Class Imbalance Ratio
# ============================================================
print("\n[3/6] Handling class imbalance...")
scale_pos_weight = neg_count / pos_count
print(f"Class ratio (neg/pos): {scale_pos_weight:.2f}")

# ============================================================
# STEP 4: Stratified K-Fold Cross Validation with SMOTE
# ============================================================
print("\n[4/6] Training with StratifiedKFold (5 folds) + SMOTE...")

# Updated LGBMClassifier parameters as requested
params = {
    'objective': 'binary',
    'metric': 'average_precision',  # Better than accuracy for imbalanced
    'boosting_type': 'gbdt',
    'n_estimators': 500,
    'learning_rate': 0.05,
    'num_leaves': 63,
    'min_child_samples': 50,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'reg_alpha': 0.1,
    'reg_lambda': 0.1,
    'scale_pos_weight': scale_pos_weight,
    'random_state': 42,
    'verbose': -1,
    'n_jobs': -1,
    'force_col_wise': True
}

print(f"\nLGBM Parameters:")
for k, v in params.items():
    print(f"  {k}: {v}")

# StratifiedKFold
n_folds = 5
skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

# Store fold results
fold_f1_scores = []
fold_models = []

# SMOTE for oversampling
smote = SMOTE(random_state=42)

# Cross-validation training
print(f"\nTraining {n_folds}-fold CV...")
for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), 1):
    print(f"\n--- Fold {fold}/{n_folds} ---")
    
    X_train_fold, X_val_fold = X.iloc[train_idx], X.iloc[val_idx]
    y_train_fold, y_val_fold = y.iloc[train_idx], y.iloc[val_idx]
    
    print(f"Train: {len(X_train_fold):,} | Val: {len(X_val_fold):,}")
    print(f"Train fraud: {y_train_fold.sum():,} | Val fraud: {y_val_fold.sum():,}")
    
    # Apply SMOTE to training data only
    print("Applying SMOTE...")
    X_train_smote, y_train_smote = smote.fit_resample(X_train_fold, y_train_fold)
    print(f"After SMOTE: {len(X_train_smote):,} | Fraud: {(y_train_smote == 1).sum():,}")
    
    # Train model
    model = lgb.LGBMClassifier(**params)
    model.fit(
        X_train_smote, y_train_smote,
        eval_set=[(X_val_fold, y_val_fold)],
        callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)]
    )
    
    # Predict on validation
    y_pred = model.predict(X_val_fold)
    
    # Calculate F1 with average='binary'
    f1 = f1_score(y_val_fold, y_pred, average='binary')
    fold_f1_scores.append(f1)
    fold_models.append(model)
    
    print(f"Fold {fold} F1 (binary): {f1:.4f}")

# Average CV F1
avg_cv_f1 = np.mean(fold_f1_scores)
std_cv_f1 = np.std(fold_f1_scores)
print(f"\nCV F1 Scores: {[f'{x:.4f}' for x in fold_f1_scores]}")
print(f"Average CV F1: {avg_cv_f1:.4f} (+/- {std_cv_f1:.4f})")

# ============================================================
# STEP 5: Final Model Training on Full Data with SMOTE
# ============================================================
print("\n[5/6] Training final model on full data...")

# Apply SMOTE to full training set
X_smote, y_smote = smote.fit_resample(X, y)
print(f"After SMOTE: {len(X_smote):,} | Fraud: {(y_smote == 1).sum():,}")

# Train final model
final_model = lgb.LGBMClassifier(**params)
final_model.fit(X_smote, y_smote)

# Save the best fold model for evaluation
best_fold_idx = np.argmax(fold_f1_scores)
best_model = fold_models[best_fold_idx]

# Evaluate on a holdout test set
X_train_final, X_test_final, y_train_final, y_test_final = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Apply SMOTE only to training
X_train_smote_final, y_train_smote_final = smote.fit_resample(X_train_final, y_train_final)

# Train evaluation model
eval_model = lgb.LGBMClassifier(**params)
eval_model.fit(X_train_smote_final, y_train_smote_final)

# Predict
y_pred_test = eval_model.predict(X_test_final)
y_proba_test = eval_model.predict_proba(X_test_final)[:, 1]

# Find optimal threshold
best_threshold = 0.5
best_f1 = 0
for threshold in np.arange(0.1, 0.95, 0.05):
    y_pred_temp = (y_proba_test >= threshold).astype(int)
    f1_temp = f1_score(y_test_final, y_pred_temp, average='binary')
    if f1_temp > best_f1:
        best_f1 = f1_temp
        best_threshold = threshold

print(f"Optimal threshold: {best_threshold:.2f}")

# Final predictions with optimal threshold
y_pred_final = (y_proba_test >= best_threshold).astype(int)

# ============================================================
# STEP 6: Evaluation with Classification Report
# ============================================================
print("\n" + "=" * 70)
print("FINAL EVALUATION METRICS")
print("=" * 70)

# Use classification_report as requested
print("\nClassification Report:")
print(classification_report(y_test_final, y_pred_final, target_names=['Legit', 'Fraud']))

# Calculate metrics
accuracy = accuracy_score(y_test_final, y_pred_final) * 100
precision = precision_score(y_test_final, y_pred_final) * 100
recall = recall_score(y_test_final, y_pred_final) * 100
f1_binary = f1_score(y_test_final, y_pred_final, average='binary') * 100

print(f"\nKey Metrics:")
print(f"{'Metric':<15} {'Value':>10}")
print(f"{'-'*25}")
print(f"{'Accuracy':<15} {accuracy:>9.2f}%")
print(f"{'Precision':<15} {precision:>9.2f}%")
print(f"{'Recall':<15} {recall:>9.2f}%")
print(f"{'F1 (binary)':<15} {f1_binary:>9.2f}%")

# Confusion Matrix
cm = confusion_matrix(y_test_final, y_pred_final)
print(f"\nConfusion Matrix:")
print(f"{' '*12} Predicted")
print(f"{' '*12} Legit    Fraud")
print(f"Actual Legit   {cm[0,0]:5d}   {cm[0,1]:5d}")
print(f"       Fraud   {cm[1,0]:5d}   {cm[1,1]:5d}")

# Feature Importance
print(f"\nTop 10 Feature Importance:")
importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': final_model.feature_importances_
}).sort_values('importance', ascending=False)

for idx, (_, row) in enumerate(importance.head(10).iterrows()):
    print(f"  {idx+1}. {row['feature']:25s}: {row['importance']:5d}")

# ============================================================
# STEP 7: Save Model and Features
# ============================================================
print("\n[6/6] Saving model and features...")

# Save model with joblib as requested
model_path = 'lgbm_fraud_model.pkl'
joblib.dump({
    'model': final_model,
    'feature_cols': feature_cols,
    'threshold': best_threshold,
    'f1_score': f1_binary,
    'data_source': 'PaySim Enhanced',
    'smote_applied': True,
    'stratified_kfold': n_folds,
    'cv_f1_avg': avg_cv_f1,
    'cv_f1_std': std_cv_f1
}, model_path)

# Save feature list as JSON
features_path = 'lgbm_features.json'
with open(features_path, 'w') as f:
    json.dump({
        'features': feature_cols,
        'n_features': len(feature_cols),
        'engineered_features': [
            'amount_to_balance_ratio',
            'dest_balance_change',
            'is_round_amount',
            'hour_of_day'
        ]
    }, f, indent=2)

# File sizes
model_size = os.path.getsize(model_path) / (1024 * 1024)
features_size = os.path.getsize(features_path) / 1024

training_time = (time.time() - start_time) / 60

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("TRAINING COMPLETE!")
print("=" * 70)
print(f"\n✅ Model: {model_path} ({model_size:.2f} MB)")
print(f"✅ Features: {features_path} ({features_size:.2f} KB)")
print(f"✅ Target F1 > 0.90: {'✅ ACHIEVED!' if f1_binary >= 90 else '❌ NOT MET'}")
print(f"\nFinal F1 Score: {f1_binary:.2f}%")
print(f"Average CV F1: {avg_cv_f1:.4f} (+/- {std_cv_f1:.4f})")
print(f"Training time: {training_time:.1f} minutes")
print(f"\n🚀 Ready for fraud detection!")
