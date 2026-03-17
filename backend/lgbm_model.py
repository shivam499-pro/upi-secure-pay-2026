"""
LightGBM Fraud Detection Model Loader and Predictor
Loads model.pkl and provides prediction function
Updated for PaySim dataset
"""

import os
import numpy as np
import pandas as pd

# Model file path
MODEL_PATH = 'model.pkl'

# Global model variable
_model = None
_model_loaded = False
_feature_cols = None

def load_model():
    """Load the trained LightGBM model"""
    global _model, _model_loaded, _feature_cols
    
    if _model_loaded:
        return _model
    
    if not os.path.exists(MODEL_PATH):
        print(f"Warning: Model file '{MODEL_PATH}' not found!")
        print("Please run 'python train_model.py' first to train the model.")
        _model = None
        _model_loaded = True
        return None
    
    try:
        with open(MODEL_PATH, 'rb') as f:
            _model = pickle.load(f)
        
        # Handle both old and new model formats
        if isinstance(_model, dict):
            _feature_cols = _model.get('feature_cols', [])
            data_source = _model.get('data_source', 'Unknown')
        else:
            # Old format - use default features
            _feature_cols = [
                'type_CASH_IN', 'type_CASH_OUT', 'type_DEBIT', 'type_PAYMENT', 'type_TRANSFER',
                'amount', 'log_amount',
                'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest',
                'balance_change_orig', 'balance_change_dest',
                'balance_error_orig', 'balance_error_dest',
                'is_flagged', 'type_numeric', 'step'
            ]
            data_source = 'Unknown'
        
        print(f"LightGBM model loaded from {MODEL_PATH}")
        print(f"Data source: {data_source}")
        print(f"Features: {len(_feature_cols)} columns")
        _model_loaded = True
        return _model
    except Exception as e:
        print(f"Error loading model: {e}")
        _model = None
        _model_loaded = True
        return None

def predict_fraud_score(transaction):
    """
    Predict fraud probability for a transaction.
    
    Args:
        transaction: TransactionInput object
    
    Returns:
        float: Fraud probability between 0.0 and 1.0
    """
    global _model, _model_loaded, _feature_cols
    
    # Load model if not loaded
    if not _model_loaded:
        load_model()
    
    # If model not available, return default score
    if _model is None:
        print("Warning: Model not available, using fallback score")
        return 0.0
    
    try:
        # Extract features - map transaction to PaySim format
        amount = float(transaction.amount)
        
        # Default values for UPI-style transaction
        type_val = getattr(transaction, 'type', 'PAYMENT').upper() if hasattr(transaction, 'type') else 'PAYMENT'
        oldbalance_org = getattr(transaction, 'old_balance_org', 0) if hasattr(transaction, 'old_balance_org') else 10000
        newbalance_org = getattr(transaction, 'new_balance_org', 0) if hasattr(transaction, 'new_balance_org') else (oldbalance_org - amount)
        oldbalance_dest = getattr(transaction, 'old_balance_dest', 0) if hasattr(transaction, 'old_balance_dest') else 5000
        newbalance_dest = getattr(transaction, 'new_balance_dest', 0) if hasattr(transaction, 'new_balance_dest') else (oldbalance_dest + amount)
        
        # Encode transaction type (UPI types to PaySim equivalents)
        type_map = {
            'CASH_IN': 'CASH_IN', 'CASH_OUT': 'CASH_OUT', 
            'TRANSFER': 'TRANSFER', 'PAYMENT': 'PAYMENT', 
            'DEBIT': 'DEBIT', 'UPI': 'PAYMENT'
        }
        mapped_type = type_map.get(type_val, 'PAYMENT')
        
        # Transaction type one-hot encoding
        type_cash_in = 1 if mapped_type == 'CASH_IN' else 0
        type_cash_out = 1 if mapped_type == 'CASH_OUT' else 0
        type_debit = 1 if mapped_type == 'DEBIT' else 0
        type_payment = 1 if mapped_type == 'PAYMENT' else 0
        type_transfer = 1 if mapped_type == 'TRANSFER' else 0
        
        # Balance changes
        balance_change_orig = newbalance_org - oldbalance_org
        balance_change_dest = newbalance_dest - oldbalance_dest
        balance_error_orig = oldbalance_org - amount - newbalance_org
        balance_error_dest = oldbalance_dest + amount - newbalance_dest
        
        # Is flagged (from UPI flags if available)
        is_flagged = 1 if (getattr(transaction, 'is_high_risk', False) or getattr(transaction, 'is_flagged', False)) else 0
        
        # Step (time - use hour of day as proxy)
        hour_of_day = getattr(transaction, 'hour_of_day', 12) if hasattr(transaction, 'hour_of_day') else 12
        step = hour_of_day
        
        # Log amount
        log_amount = np.log1p(amount)
        
        # Type numeric
        type_numeric_map = {'CASH_IN': 0, 'CASH_OUT': 1, 'DEBIT': 2, 'PAYMENT': 3, 'TRANSFER': 4}
        type_numeric = type_numeric_map.get(mapped_type, 3)
        
        # Build feature vector
        features = pd.DataFrame([{
            'type_CASH_IN': type_cash_in,
            'type_CASH_OUT': type_cash_out,
            'type_DEBIT': type_debit,
            'type_PAYMENT': type_payment,
            'type_TRANSFER': type_transfer,
            'amount': amount,
            'log_amount': log_amount,
            'oldbalanceOrg': oldbalance_org,
            'newbalanceOrig': newbalance_org,
            'oldbalanceDest': oldbalance_dest,
            'newbalanceDest': newbalance_dest,
            'balance_change_orig': balance_change_orig,
            'balance_change_dest': balance_change_dest,
            'balance_error_orig': balance_error_orig,
            'balance_error_dest': balance_error_dest,
            'is_flagged': is_flagged,
            'type_numeric': type_numeric,
            'step': step
        }])
        
        # Ensure correct column order
        if _feature_cols:
            features = features[[c for c in _feature_cols if c in features.columns]]
        
        # Handle any NaN values
        features = features.fillna(0)
        
        # Get fraud probability
        if hasattr(_model, 'predict'):
            # Old format - model directly
            fraud_probability = _model.predict(features)[0]
        else:
            # New format - dict with model key
            model_obj = _model.get('model', _model)
            fraud_probability = model_obj.predict(features)[0]
        
        # Ensure within bounds
        fraud_probability = max(0.0, min(1.0, fraud_probability))
        
        return fraud_probability
        
    except Exception as e:
        print(f"Error predicting fraud score: {e}")
        import traceback
        traceback.print_exc()
        return 0.0

def is_model_loaded():
    """Check if model is loaded"""
    global _model_loaded
    return _model_loaded and _model is not None

def get_model_info():
    """Get information about the loaded model"""
    if _model is None:
        return {
            "loaded": False,
            "message": "Model not loaded. Run train_model.py first."
        }
    
    data_source = "Unknown"
    if isinstance(_model, dict):
        data_source = _model.get('data_source', 'Unknown')
    
    return {
        "loaded": True,
        "model_path": MODEL_PATH,
        "data_source": data_source,
        "features": _feature_cols or [],
        "n_features": len(_feature_cols) if _feature_cols else 0
    }

# Auto-load model on import
import pickle
load_model()
