"""
LightGBM Fraud Detection Model Loader and Predictor
Loads model.pkl and provides prediction function
"""

import os
import numpy as np
import pandas as pd
from joblib import load

# Model file path
MODEL_PATH = 'model.pkl'

# Feature columns (must match training)
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

# Global model variable
_model = None
_model_loaded = False

def load_model():
    """Load the trained LightGBM model"""
    global _model, _model_loaded
    
    if _model_loaded:
        return _model
    
    if not os.path.exists(MODEL_PATH):
        print(f"Warning: Model file '{MODEL_PATH}' not found!")
        print("Please run 'python train_model.py' first to train the model.")
        _model = None
        _model_loaded = True
        return None
    
    try:
        _model = load(MODEL_PATH)
        print(f"LightGBM model loaded successfully from {MODEL_PATH}")
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
        transaction: TransactionInput object with these required fields:
            - amount: float
            - is_new_merchant: bool
            - hour_of_day: int (0-23)
            - is_new_device: bool
            - device_rooted: bool
            - is_on_call: bool
            - location_changed: bool
            - velocity_last_1hr: int
            - user_avg_amount: float
            - swipe_confidence: float (0.0-1.0)
    
    Returns:
        float: Fraud probability between 0.0 and 1.0
    """
    global _model, _model_loaded
    
    # Load model if not loaded
    if not _model_loaded:
        load_model()
    
    # If model not available, return default score
    if _model is None:
        print("Warning: Model not available, using fallback score")
        return 0.0
    
    try:
        # Extract features from transaction
        features = pd.DataFrame([{
            'amount': float(transaction.amount),
            'is_new_merchant': int(transaction.is_new_merchant) if hasattr(transaction, 'is_new_merchant') else 0,
            'hour_of_day': int(transaction.hour_of_day) if hasattr(transaction, 'hour_of_day') else 12,
            'is_new_device': int(transaction.is_new_device) if hasattr(transaction, 'is_new_device') else 0,
            'device_rooted': int(transaction.device_rooted) if hasattr(transaction, 'device_rooted') else 0,
            'is_on_call': int(transaction.is_on_call) if hasattr(transaction, 'is_on_call') else 0,
            'location_changed': int(transaction.location_changed) if hasattr(transaction, 'location_changed') else 0,
            'velocity_last_1hr': int(transaction.velocity_last_1hr) if hasattr(transaction, 'velocity_last_1hr') else 0,
            'user_avg_amount': float(transaction.user_avg_amount) if hasattr(transaction, 'user_avg_amount') else 1000,
            'swipe_confidence': float(transaction.swipe_confidence) if hasattr(transaction, 'swipe_confidence') else 0.8,
            'amount_ratio': float(transaction.amount) / float(transaction.user_avg_amount) if hasattr(transaction, 'user_avg_amount') and transaction.user_avg_amount > 0 else 1.0
        }])
        
        # Ensure correct column order
        features = features[FEATURE_COLUMNS]
        
        # Handle any NaN values
        features = features.fillna(0)
        
        # Get fraud probability
        fraud_probability = _model.predict(features)[0]
        
        # Ensure within bounds
        fraud_probability = max(0.0, min(1.0, fraud_probability))
        
        return fraud_probability
        
    except Exception as e:
        print(f"Error predicting fraud score: {e}")
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
    
    return {
        "loaded": True,
        "model_path": MODEL_PATH,
        "features": FEATURE_COLUMNS,
        "n_features": len(FEATURE_COLUMNS)
    }

# Auto-load model on import
load_model()
