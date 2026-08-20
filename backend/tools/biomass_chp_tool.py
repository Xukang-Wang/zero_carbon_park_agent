"""
zero_carbon_park_agent 生物质热电联产(CHP)分析工具
供 Agent 评估生物质能利用效率与碳减排效益
"""
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class BiomassCHPTool(BaseTool):
    """生物质热电联产(CHP)分析工具

    评估生物质能利用效率与碳减排效益，支持CHP分析和沼气分析。
    """

    @property
    def name(self) -> str:
        return "biomass_chp"

    @property
    def description(self) -> str:
        return (
            "生物质热电联产(CHP)分析工具，评估生物质能利用效率与碳减排效益。"
            "action 可选值: chp_analysis (CHP分析), biogas_analysis (沼气分析)"
        )

    def run(self, action: str = "chp_analysis", **kwargs) -> str:
        """生物质热电联产(CHP)分析

        Args:
            action: 操作类型，"chp_analysis"（CHP分析）或 "biogas_analysis"（沼气分析）
            **kwargs: 各 action 对应的参数（feedstock_input_tph, organic_waste_tpd 等）

        Returns:
            str: JSON 格式的生物质 CHP 分析结果或错误信息
        """
        if action not in ("chp_analysis", "biogas_analysis"):
            return json.dumps({"error": f"无效 action: {action}，支持 chp_analysis / biogas_analysis"}, ensure_ascii=False)

        logger.info(f"BiomassCHPTool run: action={action}, kwargs={kwargs}")
        try:
            if action == "chp_analysis":
                result = self._analyze_chp(kwargs)
            elif action == "biogas_analysis":
                result = self._analyze_biogas(kwargs)

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"BiomassCHPTool failed: {e}", exc_info=True)
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @staticmethod
    def _analyze_chp(kwargs: Dict) -> Dict:
        """生物质热电联产分析"""
        feedstock_input_tph = kwargs.get("feedstock_input_tph", 5.0)
        feedstock_type = kwargs.get("feedstock_type", "agricultural_residue")
        feedstock_lhv = kwargs.get("feedstock_lhv_mj_per_kg", 14.5)  # MJ/kg

        # 原料特性
        feedstock_params = {
            "agricultural_residue": {"lhv": 14.5, "moisture": 20.0, "ash_content": 8.0},
            "wood_chips": {"lhv": 16.0, "moisture": 30.0, "ash_content": 2.0},
            "municipal_solid_waste": {"lhv": 10.0, "moisture": 35.0, "ash_content": 15.0},
        }
        params = feedstock_params.get(feedstock_type, feedstock_params["agricultural_residue"])

        # 热输入
        heat_input_mw = feedstock_input_tph * 1000 * params["lhv"] / 3600

        # 发电效率与热效率
        electrical_efficiency = 0.28
        thermal_efficiency = 0.52
        overall_efficiency = electrical_efficiency + thermal_efficiency

        power_output = heat_input_mw * electrical_efficiency * 1000  # kW
        heat_output = heat_input_mw * thermal_efficiency * 1000  # kW

        # 碳排放因子（生物质净排放视为零）
        coal_emission_factor = 0.95  # tCO₂/MWh
        carbon_saving = (power_output + heat_output) / 1000 * coal_emission_factor

        return {
            "chp_analysis": {
                "feedstock": {
                    "type": feedstock_type,
                    "consumption_tph": feedstock_input_tph,
                    "lhv_mj_per_kg": params["lhv"],
                    "moisture_pct": params["moisture"],
                },
                "heat_input_mw": round(heat_input_mw, 2),
                "power_output_kw": round(power_output, 2),
                "heat_output_kw": round(heat_output, 2),
                "electrical_efficiency": electrical_efficiency,
                "thermal_efficiency": thermal_efficiency,
                "overall_efficiency": round(overall_efficiency, 4),
                "carbon_emission_factor_net": 0.0,
                "carbon_saving_vs_coal_tco2_per_h": round(carbon_saving, 2),
                "carbon_saving_vs_coal_tco2_per_year": round(carbon_saving * 8760, 2),
                "note": "生物质燃烧排放的CO₂属于生物碳循环，净排放因子视为零",
            },
        }

    @staticmethod
    def _analyze_biogas(kwargs: Dict) -> Dict:
        """沼气生产分析"""
        organic_waste_tpd = kwargs.get("organic_waste_tpd", 100.0)  # 吨/天
        biogas_yield = kwargs.get("biogas_yield_m3_per_ton", 80.0)  # m³/吨

        daily_biogas_production = organic_waste_tpd * biogas_yield
        methane_content = 0.60
        daily_methane_production = daily_biogas_production * methane_content

        # 沼气发电
        methane_lhv = 35.8  # MJ/m³
        generator_efficiency = 0.38
        daily_power_gen = daily_methane_production * methane_lhv * generator_efficiency / 3.6  # kWh

        # 沼渣沼液
        digestate_tpd = organic_waste_tpd * 0.70
        fertilizer_value = digestate_tpd * 50  # 元/吨 有机肥

        # 碳减排
        coal_displacement = daily_power_gen * 0.581 / 1000  # tCO₂/天
        methane_avoided = organic_waste_tpd * 0.05  # 避免露天堆放CH₄排放 t/天

        return {
            "biogas_analysis": {
                "feedstock": {
                    "organic_waste_tpd": organic_waste_tpd,
                    "annual_capacity_ton": round(organic_waste_tpd * 365, 2),
                },
                "biogas_production": {
                    "daily_biogas_m3": round(daily_biogas_production, 2),
                    "methane_content_pct": methane_content * 100,
                    "daily_methane_m3": round(daily_methane_production, 2),
                },
                "power_generation": {
                    "daily_power_kwh": round(daily_power_gen, 2),
                    "annual_power_mwh": round(daily_power_gen * 365 / 1000, 2),
                    "generator_efficiency": generator_efficiency,
                },
                "byproducts": {
                    "digestate_tpd": round(digestate_tpd, 2),
                    "fertilizer_value_cny_per_day": round(fertilizer_value, 2),
                },
                "carbon_reduction": {
                    "coal_displacement_tco2_per_day": round(coal_displacement, 2),
                    "methane_avoided_t_per_day": round(methane_avoided, 2),
                    "total_annual_carbon_reduction_tco2": round((coal_displacement + methane_avoided * 25) * 365, 2),
                },
            },
        }

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型: chp_analysis / biogas_analysis",
                    "enum": ["chp_analysis", "biogas_analysis"],
                },
                "feedstock_input_tph": {
                    "type": "number",
                    "description": "生物质原料投入量（吨/小时），默认5.0",
                },
                "feedstock_type": {
                    "type": "string",
                    "description": "原料类型: agricultural_residue / wood_chips / municipal_solid_waste",
                    "enum": ["agricultural_residue", "wood_chips", "municipal_solid_waste"],
                },
                "organic_waste_tpd": {
                    "type": "number",
                    "description": "有机废弃物处理量（吨/天），默认100.0",
                },
                "biogas_yield_m3_per_ton": {
                    "type": "number",
                    "description": "沼气产率（m³/吨），默认80.0",
                },
            },
            "required": ["action"],
        }