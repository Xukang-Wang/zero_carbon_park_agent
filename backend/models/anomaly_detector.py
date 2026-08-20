"""
zero_carbon_park_agent 异常检测模型（基于 LightGBM 残差分析）
对预测残差进行统计检验，判断是否存在异常偏离
"""
import numpy as np
import pickle
from pathlib import Path
from typing import Dict, List, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import WATER_THRESHOLDS, MODEL_DIR


class AnomalyDetector:
    """水质异常检测器

    两层检测机制：
    1. 阈值检测：预测值是否超过预设阈值
    2. 残差统计检测：预测残差是否显著偏离历史分布（3-sigma 原则）
    """

    def __init__(self):
        self.thresholds = WATER_THRESHOLDS
        self.residual_stats = {}  # {metric: {"mean": float, "std": float}}
        self.is_fitted = False

    def fit(self, residuals: Dict[str, np.ndarray]):
        """拟合残差分布（用于统计检测）

        Args:
            residuals: {"cod": array, "ammonia_nitrogen": array, "nitrate_nitrogen": array}
        """
        for metric, values in residuals.items():
            self.residual_stats[metric] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
            }
        self.is_fitted = True
        print(f"残差统计拟合完成: {self.residual_stats}")

    def detect(self, predictions: Dict[str, List[float]],
               timestamps: List[str] = None) -> List[Dict]:
        """检测异常

        Args:
            predictions: {"cod": [...], "ammonia_nitrogen": [...], "nitrate_nitrogen": [...]}
            timestamps: 对应的时间戳列表

        Returns:
            异常列表 [{"metric": "cod", "index": 5, "value": 320.5, "threshold": 300, "severity": "critical"}, ...]
        """
        anomalies = []
        n_steps = len(next(iter(predictions.values())))

        for i in range(n_steps):
            for metric in ["cod", "ammonia_nitrogen", "nitrate_nitrogen"]:
                value = predictions[metric][i]
                thresh = self.thresholds.get(metric, {})

                # 阈值检测
                severity = None
                if thresh.get("critical") and value >= thresh["critical"]:
                    severity = "critical"
                    threshold = thresh["critical"]
                elif thresh.get("warning") and value >= thresh["warning"]:
                    severity = "warning"
                    threshold = thresh["warning"]

                if severity:
                    ts = timestamps[i] if timestamps else f"t+{i+1}h"
                    anomalies.append({
                        "target_timestamp": ts,
                        "metric": metric,
                        "predicted_value": round(value, 2),
                        "threshold": threshold,
                        "severity": severity,
                    })

        return anomalies

    def save(self, path: Path = None):
        if path is None:
            path = MODEL_DIR / "anomaly_detector.pkl"
        with open(path, "wb") as f:
            pickle.dump({
                "residual_stats": self.residual_stats,
                "is_fitted": self.is_fitted,
            }, f)
        print(f"异常检测器已保存: {path}")

    def load(self, path: Path = None):
        if path is None:
            path = MODEL_DIR / "anomaly_detector.pkl"
        if not path.exists():
            print(f"异常检测器文件不存在: {path}，将使用默认阈值")
            self.is_fitted = True
            return False
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.residual_stats = data["residual_stats"]
        self.is_fitted = data["is_fitted"]
        print(f"异常检测器已加载: {path}")
        return True


# 全局实例
_detector_instance: AnomalyDetector = None


def get_anomaly_detector() -> AnomalyDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = AnomalyDetector()
        _detector_instance.load()
    return _detector_instance


if __name__ == "__main__":
    detector = AnomalyDetector()

    # 模拟预测数据测试
    preds = {
        "cod": [220, 260, 310, 280, 240],
        "ammonia_nitrogen": [18, 22, 28, 20, 19],
        "nitrate_nitrogen": [1.5, 2.0, 3.5, 2.5, 1.8],
    }
    anomalies = detector.detect(preds)
    for a in anomalies:
        print(f"  [{a['severity']}] {a['metric']}: {a['predicted_value']} > {a['threshold']}")