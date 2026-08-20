"""
zero_carbon_park_agent 特征工程管道
构建滑动窗口特征、差分特征、周期特征，为时序预测模型提供输入
"""
import numpy as np
import pandas as pd
from typing import Tuple, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SEQ_LEN, PRED_LEN, FEATURE_DIM


FEATURE_COLUMNS = ["cod", "ammonia_nitrogen", "nitrate_nitrogen", "ph",
                   "temperature", "dissolved_oxygen", "inflow_rate", "sludge_conc"]
TARGET_COLUMNS = ["cod", "ammonia_nitrogen", "nitrate_nitrogen"]


class WaterFeatureEngineer:
    """水质特征工程

    为 LSTM-Transformer 模型构建输入特征，包括：
    - 滑动窗口统计特征（1h/4h/12h/24h 的均值、标准差）
    - 差分特征（1阶差分）
    - 周期特征（小时、星期几）
    """

    def __init__(self, seq_len: int = SEQ_LEN, pred_len: int = PRED_LEN):
        self.seq_len = seq_len
        self.pred_len = pred_len

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """构建特征工程"""
        df = df.copy()
        df = df.sort_values("timestamp").reset_index(drop=True)

        for col in FEATURE_COLUMNS:
            if col not in df.columns:
                continue
            # 滑动窗口统计
            for window in [4, 12, 24]:
                df[f"{col}_ma{window}"] = df[col].rolling(window, min_periods=1).mean()
                df[f"{col}_std{window}"] = df[col].rolling(window, min_periods=1).std().fillna(0)

            # 一阶差分
            df[f"{col}_diff1"] = df[col].diff().fillna(0)

        # 时间周期特征
        df["hour_of_day"] = df["timestamp"].dt.hour / 24.0
        df["day_of_week"] = df["timestamp"].dt.dayofweek / 7.0

        return df

    def prepare_sequences(self, df: pd.DataFrame
                          ) -> Tuple[np.ndarray, np.ndarray]:
        """准备训练/预测用的序列数据

        Returns:
            X: (N, seq_len, feature_dim) 输入序列
            y: (N, pred_len, 3) 目标序列（COD, 氨氮, 硝氮）
        """
        df = self.build_features(df)

        # 构建完整的特征矩阵
        feature_cols = []
        for col in FEATURE_COLUMNS:
            feature_cols.append(col)
            for window in [4, 12, 24]:
                feature_cols.append(f"{col}_ma{window}")
                feature_cols.append(f"{col}_std{window}")
            feature_cols.append(f"{col}_diff1")
        feature_cols.extend(["hour_of_day", "day_of_week"])

        # 确保所有列存在
        available_cols = [c for c in feature_cols if c in df.columns]
        data = df[available_cols].values.astype(np.float32)

        X, y = [], []
        total_len = self.seq_len + self.pred_len

        for i in range(len(data) - total_len + 1):
            X.append(data[i:i + self.seq_len])
            # 目标：未来 pred_len 小时的三个指标
            target = df.iloc[i + self.seq_len:i + total_len][TARGET_COLUMNS].values
            y.append(target.astype(np.float32))

        return np.array(X), np.array(y)

    def prepare_single_prediction(self, df: pd.DataFrame) -> np.ndarray:
        """为单次预测准备输入序列（取最近 seq_len 条数据）"""
        df = self.build_features(df)

        feature_cols = []
        for col in FEATURE_COLUMNS:
            feature_cols.append(col)
            for window in [4, 12, 24]:
                feature_cols.append(f"{col}_ma{window}")
                feature_cols.append(f"{col}_std{window}")
            feature_cols.append(f"{col}_diff1")
        feature_cols.extend(["hour_of_day", "day_of_week"])

        available_cols = [c for c in feature_cols if c in df.columns]

        if len(df) < self.seq_len:
            raise ValueError(f"数据不足: 需要至少 {self.seq_len} 条记录，当前 {len(df)} 条")

        recent = df.iloc[-self.seq_len:][available_cols].values.astype(np.float32)
        return recent[np.newaxis, :, :]  # (1, seq_len, n_features)


if __name__ == "__main__":
    # 测试
    from data.mock_data import get_mock_data
    import pandas as pd
    from datetime import datetime

    records = get_mock_data().get_water_history("WQ-001", 240)
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    engineer = WaterFeatureEngineer()
    X, y = engineer.prepare_sequences(df)
    print(f"序列形状: X={X.shape}, y={y.shape}")
    print(f"特征维度: {X.shape[2]}")
    print(f"目标维度: {y.shape[2]}")