"""
zero_carbon_park_agent 碳捕集利用与封存(CCUS)分析工具
供 Agent 评估碳捕集效率、成本与碳利用路径
"""
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class CCUSTool(BaseTool):
    """碳捕集利用与封存(CCUS)分析工具

    评估碳捕集效率、成本与碳利用路径，支持捕集分析和利用优化。
    """

    @property
    def name(self) -> str:
        return "ccus_analysis"

    @property
    def description(self) -> str:
        return (
            "碳捕集利用与封存(CCUS)分析工具，评估碳捕集效率、成本与碳利用路径。"
            "action 可选值: capture_analysis (碳捕集分析), utilization_optimization (碳利用优化)"
        )

    def run(self, action: str = "capture_analysis",
            co2_emission_tph: float = 10.0, **kwargs) -> str:
        """碳捕集利用与封存(CCUS)分析

        Args:
            action: 操作类型，"capture_analysis" 或 "utilization_optimization"
            co2_emission_tph: CO₂排放量（吨/小时），默认 10.0
            **kwargs: 各 action 对应的参数（capture_tech, capture_rate 等）

        Returns:
            str: JSON 格式的 CCUS 分析结果或错误信息
        """
        if action not in ("capture_analysis", "utilization_optimization"):
            return json.dumps({"error": f"无效 action: {action}，支持 capture_analysis / utilization_optimization"}, ensure_ascii=False)
        if not isinstance(co2_emission_tph, (int, float)) or co2_emission_tph <= 0:
            return json.dumps({"error": f"无效 co2_emission_tph: {co2_emission_tph}，应 > 0"}, ensure_ascii=False)

        logger.info(f"CCUSTool run: action={action}, co2_emission_tph={co2_emission_tph}, kwargs={kwargs}")
        try:
            if action == "capture_analysis":
                result = self._analyze_capture(co2_emission_tph, kwargs)
            elif action == "utilization_optimization":
                result = self._optimize_utilization(kwargs)

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"CCUSTool failed: {e}", exc_info=True)
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @staticmethod
    def _analyze_capture(co2_emission_tph: float, kwargs: Dict) -> Dict:
        """分析碳捕集效率与成本"""
        capture_tech = kwargs.get("capture_tech", "amine_scrubbing")
        capture_rate = kwargs.get("capture_rate", 0.90)

        # 不同技术对应的参数
        tech_params = {
            "amine_scrubbing": {
                "capture_efficiency": 0.90,
                "energy_penalty_mw_per_tco2": 0.35,
                "cost_per_ton_cny": 350.0,
            },
            "membrane_separation": {
                "capture_efficiency": 0.85,
                "energy_penalty_mw_per_tco2": 0.25,
                "cost_per_ton_cny": 280.0,
            },
            "calcium_looping": {
                "capture_efficiency": 0.92,
                "energy_penalty_mw_per_tco2": 0.40,
                "cost_per_ton_cny": 320.0,
            },
        }

        params = tech_params.get(capture_tech, tech_params["amine_scrubbing"])
        capture_efficiency = params["capture_efficiency"] * capture_rate

        captured_co2 = co2_emission_tph * capture_efficiency
        energy_penalty = captured_co2 * params["energy_penalty_mw_per_tco2"]
        capture_cost = params["cost_per_ton_cny"]

        # 碳利用路径
        utilization_paths = [
            {
                "path": "甲醇合成",
                "potential_tph": round(captured_co2 * 0.35, 2),
                "revenue_per_ton_cny": 1200,
            },
            {
                "path": "混凝土养护",
                "potential_tph": round(captured_co2 * 0.25, 2),
                "revenue_per_ton_cny": 400,
            },
            {
                "path": "食品级CO₂",
                "potential_tph": round(captured_co2 * 0.15, 2),
                "revenue_per_ton_cny": 800,
            },
            {
                "path": "地质封存",
                "potential_tph": round(captured_co2 * 0.25, 2),
                "revenue_per_ton_cny": -200,  # 封存成本
            },
        ]

        return {
            "capture_analysis": {
                "capture_technology": capture_tech,
                "co2_emission_tph": co2_emission_tph,
                "capture_efficiency": round(capture_efficiency, 4),
                "captured_co2_tph": round(captured_co2, 2),
                "capture_cost_per_ton_cny": capture_cost,
                "total_daily_cost_cny": round(captured_co2 * capture_cost * 24, 2),
                "energy_penalty_mw": round(energy_penalty, 2),
                "utilization_paths": utilization_paths,
                "storage_capacity_remaining_tco2": 500000,  # 模拟剩余封存容量
            },
        }

    @staticmethod
    def _optimize_utilization(kwargs: Dict) -> Dict:
        """优化碳利用路径分配"""
        captured_co2 = kwargs.get("captured_co2_tph", 9.0)

        # 收益最大化分配
        allocation = {
            "methanol_production": {
                "percentage": 35.0,
                "co2_allocated_tph": round(captured_co2 * 0.35, 2),
                "unit_revenue_cny_per_ton": 1200,
                "total_revenue_cny": round(captured_co2 * 0.35 * 1200, 2),
            },
            "concrete_curing": {
                "percentage": 25.0,
                "co2_allocated_tph": round(captured_co2 * 0.25, 2),
                "unit_revenue_cny_per_ton": 400,
                "total_revenue_cny": round(captured_co2 * 0.25 * 400, 2),
            },
            "food_industry": {
                "percentage": 15.0,
                "co2_allocated_tph": round(captured_co2 * 0.15, 2),
                "unit_revenue_cny_per_ton": 800,
                "total_revenue_cny": round(captured_co2 * 0.15 * 800, 2),
            },
            "geological_storage": {
                "percentage": 25.0,
                "co2_allocated_tph": round(captured_co2 * 0.25, 2),
                "unit_cost_cny_per_ton": -200,
                "total_cost_cny": round(captured_co2 * 0.25 * -200, 2),
            },
        }

        total_revenue = sum(
            v["total_revenue_cny"] if "total_revenue_cny" in v else v["total_cost_cny"]
            for v in allocation.values()
        )

        return {
            "utilization_optimization": {
                "total_captured_co2_tph": captured_co2,
                "allocation": allocation,
                "total_utilization_revenue_cny": round(total_revenue, 2),
                "optimization_strategy": "优先高附加值利用路径（甲醇合成 > 食品级CO₂ > 混凝土养护），剩余部分地质封存",
                "recommendation": "建议建设甲醇合成示范装置，将CO₂转化为高附加值化工产品",
            },
        }

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型: capture_analysis / utilization_optimization",
                    "enum": ["capture_analysis", "utilization_optimization"],
                },
                "co2_emission_tph": {
                    "type": "number",
                    "description": "CO₂排放量（吨/小时），默认10.0",
                },
                "capture_tech": {
                    "type": "string",
                    "description": "捕集技术: amine_scrubbing / membrane_separation / calcium_looping",
                    "enum": ["amine_scrubbing", "membrane_separation", "calcium_looping"],
                },
                "capture_rate": {
                    "type": "number",
                    "description": "目标捕集率，默认0.90",
                },
                "captured_co2_tph": {
                    "type": "number",
                    "description": "已捕集CO₂量（吨/小时）",
                },
            },
            "required": ["action"],
        }