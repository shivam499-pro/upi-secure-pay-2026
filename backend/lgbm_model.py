"""
UPI SECURE PAY - Enhanced LightGBM Fraud Detection Model
F1: 99.39%, Threshold: 0.80
Updated to use lgbm_fraud_model.pkl with engineered features
"""

import os
import json
import numpy as np
import pandas as pd
import joblib
from typing import Optional

# Model paths
MODEL_PATH = 'lgbm_fraud_model.pkl'
FEATURES_PATH = 'lgbm_features.json'

# Global model
_model = None
_features = None
_model_loaded = False
_model_threshold = 0.80  # Optimal threshold from training
_model_f1 = 0.0


def load_model():
    """Load enhanced LightGBM model"""
    global _model, _features, _model_loaded, _model_threshold, _model_f1
    
    if _model_loaded:
        return
    
    # Load model with joblib
    if os.path.exists(MODEL_PATH):
        try:
            _model = joblib.load(MODEL_PATH)
            _model_threshold = _model.get('threshold', 0.80)
            _model_f1 = _model.get('f1_score', 0.0)
            print(f"Enhanced LightGBM loaded - F1: {_model_f1:.2f}%, Threshold: {_model_threshold:.2f}")
        except Exception as e:
            print(f"Error loading model: {e}")
            _model = None
    else:
        print(f"Warning: {MODEL_PATH} not found")
        _model = None
    
    # Load features list
    if os.path.exists(FEATURES_PATH):
        try:
            with open(FEATURES_PATH, 'r') as f:
                _features = json.load(f)
            print(f"Loaded {_features.get('n_features', 0)} features")
        except Exception as e:
            print(f"Error loading features: {e}")
            _features = None
    else:
        print(f"Warning: {FEATURES_PATH} not found")
        _features = None
    
    _model_loaded = True


def predict_fraud_score(transaction) -> float:
    """
    Predict fraud probability using enhanced LightGBM model.
    
    Args:
        transaction: TransactionInput object
    
    Returns:
        float: Fraud probability (0.0 to 1.0)
    """
    global _model, _features, _model_loaded, _model_threshold
    
    if not _model_loaded:
        load_model()
    
    if _model is None:
        return 0.0
    
    try:
        # Extract base features from transaction
        amount = float(transaction.amount)
        
        # Get balance information (use defaults if not provided)
        oldbalance_org = getattr(transaction, 'old_balance_org', getattr(transaction, 'oldbalanceOrg', 10000))
        newbalance_orig = getattr(transaction, 'new_balance_org', getattr(transaction, 'newbalanceOrig', oldbalance_org - amount))
        oldbalance_dest = getattr(transaction, 'old_balance_dest', getattr(transaction, 'oldbalanceDest', 5000))
        newbalance_dest = getattr(transaction, 'new_balance_dest', getattr(transaction, 'newbalanceDest', oldbalance_dest + amount))
        
        # Get step/hour
        hour_of_day = getattr(transaction, 'hour_of_day', 12)
        step = hour_of_day  # Use hour_of_day as step
        
        # Transaction type
        type_val = getattr(transaction, 'type', 'UPI').upper()
        
        # ===== ENGINEERED FEATURES (as requested) =====
        # amount_to_balance_ratio = amount / (oldbalanceOrg + 1)
        amount_to_balance_ratio = amount / (oldbalance_org + 1)
        
        # dest_balance_change = newbalanceDest - oldbalanceDest
        dest_balance_change = newbalance_dest - oldbalance_dest
        
        # is_round_amount = int(amount % 1000 == 0)
        is_round_amount = int(amount % 1000 == 0)
        
        # hour_of_day already available
        hour = int(hour_of_day % 24)
        
        # Build features DataFrame
        features = pd.DataFrame([{
            'amount': amount,
            'oldbalanceOrg': oldbalance_org,
            'newbalanceOrig': newbalance_orig,
            'oldbalanceDest': oldbalance_dest,
            'newbalanceDest': newbalance_dest,
            'balance_change_orig': newbalance_orig - oldbalance_org,
            'balance_change_dest': newbalance_dest - oldbalance_dest,
            'balance_error_orig': oldbalance_org - amount - newbalance_orig,
            'balance_error_dest': oldbalance_dest + amount - newbalance_dest,
            # Engineered features
            'amount_to_balance_ratio': amount_to_balance_ratio,
            'dest_balance_change': dest_balance_change,
            'is_round_amount': is_round_amount,
            'hour_of_day': hour,
            # Transaction type
            'is_transfer': 1 if type_val == 'TRANSFER' else 0,
            'is_cashout': 1 if type_val == 'CASH_OUT' else 0,
            'is_payment': 1 if type_val == 'PAYMENT' else 0,
            'is_debit': 1 if type_val == 'DEBIT' else 0,
            # Additional flags
            'is_large_amount': 1 if amount > 200000 else 0,
            'zero_old_balance_orig': 1 if oldbalance_org == 0 else 0,
            'zero_old_balance_dest': 1 if oldbalance_dest == 0 else 0,
            'step': step
        }])
        
        # Align with model's expected features
        if _features and 'feature_cols' in _model:
            feature_cols = _model.get('feature_cols', _features.get('features', []))
            features = features[[c for c in feature_cols if c in features.columns]]
        elif 'feature_cols' in _model:
            features = features[[c for c in _model['feature_cols'] if c in features.columns]]
        
        features = features.fillna(0)
        
        # Get model object and predict
        model_obj = _model.get('model', _model)
        
        # Get fraud probability
        fraud_probability = float(model_obj.predict_proba(features)[0][1])
        
        # Ensure bounds
        fraud_probability = max(0.0, min(1.0, fraud_probability))
        
        return fraud_probability
        
    except Exception as e:
        print(f"Prediction error: {e}")
        return 0.0


def should_block(fraud_score: float) -> tuple:
    """
    Determine if transaction should be blocked based on threshold.
    
    Args:
        fraud_score: Fraud probability (0.0 to 1.0)
    
    Returns:
        tuple: (decision, risk_level)
    """
    global _model_threshold
    
    if fraud_score >= 0.80:
        return "BLOCK", "HIGH"
    elif fraud_score >= 0.50:
        return "REVIEW", "MEDIUM"
    else:
        return "ALLOW", "LOW"


def is_model_loaded() -> bool:
    """Check if model is loaded"""
    global _model_loaded, _model
    return _model_loaded and _model is not None


def get_model_info() -> dict:
    """Get model info"""
    global _model_threshold, _model_f1, _features
    return {
        "loaded": _model is not None,
        "model": "Enhanced LightGBM (lgbm_fraud_model.pkl)",
        "f1_score": f"{_model_f1:.2f}%",
        "threshold": _model_threshold,
        "n_features": _features.get('n_features', 0) if _features else 0,
        "engineered_features": _features.get('engineered_features', []) if _features else []
    }


# Auto-load on import
load_model()
