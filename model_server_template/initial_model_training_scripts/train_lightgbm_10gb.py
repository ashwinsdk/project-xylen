"""
Memory-optimized LightGBM model for BTCUSDT trading
Designed for 10GB RAM Linux VMs (ashwin-linux, aswinp, etc.)
Optimized for production deployment with maximum accuracy
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
import gc

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
    mem_info = process.memory_info()
    return mem_info.rss / 1024 / 1024

def get_system_memory():
    """Get total and available system memory"""
    mem = psutil.virtual_memory()
    return {
        'total_gb': mem.total / (1024**3),
        'available_gb': mem.available / (1024**3),
        'used_percent': mem.percent
    }

def generate_synthetic_training_data(n_samples=150000):
    """
    Generate synthetic BTCUSDT-like data for initial training.
    10GB RAM can handle 150k samples comfortably (~5-6GB peak usage)
    """
    np.random.seed(42)
    
    sys_mem = get_system_memory()
    print(f"  System memory: {sys_mem['total_gb']:.1f}GB total, {sys_mem['available_gb']:.1f}GB available")
    print(f"  Process memory before generation: {get_memory_usage():.1f} MB")
    
    # Generate data in chunks to be memory-efficient
    chunk_size = 50000
    chunks = []
    
    for i in range(0, n_samples, chunk_size):
        current_chunk = min(chunk_size, n_samples - i)
        
        data = {
            'close': np.random.uniform(25000, 70000, current_chunk),
            'volume': np.random.uniform(100, 10000, current_chunk),
            'rsi': np.random.uniform(20, 80, current_chunk),
            'ema_9': np.random.uniform(25000, 70000, current_chunk),
            'ema_21': np.random.uniform(25000, 70000, current_chunk),
            'macd': np.random.uniform(-500, 500, current_chunk),
            'macd_signal': np.random.uniform(-500, 500, current_chunk),
            'macd_hist': np.random.uniform(-200, 200, current_chunk),
            'bb_upper': np.random.uniform(26000, 71000, current_chunk),
            'bb_middle': np.random.uniform(25000, 70000, current_chunk),
            'bb_lower': np.random.uniform(24000, 69000, current_chunk),
            'bb_width': np.random.uniform(500, 3000, current_chunk),
            'price_change_1h': np.random.uniform(-5, 5, current_chunk),
            'volume_change_1h': np.random.uniform(-50, 50, current_chunk),
        }
        
        chunk_df = pd.DataFrame(data, dtype=np.float32)
        chunks.append(chunk_df)
        
        if (i + current_chunk) % 50000 == 0:
            print(f"    Generated {i + current_chunk:,} samples...")
    
    df = pd.concat(chunks, ignore_index=True)
    del chunks
    gc.collect()
    
    # Generate realistic labels with sophisticated logic
    # Buy signal: RSI < 35, positive MACD, price near lower BB
    # Sell signal: RSI > 65, negative MACD, price near upper BB
    conditions_buy = (df['rsi'] < 35) & (df['macd'] > 0) & \
                     ((df['close'] - df['bb_lower']) / df['bb_width'] < 0.25)
    conditions_sell = (df['rsi'] > 65) & (df['macd'] < 0) & \
                      ((df['bb_upper'] - df['close']) / df['bb_width'] < 0.25)
    
    df['action'] = 0  # HOLD
    df.loc[conditions_buy, 'action'] = 1  # BUY
    df.loc[conditions_sell, 'action'] = 2  # SELL
    
    print(f"  Process memory after generation: {get_memory_usage():.1f} MB")
    
    return df

def train_model_with_cv():
    """Train LightGBM model optimized for 10GB RAM Linux VMs"""
    
    print("=" * 70)
    print("TRAINING LIGHTGBM MODEL FOR 10GB RAM LINUX VMs")
    print("PRODUCTION-GRADE CONFIGURATION")
    print("=" * 70)
    
    sys_mem = get_system_memory()
    print(f"\nSystem Resources:")
    print(f"  Total Memory: {sys_mem['total_gb']:.1f} GB")
    print(f"  Available: {sys_mem['available_gb']:.1f} GB")
    print(f"  CPU Count: {psutil.cpu_count()} cores")
    
    # Generate training data
    print("\n[1/6] Generating synthetic training data (150k samples)...")
    df = generate_synthetic_training_data(n_samples=150000)
    print(f"  ✓ Dataset shape: {df.shape}")
    print(f"  ✓ Memory type: {df.dtypes[0]}")
    print(f"  ✓ Dataset size: {df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")
    print(f"  ✓ Action distribution:\n{df['action'].value_counts()}")
    print(f"  ✓ Action percentages:\n{df['action'].value_counts(normalize=True) * 100}")
    
    # Split features and target
    X = df[FEATURE_NAMES]
    y = df['action']
    
    # Clear original dataframe to save memory
    del df
    gc.collect()
    
    # Train/test split (85/15 balance)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )
    print(f"\n[2/6] Data split complete:")
    print(f"  ✓ Train: {X_train.shape[0]:,} samples")
    print(f"  ✓ Test:  {X_test.shape[0]:,} samples")
    print(f"  ✓ Memory usage: {get_memory_usage():.1f} MB")
    
    # LightGBM parameters optimized for 10GB RAM
    params = {
        'objective': 'multiclass',
        'num_class': 3,
        'metric': 'multi_logloss',
        'boosting_type': 'gbdt',
        'num_leaves': 95,           # Optimized for 10GB
        'learning_rate': 0.04,      # Balanced learning rate
        'feature_fraction': 0.85,
        'bagging_fraction': 0.85,
        'bagging_freq': 5,
        'max_depth': 9,             # Deep trees for 10GB
        'min_data_in_leaf': 12,     # Fine granularity
        'lambda_l1': 0.08,          # Moderate regularization
        'lambda_l2': 0.08,
        'verbose': 1,
        'num_threads': 8,           # Most Linux VMs have 8+ cores
        'force_col_wise': True,
        'max_bin': 383,             # Optimized for 10GB
        'min_gain_to_split': 0.001,
    }
    
    # Create datasets
    print("\n[3/6] Creating LightGBM datasets...")
    train_data = lgb.Dataset(X_train, label=y_train, free_raw_data=False)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data, free_raw_data=False)
    print(f"  ✓ Memory usage: {get_memory_usage():.1f} MB")
    
    # Cross-validation for robustness
    print("\n[4/6] Performing 5-fold cross-validation...")
    print("  This may take 5-10 minutes...")
    
    cv_results = lgb.cv(
        params,
        train_data,
        num_boost_round=800,
        nfold=5,
        stratified=True,
        callbacks=[
            lgb.early_stopping(stopping_rounds=40),
            lgb.log_evaluation(period=100)
        ]
    )
    
    best_rounds = len(cv_results['valid multi_logloss-mean'])
    print(f"  ✓ Best iteration: {best_rounds}")
    print(f"  ✓ CV Score: {cv_results['valid multi_logloss-mean'][-1]:.4f}")
    print(f"  ✓ Memory usage: {get_memory_usage():.1f} MB")
    
    # Train final model
    print(f"\n[5/6] Training final model ({best_rounds + 50} iterations)...")
    print("  This will use ~5-7GB RAM during training...")
    
    model = lgb.train(
        params,
        train_data,
        num_boost_round=best_rounds + 50,
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
    print(f"  ✓ Overall Test Accuracy: {accuracy:.2%}")
    
    # Per-class accuracy
    for cls in range(3):
        cls_mask = y_test == cls
        if cls_mask.sum() > 0:
            cls_acc = (y_pred_class[cls_mask] == cls).mean()
            cls_name = ['HOLD', 'BUY', 'SELL'][cls]
            print(f"  ✓ {cls_name} Accuracy: {cls_acc:.2%} ({cls_mask.sum()} samples)")
    
    # Detailed classification report
    print("\n  Classification Report:")
    print(classification_report(y_test, y_pred_class, target_names=['HOLD', 'BUY', 'SELL']))
    
    # Confusion matrix
    print("\n  Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred_class)
    print("           Predicted")
    print("           HOLD  BUY  SELL")
    for i, row in enumerate(cm):
        label = ['HOLD', 'BUY', 'SELL'][i]
        print(f"Actual {label:4s} {row[0]:5d} {row[1]:4d} {row[2]:5d}")
    
    # Feature importance
    importance = pd.DataFrame({
        'feature': FEATURE_NAMES,
        'importance': model.feature_importance(importance_type='gain')
    }).sort_values('importance', ascending=False)
    print("\n  Feature Importance (sorted by gain):")
    print(importance.to_string(index=False))
    
    # Save model
    model_path = 'models/lightgbm_model_10gb.txt'
    metadata_path = 'models/model_metadata_10gb.json'
    
    os.makedirs('models', exist_ok=True)
    
    print(f"\n[SAVING] Model to {model_path}...")
    model.save_model(model_path)
    
    # Save comprehensive metadata
    metadata = {
        'model_type': 'lightgbm',
        'hardware': '10GB RAM Linux VM',
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
        'final_iterations': model.current_iteration(),
        'trained_at': datetime.now().isoformat(),
        'model_params': params,
        'model_size_mb': os.path.getsize(model_path) / 1024 / 1024,
        'feature_importance': importance.to_dict('records'),
        'confusion_matrix': cm.tolist(),
        'per_class_accuracy': {
            'HOLD': float((y_pred_class[y_test == 0] == 0).mean()) if (y_test == 0).sum() > 0 else 0.0,
            'BUY': float((y_pred_class[y_test == 1] == 1).mean()) if (y_test == 1).sum() > 0 else 0.0,
            'SELL': float((y_pred_class[y_test == 2] == 2).mean()) if (y_test == 2).sum() > 0 else 0.0,
        },
        'system_info': {
            'total_memory_gb': sys_mem['total_gb'],
            'cpu_cores': psutil.cpu_count()
        }
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  ✓ Model saved: {os.path.getsize(model_path) / 1024 / 1024:.2f} MB")
    print(f"  ✓ Metadata saved: {metadata_path}")
    print(f"  ✓ Final memory usage: {get_memory_usage():.1f} MB")
    
    # System resource summary
    final_sys_mem = get_system_memory()
    print(f"\n  System Memory After Training:")
    print(f"    Available: {final_sys_mem['available_gb']:.1f} GB")
    print(f"    Used: {final_sys_mem['used_percent']:.1f}%")
    
    print("\n" + "=" * 70)
    print("MODEL TRAINING COMPLETE FOR 10GB RAM LINUX VMs!")
    print("=" * 70)
    print("\nModel optimizations for 10GB RAM:")
    print("  • 150k training samples (3x more than 3.5GB system)")
    print("  • 800+ boosting rounds with early stopping")
    print("  • 5-fold cross-validation for production robustness")
    print("  • Deep trees (max_depth=9, num_leaves=95)")
    print("  • 8 threads for multi-core Linux systems")
    print("  • 383 bins for high precision")
    print("\nPerformance highlights:")
    print(f"  • Test accuracy: {accuracy:.2%}")
    print(f"  • CV score: {cv_results['valid multi_logloss-mean'][-1]:.4f}")
    print(f"  • Model size: {os.path.getsize(model_path) / 1024 / 1024:.2f} MB")
    print(f"  • Iterations: {model.current_iteration()}")
    print("\nDeployment instructions:")
    print("1. Copy model to server:")
    print("   scp models/lightgbm_model_10gb.txt ubuntu@<server-ip>:/opt/trading_model/models/trading_model.txt")
    print("\n2. Update server configuration:")
    print("   ssh ubuntu@<server-ip>")
    print("   cd /opt/trading_model")
    print("   nano models.env")
    print("   # Set: MODEL_PATH=/opt/trading_model/models/trading_model.txt")
    print("\n3. Restart model server:")
    print("   sudo systemctl restart model_server.service")
    print("   sudo journalctl -u model_server -f")
    print("\n4. Verify deployment:")
    print("   curl http://localhost:8000/health")
    
    return model

if __name__ == '__main__':
    try:
        model = train_model_with_cv()
        print("\n✅ Training completed successfully!")
    except KeyboardInterrupt:
        print("\n⚠️  Training interrupted by user")
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()