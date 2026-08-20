"""
zero_carbon_park_agent 知识图谱查询工具
供 Agent 查询能源知识图谱，进行能源血缘追溯与碳足迹计算
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.base_tool import BaseTool


class GraphQueryTool(BaseTool):
    """能源知识图谱查询工具"""

    @property
    def name(self) -> str:
        return "energy_graph_query"

    @property
    def description(self) -> str:
        return (
            "查询能源知识图谱，支持能源血缘追溯、碳足迹计算、实体信息查询。"
            "action 可选值: trace_energy (能源追溯), carbon_footprint (碳足迹), "
            "entity_info (实体信息), overview (图谱概览), upstream_loads (上游产线查询)"
        )

    def run(self, action: str = "overview", entity_id: str = None,
            trace_direction: str = "upstream") -> str:
        from graph.graph_builder import get_knowledge_graph

        try:
            kg = get_knowledge_graph()

            if action == "overview":
                result = kg.get_overview()
            elif action == "trace_energy":
                if not entity_id:
                    return json.dumps({"error": "缺少 entity_id 参数"}, ensure_ascii=False)
                trace = kg.trace_energy(entity_id, trace_direction)
                entity = kg.get_entity_info(entity_id)
                result = {
                    "entity": entity,
                    "trace_path": trace,
                }
            elif action == "carbon_footprint":
                result = kg.calculate_carbon_footprint()
            elif action == "entity_info":
                if not entity_id:
                    return json.dumps({"error": "缺少 entity_id 参数"}, ensure_ascii=False)
                result = kg.get_entity_info(entity_id)
            elif action == "upstream_loads":
                result = kg.get_loads_upstream_of_wwtp()
            else:
                return json.dumps({"error": f"未知 action: {action}"}, ensure_ascii=False)

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型: trace_energy / carbon_footprint / entity_info / overview / upstream_loads",
                    "enum": ["trace_energy", "carbon_footprint", "entity_info", "overview", "upstream_loads"],
                },
                "entity_id": {
                    "type": "string",
                    "description": "实体 ID，如 'WWTP-001'",
                },
                "trace_direction": {
                    "type": "string",
                    "description": "追溯方向: upstream / downstream",
                    "enum": ["upstream", "downstream"],
                },
            },
            "required": ["action"],
        }


class ResourceRecoveryTool(BaseTool):
    """资源回收优化工具"""

    @property
    def name(self) -> str:
        return "resource_recovery_optimization"

    @property
    def description(self) -> str:
        return (
            "基于预测的COD负荷，计算最优厌氧消化罐进料速率与停留时间，"
            "最大化甲烷产率。输入: cod_pred (预测COD值), inflow_rate (进水流量)"
        )

    def run(self, cod_pred: float = 250.0, inflow_rate: float = 800.0) -> str:
        try:
            # 厌氧消化优化模型（简化版）
            # 最优进料 COD 负荷: 2-5 kg COD/m³/day
            # 最优停留时间: 15-30 天

            # 基于 COD 预测计算最优进料速率
            optimal_loading_rate = min(5.0, max(2.0, cod_pred / 100))
            optimal_retention = max(15, min(30, 450 / optimal_loading_rate))

            # 预估甲烷产率 (0.35 m³ CH₄ / kg COD removed)
            cod_removal_efficiency = 0.85
            methane_yield = cod_pred * inflow_rate * 24 * cod_removal_efficiency * 0.35 / 1000

            # 生物硫回收优化
            sulfur_removal_rate = 0.90
            bio_sulfur_yield = cod_pred * 0.02 * sulfur_removal_rate  # 估算

            result = {
                "cod_pred_mg_per_l": cod_pred,
                "inflow_rate_m3_per_h": inflow_rate,
                "optimal_loading_rate_kg_cod_m3_d": round(optimal_loading_rate, 2),
                "optimal_retention_days": round(optimal_retention, 0),
                "estimated_methane_yield_m3_per_h": round(methane_yield, 2),
                "estimated_bio_sulfur_yield_kg_per_h": round(bio_sulfur_yield, 2),
                "recommendations": [
                    f"调节厌氧罐进料速率至 {inflow_rate * 0.85:.0f} m³/h（降低15%）",
                    f"保持停留时间 {optimal_retention:.0f} 天",
                    "建议启动备用曝气风机以应对负荷波动",
                ],
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "cod_pred": {
                    "type": "number",
                    "description": "预测的 COD 值 (mg/L)",
                },
                "inflow_rate": {
                    "type": "number",
                    "description": "进水流量 (m³/h)",
                },
            },
            "required": ["cod_pred"],
        }


class NotificationTool(BaseTool):
    """通知推送工具（模拟）"""

    @property
    def name(self) -> str:
        return "send_notification"

    @property
    def description(self) -> str:
        return (
            "发送通知消息（模拟企业微信/飞书消息推送）。"
            "输入: message (消息内容), severity (严重程度: warning/critical/info)"
        )

    def run(self, message: str = "", severity: str = "warning") -> str:
        # 模拟通知推送
        result = {
            "status": "sent",
            "channel": "simulated_feishu",
            "message": message,
            "severity": severity,
            "sent_at": __import__("datetime").datetime.now().isoformat(),
            "note": "模拟通知 - 实际部署时替换为飞书/企业微信 Webhook",
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "通知消息内容",
                },
                "severity": {
                    "type": "string",
                    "description": "严重程度",
                    "enum": ["warning", "critical", "info"],
                },
            },
            "required": ["message"],
        }