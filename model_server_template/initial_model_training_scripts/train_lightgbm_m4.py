"""
High-performance LightGBM model for BTCUSDT trading
Designed for Mac M4 with 16GB RAM
Leverages full M4 capabilities for maximum accuracy
"""

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix
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

def generate_synthetic_training_data(n_samples=250000):
    """
    Generate synthetic BTCUSDT-like data for initial training.
    Mac M4 16GB can handle 250k samples comfortably (~8GB peak usage)
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
    
    df = pd.DataFrame(data, dtype=np.float32)
    
    # Generate realistic labels with advanced conditions
    # Buy signal: RSI < 30, strong positive MACD, price in lower 20% of BB
    # Sell signal: RSI > 70, strong negative MACD, price in upper 20% of BB
    conditions_buy = (df['rsi'] < 30) & (df['macd'] > df['macd'].quantile(0.6)) & \
                     ((df['close'] - df['bb_lower']) / df['bb_width'] < 0.2)
    conditions_sell = (df['rsi'] > 70) & (df['macd'] < df['macd'].quantile(0.4)) & \
                      ((df['bb_upper'] - df['close']) / df['bb_width'] < 0.2)
    
    df['action'] = 0  # HOLD
    df.loc[conditions_buy, 'action'] = 1  # BUY
    df.loc[conditions_sell, 'action'] = 2  # SELL
    
    print(f"  Memory after generation: {get_memory_usage():.1f} MB")
    
    return df

def train_model_with_cv():
    """Train LightGBM model optimized for Mac M4 16GB with cross-validation"""
    
    print("=" * 70)
    print("TRAINING LIGHTGBM MODEL FOR MAC M4 (16GB RAM)")
    print("HIGH-PERFORMANCE CONFIGURATION")
    print("=" * 70)
    
    # Generate training data
    print("\n[1/6] Generating synthetic training data (250k samples)...")
    df = generate_synthetic_training_data(n_samples=250000)
    print(f"  ✓ Dataset shape: {df.shape}")
    print(f"  ✓ Memory type: {df.dtypes[0]}")
    print(f"  ✓ Action distribution:\n{df['action'].value_counts()}")
    print(f"  ✓ Action percentages:\n{df['action'].value_counts(normalize=True) * 100}")
    
    # Split features and target
    X = df[FEATURE_NAMES]
    y = df['action']
    
    # Train/test split (90/10 for maximum training data)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.10, random_state=42, stratify=y
    )
    print(f"\n[2/6] Data split complete:")
    print(f"  ✓ Train: {X_train.shape[0]:,} samples")
    print(f"  ✓ Test:  {X_test.shape[0]:,} samples")
    print(f"  ✓ Memory usage: {get_memory_usage():.1f} MB")
    
    # LightGBM parameters optimized for Mac M4 16GB
    params = {
        'objective': 'multiclass',
        'num_class': 3,
        'metric': 'multi_logloss',
        'boosting_type': 'gbdt',
        'num_leaves': 127,          # Maximum for M4
        'learning_rate': 0.03,      # Lower for better convergence
        'feature_fraction': 0.9,    # High feature usage
        'bagging_fraction': 0.9,
        'bagging_freq': 5,
        'max_depth': 10,            # Deep trees for M4
        'min_data_in_leaf': 10,     # Fine granularity
        'lambda_l1': 0.05,          # Light regularization
        'lambda_l2': 0.05,
        'verbose': 1,
        'num_threads': 10,          # M4 has 10 cores (4P + 6E)
        'force_col_wise': True,
        'max_bin': 511,             # Maximum bins for M4
        'min_gain_to_split': 0.001,
    }
    
    # Create datasets
    print("\n[3/6] Creating LightGBM datasets...")
    train_data = lgb.Dataset(X_train, label=y_train, free_raw_data=False)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data, free_raw_data=False)
    print(f"  ✓ Memory usage: {get_memory_usage():.1f} MB")
    
    # Cross-validation for robustness
    print("\n[4/6] Performing 5-fold cross-validation...")
    cv_results = lgb.cv(
        params,
        train_data,
        num_boost_round=1000,
        nfold=5,
        stratified=True,
        callbacks=[
            lgb.early_stopping(stopping_rounds=50),
            lgb.log_evaluation(period=100)
        ]
    )
    
    best_rounds = len(cv_results['valid multi_logloss-mean'])
    print(f"  ✓ Best iteration: {best_rounds}")
    print(f"  ✓ CV Score: {cv_results['valid multi_logloss-mean'][-1]:.4f}")
    
    # Train final model
    print(f"\n[5/6] Training final model ({best_rounds + 50} iterations)...")
    print("  This will use ~6-8GB RAM during training...")
    
    model = lgb.train(
        params,
        train_data,
        num_boost_round=best_rounds + 50,  # Slightly more than CV
        valid_sets=[train_data, test_data],
        valid_names=['train', 'test'],
        callbacks=[
            lgb.log_evaluation(period=100)
        ]
    )
    
    print(f"  ✓ Peak memory usage: {get_memory_usage():.1f} MB")
    
    # Comprehensive evaluation
    print("\n[6/6] Model evaluation:")
    y_pred = model.predict(X_test)
    y_pred_class = np.argmax(y_pred, axis=1)
    accuracy = (y_pred_class == y_test).mean()
    print(f"  ✓ Test Accuracy: {accuracy:.2%}")
    
    # Detailed classification report
    print("\n  Classification Report:")
    print(classification_report(y_test, y_pred_class, target_names=['HOLD', 'BUY', 'SELL']))
    
    # Confusion matrix
    print("\n  Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred_class)
    print(cm)
    
    # Feature importance
    importance = pd.DataFrame({
        'feature': FEATURE_NAMES,
        'importance': model.feature_importance(importance_type='gain')
    }).sort_values('importance', ascending=False)
    print("\n  Feature Importance (sorted by gain):")
    print(importance.to_string(index=False))
    
    # Save model
    model_path = 'models/lightgbm_model_m4_large.txt'
    metadata_path = 'models/model_metadata_m4_large.json'
    
    os.makedirs('models', exist_ok=True)
    
    print(f"\n[SAVING] Model to {model_path}...")
    model.save_model(model_path)
    
    # Save comprehensive metadata
    metadata = {
        'model_type': 'lightgbm',
        'hardware': 'Mac M4 16GB RAM',
        'num_features': len(FEATURE_NAMES),
        'feature_names': FEATURE_NAMES,
        'num_classes': 3,
        'class_names': ['HOLD', 'BUY', 'SELL'],
        'test_accuracy': float(accuracy),
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'cv_folds': 5,
        'cv_score': float(cv_results['valid multi_logloss-mean'][-1]),
        'best_iteration': int(best_rounds),
        'trained_at': datetime.now().isoformat(),
        'model_params': params,
        'model_size_mb': os.path.getsize(model_path) / 1024 / 1024,
        'num_iterations': model.current_iteration(),
        'feature_importance': importance.to_dict('records'),
        'confusion_matrix': cm.tolist(),
        'classification_report': classification_report(y_test, y_pred_class, 
                                                       target_names=['HOLD', 'BUY', 'SELL'],
                                                       output_dict=True)
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  ✓ Model saved: {os.path.getsize(model_path) / 1024 / 1024:.2f} MB")
    print(f"  ✓ Metadata saved: {metadata_path}")
    print(f"  ✓ Final memory usage: {get_memory_usage():.1f} MB")
    
    print("\n" + "=" * 70)
    print("MODEL TRAINING COMPLETE FOR MAC M4!")
    print("=" * 70)
    print("\nModel optimizations for M4:")
    print("  • 250k training samples (5x more than 3.5GB system)")
    print("  • 1000+ boosting rounds with early stopping")
    print("  • 5-fold cross-validation for robustness")
    print("  • Maximum tree depth (10) and leaves (127)")
    print("  • 10 threads for M4's 4P+6E core architecture")
    print("  • 511 bins for finest granularity")
    print("\nPerformance highlights:")
    print(f"  • Test accuracy: {accuracy:.2%}")
    print(f"  • CV score: {cv_results['valid multi_logloss-mean'][-1]:.4f}")
    print(f"  • Model size: {os.path.getsize(model_path) / 1024 / 1024:.2f} MB")
    print("\nNext steps:")
    print("1. Copy to model server: scp models/lightgbm_model_m4_large.txt user@server:/opt/trading_model/models/")
    print("2. Update MODEL_PATH in models.env")
    print("3. Start server: python server.py")
    print("4. Test prediction: curl http://localhost:8000/health")
    
    return model

if __name__ == '__main__':
    train_model_with_cv()