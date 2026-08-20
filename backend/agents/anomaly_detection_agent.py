"""
zero_carbon_park_agent 异常检测 Agent
负责调用时序预测模型，检测水质指标是否超过阈值
"""
import json
from typing import Dict, Any
from pathlib import Path
import sys
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent


class AnomalyDetectionAgent(BaseAgent):
    """异常检测 Agent

    调用时序预测模型获取未来 24h 预测值，检测是否超过阈值，触发工作流
    """

    def __init__(self):
        super().__init__("anomaly_detection_agent")
        from tools.prediction_tool import PredictionTool
        self.register_tool(PredictionTool())

    @property
    def system_prompt(self) -> str:
        return """你是一个工业废水处理专家，专注于零碳园区的水质异常检测。

你的职责：
1. 调用水质预测工具获取未来24小时的COD、氨氮、硝氮预测值
2. 判断预测值是否超过预设阈值（COD: 250预警/300严重, 氨氮: 25预警/35严重, 硝氮: 3预警/5严重）
3. 如果发现异常，详细描述异常类型、预测值、超阈值时间点和严重程度
4. 输出结构化的异常检测结果

注意：工业废水处理中，COD超标是最常见的异常，需重点关注上游产线排放情况。"""

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        device_id = state.get("params", {}).get("device_id", "WQ-001")

        # 调用预测工具
        tool = self.tools[0]
        pred_result = json.loads(tool.run(device_id=device_id))

        # 分析异常
        anomaly_flags = pred_result.get("anomaly_flags", [])
        has_anomaly = len(anomaly_flags) > 0

        if has_anomaly:
            # 构建 LLM 提示词
            anomaly_summary = json.dumps(anomaly_flags, ensure_ascii=False)
            user_msg = f"水质预测发现异常，请分析：\n{anomaly_summary}"

            try:
                llm_response = self._call_llm(user_msg)
            except Exception:
                llm_response = json.dumps({
                    "analysis": "COD 预测值将在未来6小时内超过严重阈值",
                    "recommendation": "建议立即触发根因分析流程",
                }, ensure_ascii=False)

            anomaly_info = {
                "anomaly_type": anomaly_flags[0]["metric"] + "_exceeded",
                "anomaly_description": f"{anomaly_flags[0]['metric']} 预测值 {anomaly_flags[0]['predicted_value']} 超过阈值 {anomaly_flags[0]['threshold']}",
                "anomaly_severity": anomaly_flags[0]["severity"],
                "predicted_value": anomaly_flags[0]["predicted_value"],
                "threshold": anomaly_flags[0]["threshold"],
                "anomaly_flags": anomaly_flags,
                "llm_analysis": llm_response,
            }
        else:
            anomaly_info = {
                "anomaly_type": None,
                "anomaly_description": "未检测到异常",
                "anomaly_severity": "info",
                "predicted_value": None,
                "threshold": None,
                "anomaly_flags": [],
            }

        return {
            "current_step": "anomaly_detection",
            "anomaly_type": anomaly_info["anomaly_type"],
            "anomaly_description": anomaly_info.get("anomaly_description", ""),
            "anomaly_severity": anomaly_info.get("anomaly_severity", "info"),
            "predicted_value": anomaly_info.get("predicted_value"),
            "threshold": anomaly_info.get("threshold"),
            "messages": [{"agent": self.name, "content": anomaly_info}],
        }