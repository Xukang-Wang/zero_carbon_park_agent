"""
zero_carbon_park_agent 时序预测工具
供 Agent 调用水质预测模型（基于静态预计算数据）
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.base_tool import BaseTool


class PredictionTool(BaseTool):
    """水质时序预测工具

    使用静态预计算数据生成预测结果，无需安装 PyTorch。
    后续可替换为真实的 LSTM-Transformer 模型推理。
    """

    @property
    def name(self) -> str:
        return "water_quality_prediction"

    @property
    def description(self) -> str:
        return (
            "预测未来24小时的COD（化学需氧量）、氨氮、硝氮指标。"
            "输入参数: device_id (设备编号, 如 'WQ-001'), horizon_hours (预测时长, 默认24)"
        )

    def run(self, device_id: str = "WQ-001", horizon_hours: int = 24) -> str:
        from models.anomaly_detector import get_anomaly_detector

        try:
            from data.mock_data import get_mock_data
            mg = get_mock_data()

            now = datetime.now()

            # 从静态数据加载预测
            preds = mg.get_water_prediction(device_id, horizon_hours)

            predictions = {
                "cod": [p["cod"] for p in preds],
                "ammonia_nitrogen": [p["ammonia_nitrogen"] for p in preds],
                "nitrate_nitrogen": [p["nitrate_nitrogen"] for p in preds],
            }
            timestamps = [p["target_timestamp"] for p in preds]

            # 异常检测
            detector = get_anomaly_detector()
            anomalies = detector.detect(predictions, timestamps)

            result = {
                "device_id": device_id,
                "predicted_at": now.isoformat(),
                "horizon_hours": horizon_hours,
                "predictions": [
                    {
                        "target_timestamp": timestamps[i],
                        "cod": round(predictions["cod"][i], 2),
                        "ammonia_nitrogen": round(predictions["ammonia_nitrogen"][i], 2),
                        "nitrate_nitrogen": round(predictions["nitrate_nitrogen"][i], 2),
                    }
                    for i in range(horizon_hours)
                ],
                "anomaly_flags": anomalies,
                "model_version": "simulation_v1",
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "设备编号，如 'WQ-001'",
                },
                "horizon_hours": {
                    "type": "integer",
                    "description": "预测时长（小时），默认24",
                    "default": 24,
                },
            },
            "required": ["device_id"],
        }