"""
Memory-optimized LightGBM model for BTCUSDT trading
Designed for 7.5GB RAM system with aggressive memory usage
"""

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
import joblib
import json
from datetime import datetime

# Feature configuration matching coordinator's snapshot
FEATURE_NAMES = [
    'close', 'volume', 'rsi', 'ema_9', 'ema_21', 
    'macd', 'macd_signal', 'macd_hist',
    'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
    'price_change_1h', 'volume_change_1h'
]

def generate_synthetic_training_data(n_samples=50000):
    """
    Generate synthetic BTCUSDT-like data for initial training.
    Using 50k samples to maximize 2.5GB training buffer.
    """
    np.random.seed(42)
    
    data = {
        'close': np.random.uniform(25000, 70000, n_samples),
        'volume': np.random.uniform(100, 10000, n_samples),
        'rsi': np.random.uniform(20, 80, n_samples),
        'ema_9': np.random.uniform(25000, 70000, n_samples),
        'ema_21': np.random.uniform(25000, 70000, n_samples),
        'macd': np.random.uniform(-500, 500, n_samples),
        'macd_signal': np.random.uniform(-500, 500, n_samples),
        'macd_hist': np.random.uniform(-200, 200, n_samples),
        'bb_upper': np.random.uniform(26000, 71000, n_samples),
        'bb_middle': np.random.uniform(25000, 70000, n_samples),
        'bb_lower': np.random.uniform(24000, 69000, n_samples),
        'bb_width': np.random.uniform(500, 3000, n_samples),
        'price_change_1h': np.random.uniform(-5, 5, n_samples),
        'volume_change_1h': np.random.uniform(-50, 50, n_samples),
    }
    
    df = pd.DataFrame(data)
    
    # Generate realistic labels
    # Buy signal: RSI < 40, positive MACD, price near lower BB
    # Sell signal: RSI > 60, negative MACD, price near upper BB
    conditions_buy = (df['rsi'] < 40) & (df['macd'] > 0) & \
                     ((df['close'] - df['bb_lower']) / df['bb_width'] < 0.3)
    conditions_sell = (df['rsi'] > 60) & (df['macd'] < 0) & \
                      ((df['bb_upper'] - df['close']) / df['bb_width'] < 0.3)
    
    df['action'] = 0  # HOLD
    df.loc[conditions_buy, 'action'] = 1  # BUY
    df.loc[conditions_sell, 'action'] = 2  # SELL
    
    return df

def train_model():
    """Train LightGBM model with memory-optimized parameters"""
    
    print("=" * 60)
    print("TRAINING LIGHTGBM MODEL FOR 3.5GB RAM SYSTEM")
    print("=" * 60)
    
    # Generate training data
    print("\n[1/5] Generating synthetic training data (50k samples)...")
    df = generate_synthetic_training_data(n_samples=50000)
    print(f"  ✓ Dataset shape: {df.shape}")
    print(f"  ✓ Action distribution:\n{df['action'].value_counts()}")
    
    # Split features and target
    X = df[FEATURE_NAMES]
    y = df['action']
    
    # Train/test split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n[2/5] Data split complete:")
    print(f"  ✓ Train: {X_train.shape[0]:,} samples")
    print(f"  ✓ Test:  {X_test.shape[0]:,} samples")
    
    # LightGBM parameters optimized for 3.5GB RAM
    params = {
        'objective': 'multiclass',
        'num_class': 3,
        'metric': 'multi_logloss',
        'boosting_type': 'gbdt',
        'num_leaves': 31,           # Moderate complexity
        'learning_rate': 0.05,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'max_depth': 7,
        'min_data_in_leaf': 20,
        'lambda_l1': 0.1,
        'lambda_l2': 0.1,
        'verbose': 1,
        'num_threads': 2,           # Leave CPU headroom
        'force_col_wise': True,     # Memory efficient
    }
    
    # Create datasets
    print("\n[3/5] Creating LightGBM datasets...")
    train_data = lgb.Dataset(X_train, label=y_train, free_raw_data=False)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data, free_raw_data=False)
    
    # Train model with aggressive iterations
    print("\n[4/5] Training model (300 iterations)...")
    print("  This will use ~2GB RAM during training...")
    
    model = lgb.train(
        params,
        train_data,
        num_boost_round=300,
        valid_sets=[train_data, test_data],
        valid_names=['train', 'test'],
        callbacks=[
            lgb.early_stopping(stopping_rounds=20),
            lgb.log_evaluation(period=50)
        ]
    )
    
    # Evaluate
    print("\n[5/5] Model evaluation:")
    y_pred = model.predict(X_test)
    y_pred_class = np.argmax(y_pred, axis=1)
    accuracy = (y_pred_class == y_test).mean()
    print(f"  ✓ Test Accuracy: {accuracy:.2%}")
    
    # Feature importance
    importance = pd.DataFrame({
        'feature': FEATURE_NAMES,
        'importance': model.feature_importance(importance_type='gain')
    }).sort_values('importance', ascending=False)
    print("\n  Top 5 Important Features:")
    print(importance.head().to_string(index=False))
    
    # Save model
    model_path = 'models/lightgbm_model.txt'
    metadata_path = 'models/model_metadata.json'
    
    import os
    os.makedirs('models', exist_ok=True)
    
    print(f"\n[SAVING] Model to {model_path}...")
    model.save_model(model_path)
    
    # Save metadata
    metadata = {
        'model_type': 'lightgbm',
        'num_features': len(FEATURE_NAMES),
        'feature_names': FEATURE_NAMES,
        'num_classes': 3,
        'class_names': ['HOLD', 'BUY', 'SELL'],
        'test_accuracy': float(accuracy),
        'training_samples': len(X_train),
        'trained_at': datetime.now().isoformat(),
        'model_params': params,
        'model_size_mb': os.path.getsize(model_path) / 1024 / 1024
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  ✓ Model saved: {os.path.getsize(model_path) / 1024 / 1024:.2f} MB")
    print(f"  ✓ Metadata saved: {metadata_path}")
    
    print("\n" + "=" * 60)
    print("MODEL TRAINING COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start server: python server.py")
    print("2. Test prediction: curl http://localhost:8000/health")
    
    return model

if __name__ == '__main__':
    train_model()
