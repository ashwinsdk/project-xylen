"""
Memory-optimized LightGBM model for BTCUSDT trading
Designed for Mac M1 with 8GB RAM
Uses Apple Silicon optimizations and efficient memory management
"""

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
import json
from datetime import datetime
import os
import psutil

# Feature configuration matching coordinator's snapshot
FEATURE_NAMES = [
    'close', 'volume', 'rsi', 'ema_9', 'ema_21', 
    'macd', 'macd_signal', 'macd_hist',
    'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
    'price_change_1h', 'volume_change_1h'
]

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024

def generate_synthetic_training_data(n_samples=100000):
    """
    Generate synthetic BTCUSDT-like data for initial training.
    Mac M1 8GB can handle 100k samples comfortably (~4GB peak usage)
    """
    np.random.seed(42)
    
    print(f"  Memory before generation: {get_memory_usage():.1f} MB")
    
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
    
    df = pd.DataFrame(data, dtype=np.float32)  # Use float32 to save memory
    
    # Generate realistic labels with more sophisticated logic
    # Buy signal: RSI < 35, positive MACD, price near lower BB
    # Sell signal: RSI > 65, negative MACD, price near upper BB
    conditions_buy = (df['rsi'] < 35) & (df['macd'] > 0) & \
                     ((df['close'] - df['bb_lower']) / df['bb_width'] < 0.25)
    conditions_sell = (df['rsi'] > 65) & (df['macd'] < 0) & \
                      ((df['bb_upper'] - df['close']) / df['bb_width'] < 0.25)
    
    df['action'] = 0  # HOLD
    df.loc[conditions_buy, 'action'] = 1  # BUY
    df.loc[conditions_sell, 'action'] = 2  # SELL
    
    print(f"  Memory after generation: {get_memory_usage():.1f} MB")
    
    return df

def train_model():
    """Train LightGBM model optimized for Mac M1 8GB"""
    
    print("=" * 70)
    print("TRAINING LIGHTGBM MODEL FOR MAC M1 (8GB RAM)")
    print("=" * 70)
    
    # Generate training data
    print("\n[1/5] Generating synthetic training data (100k samples)...")
    df = generate_synthetic_training_data(n_samples=100000)
    print(f"  ✓ Dataset shape: {df.shape}")
    print(f"  ✓ Memory type: {df.dtypes[0]}")
    print(f"  ✓ Action distribution:\n{df['action'].value_counts()}")
    
    # Split features and target
    X = df[FEATURE_NAMES]
    y = df['action']
    
    # Train/test split (85/15 for more training data)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )
    print(f"\n[2/5] Data split complete:")
    print(f"  ✓ Train: {X_train.shape[0]:,} samples")
    print(f"  ✓ Test:  {X_test.shape[0]:,} samples")
    print(f"  ✓ Memory usage: {get_memory_usage():.1f} MB")
    
    # LightGBM parameters optimized for Mac M1 8GB
    params = {
        'objective': 'multiclass',
        'num_class': 3,
        'metric': 'multi_logloss',
        'boosting_type': 'gbdt',
        'num_leaves': 63,           # Increased for 8GB
        'learning_rate': 0.05,
        'feature_fraction': 0.85,   # Slightly higher
        'bagging_fraction': 0.85,
        'bagging_freq': 5,
        'max_depth': 8,             # Deeper trees for M1
        'min_data_in_leaf': 15,     # Lower for more granularity
        'lambda_l1': 0.1,
        'lambda_l2': 0.1,
        'verbose': 1,
        'num_threads': 6,           # M1 has 4 performance + 4 efficiency cores
        'force_col_wise': True,
        'max_bin': 255,             # Good balance for M1
    }
    
    # Create datasets
    print("\n[3/5] Creating LightGBM datasets...")
    train_data = lgb.Dataset(X_train, label=y_train, free_raw_data=False)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data, free_raw_data=False)
    print(f"  ✓ Memory usage: {get_memory_usage():.1f} MB")
    
    # Train model with more iterations for M1
    print("\n[4/5] Training model (500 iterations)...")
    print("  This will use ~3-4GB RAM during training...")
    
    model = lgb.train(
        params,
        train_data,
        num_boost_round=500,        # More iterations for M1
        valid_sets=[train_data, test_data],
        valid_names=['train', 'test'],
        callbacks=[
            lgb.early_stopping(stopping_rounds=30),
            lgb.log_evaluation(period=50)
        ]
    )
    
    print(f"  ✓ Peak memory usage: {get_memory_usage():.1f} MB")
    
    # Evaluate
    print("\n[5/5] Model evaluation:")
    y_pred = model.predict(X_test)
    y_pred_class = np.argmax(y_pred, axis=1)
    accuracy = (y_pred_class == y_test).mean()
    print(f"  ✓ Test Accuracy: {accuracy:.2%}")
    
    # Per-class accuracy
    for cls in range(3):
        cls_mask = y_test == cls
        if cls_mask.sum() > 0:
            cls_acc = (y_pred_class[cls_mask] == cls).mean()
            cls_name = ['HOLD', 'BUY', 'SELL'][cls]
            print(f"  ✓ {cls_name} Accuracy: {cls_acc:.2%}")
    
    # Feature importance
    importance = pd.DataFrame({
        'feature': FEATURE_NAMES,
        'importance': model.feature_importance(importance_type='gain')
    }).sort_values('importance', ascending=False)
    print("\n  Top 5 Important Features:")
    print(importance.head().to_string(index=False))
    
    # Save model
    model_path = 'models/lightgbm_model_m1.txt'
    metadata_path = 'models/model_metadata_m1.json'
    
    os.makedirs('models', exist_ok=True)
    
    print(f"\n[SAVING] Model to {model_path}...")
    model.save_model(model_path)
    
    # Save metadata
    metadata = {
        'model_type': 'lightgbm',
        'hardware': 'Mac M1 8GB RAM',
        'num_features': len(FEATURE_NAMES),
        'feature_names': FEATURE_NAMES,
        'num_classes': 3,
        'class_names': ['HOLD', 'BUY', 'SELL'],
        'test_accuracy': float(accuracy),
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'trained_at': datetime.now().isoformat(),
        'model_params': params,
        'model_size_mb': os.path.getsize(model_path) / 1024 / 1024,
        'num_iterations': model.current_iteration(),
        'feature_importance': importance.to_dict('records')
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  ✓ Model saved: {os.path.getsize(model_path) / 1024 / 1024:.2f} MB")
    print(f"  ✓ Metadata saved: {metadata_path}")
    print(f"  ✓ Final memory usage: {get_memory_usage():.1f} MB")
    
    print("\n" + "=" * 70)
    print("MODEL TRAINING COMPLETE FOR MAC M1!")
    print("=" * 70)
    print("\nModel optimizations for M1:")
    print("  • 100k training samples (2x more than 3.5GB system)")
    print("  • 500 boosting rounds (67% more iterations)")
    print("  • Deeper trees (max_depth=8)")
    print("  • 6 threads for Apple Silicon efficiency cores")
    print("\nNext steps:")
    print("1. Copy to model server: scp models/lightgbm_model_m1.txt user@server:/opt/trading_model/models/")
    print("2. Start server: python server.py")
    print("3. Test prediction: curl http://localhost:8000/health")
    
    return model

if __name__ == '__main__':
    train_model()