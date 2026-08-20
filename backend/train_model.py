"""
zero_carbon_park_agent 模型训练脚本
使用模拟数据训练 LSTM-Transformer 预测模型
"""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))


def main():
    print("\n" + "=" * 60)
    print("  zero_carbon_park_agent 模型训练")
    print("=" * 60 + "\n")

    # 1. 加载训练数据
    print("[1/3] 加载训练数据...")
    from data.mock_data import get_mock_data
    from features.water_feature_engineering import WaterFeatureEngineer
    import pandas as pd

    records = get_mock_data().get_water_history("WQ-001", 2160)  # 90天
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    print(f"  数据量: {len(df)} 条记录")

    # 2. 特征工程
    print("\n[2/3] 特征工程...")
    engineer = WaterFeatureEngineer()
    X, y = engineer.prepare_sequences(df)
    print(f"  训练样本: X={X.shape}, y={y.shape}")

    # 划分训练集/验证集
    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]
    print(f"  训练集: {len(X_train)} | 验证集: {len(X_val)}")

    # 3. 训练模型
    print("\n[3/3] 训练模型...")
    from models.lstm_transformer import WaterPredictionModel

    model = WaterPredictionModel(input_dim=X.shape[2], pred_len=24)
    history = model.train(X_train, y_train, epochs=30, batch_size=32, lr=0.001)

    # 验证
    preds = model.predict(X_val[:5])
    mape = np.mean(np.abs(y_val[:5] - preds) / (np.abs(y_val[:5]) + 1e-8))
    print(f"\n  验证 MAPE: {mape:.4f}")

    # 保存模型
    model.save()
    print(f"\n  模型已保存到 data/models/")

    print("\n" + "=" * 60)
    print("  训练完成！")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()