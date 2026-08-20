"""
zero_carbon_park_agent 新能源功率预测工具
供 Agent 预测光伏/风电未来24小时出力，基于静态模拟数据
"""
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class PowerPredictionTool(BaseTool):
    """新能源功率预测工具

    预测光伏/风电未来24小时出力，基于静态预计算数据。
    """

    @property
    def name(self) -> str:
        return "power_prediction"

    @property
    def description(self) -> str:
        return (
            "新能源功率预测工具，预测光伏/风电未来24小时出力，基于静态模拟数据。"
            "source 可选值: pv (光伏), wind (风电); horizon_hours 默认 24"
        )

    def run(self, source: str = "pv", horizon_hours: int = 24,
            installed_capacity_kw: float = 5000.0) -> str:
        """新能源功率预测

        Args:
            source: 电源类型，"pv"（光伏）或 "wind"（风电）
            horizon_hours: 预测时长（小时），默认 24，范围 1-168
            installed_capacity_kw: 装机容量（kW），默认 5000

        Returns:
            str: JSON 格式的功率预测结果或错误信息
        """
        if source not in ("pv", "wind"):
            return json.dumps({"error": f"无效 source: {source}，支持 pv / wind"}, ensure_ascii=False)
        if not isinstance(horizon_hours, int) or horizon_hours < 1 or horizon_hours > 168:
            return json.dumps({"error": f"无效 horizon_hours: {horizon_hours}，应在 1-168 范围内"}, ensure_ascii=False)
        if not isinstance(installed_capacity_kw, (int, float)) or installed_capacity_kw <= 0:
            return json.dumps({"error": f"无效 installed_capacity_kw: {installed_capacity_kw}，应 > 0"}, ensure_ascii=False)

        logger.info(f"PowerPredictionTool run: source={source}, horizon_hours={horizon_hours}, "
                     f"installed_capacity_kw={installed_capacity_kw}")
        try:
            from data.mock_data import get_mock_data
            mg = get_mock_data()

            now = datetime.now()
            timestamps = [(now + timedelta(hours=i + 1)).isoformat()
                          for i in range(horizon_hours)]

            if source == "pv":
                raw_data = mg.get_pv_forecast()
            else:
                raw_data = mg.get_wind_forecast()

            # 从预计算数据中提取，按容量比例缩放
            default_cap = 5000.0 if source == "pv" else 3000.0
            scale = installed_capacity_kw / default_cap

            predictions = []
            for i in range(horizon_hours):
                idx = i % len(raw_data)
                power = raw_data[idx]["power_kw"] * scale
                cf = raw_data[idx].get("confidence", 0.85)
                predictions.append({
                    "power_kw": round(power, 2),
                    "capacity_factor": round(power / installed_capacity_kw, 4) if installed_capacity_kw > 0 else 0,
                })

            # 汇总统计
            total_energy = sum(p["power_kw"] for p in predictions)
            peak_power = max(p["power_kw"] for p in predictions)
            avg_cf = sum(p["capacity_factor"] for p in predictions) / len(predictions)

            result = {
                "source": source,
                "installed_capacity_kw": installed_capacity_kw,
                "predicted_at": now.isoformat(),
                "horizon_hours": horizon_hours,
                "forecast": [
                    {
                        "timestamp": timestamps[i],
                        "power_kw": predictions[i]["power_kw"],
                        "capacity_factor": predictions[i]["capacity_factor"],
                    }
                    for i in range(horizon_hours)
                ],
                "summary": {
                    "total_energy_kwh": round(total_energy, 2),
                    "peak_power_kw": round(peak_power, 2),
                    "avg_capacity_factor": round(avg_cf, 4),
                },
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"PowerPredictionTool failed: {e}", exc_info=True)
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "电源类型: pv (光伏) / wind (风电)",
                    "enum": ["pv", "wind"],
                },
                "horizon_hours": {
                    "type": "integer",
                    "description": "预测时长（小时），默认24",
                    "default": 24,
                },
                "installed_capacity_kw": {
                    "type": "number",
                    "description": "装机容量（kW），默认5000",
                },
            },
            "required": ["source"],
        }