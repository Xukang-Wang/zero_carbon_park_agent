"""
zero_carbon_park_agent 经济性分析工具
供 Agent 计算光伏/储能/综合能源项目的投资回报率、回收期等经济指标
"""
import json
import logging
import sys
import numpy as np
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class EconomicAnalysisTool(BaseTool):
    """经济性分析工具

    计算光伏/储能/综合能源项目的投资回报率、回收期等经济指标。
    """

    @property
    def name(self) -> str:
        return "economic_analysis"

    @property
    def description(self) -> str:
        return (
            "经济性分析工具，计算光伏/储能/综合能源项目的投资回报率、回收期等经济指标。"
            "action 可选值: pv_economics (光伏经济性), storage_economics (储能经济性), "
            "comprehensive_energy (综合能源服务)"
        )

    def run(self, action: str = "pv_economics", **kwargs) -> str:
        """经济性分析

        Args:
            action: 操作类型，pv_economics / storage_economics / comprehensive_energy
            **kwargs: 各 action 对应的参数（capacity_kw, unit_cost 等）

        Returns:
            str: JSON 格式的经济性分析结果或错误信息
        """
        valid_actions = ("pv_economics", "storage_economics", "comprehensive_energy")
        if action not in valid_actions:
            return json.dumps({"error": f"无效 action: {action}，支持 {valid_actions}"}, ensure_ascii=False)

        logger.info(f"EconomicAnalysisTool run: action={action}, kwargs={kwargs}")
        try:
            if action == "pv_economics":
                result = self._analyze_pv(kwargs)
            elif action == "storage_economics":
                result = self._analyze_storage(kwargs)
            elif action == "comprehensive_energy":
                result = self._analyze_comprehensive_energy(kwargs)

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"EconomicAnalysisTool failed: {e}", exc_info=True)
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @staticmethod
    def _analyze_pv(kwargs: Dict) -> Dict:
        """光伏项目经济性分析"""
        capacity_kw = kwargs.get("capacity_kw", 5000.0)
        unit_cost = kwargs.get("unit_cost_cny_per_kw", 3500.0)
        annual_sun_hours = kwargs.get("annual_sun_hours", 1300.0)
        self_use_ratio = kwargs.get("self_use_ratio", 0.80)
        self_use_price = kwargs.get("self_use_price_cny_per_kwh", 0.80)
        feed_in_price = kwargs.get("feed_in_price_cny_per_kwh", 0.39)
        project_life = kwargs.get("project_life_years", 25)
        discount_rate = kwargs.get("discount_rate", 0.06)

        total_investment = capacity_kw * unit_cost
        annual_generation = capacity_kw * annual_sun_hours

        annual_self_use_revenue = annual_generation * self_use_ratio * self_use_price
        annual_feed_in_revenue = annual_generation * (1 - self_use_ratio) * feed_in_price
        annual_revenue = annual_self_use_revenue + annual_feed_in_revenue

        o_and_m_rate = 0.01
        annual_o_and_m = total_investment * o_and_m_rate
        annual_net_revenue = annual_revenue - annual_o_and_m

        simple_payback = total_investment / annual_net_revenue if annual_net_revenue > 0 else float("inf")

        # 简化 IRR 计算
        cash_flows = [-total_investment] + [annual_net_revenue] * project_life
        irr = EconomicAnalysisTool._calc_irr(cash_flows)

        # NPV
        npv = -total_investment + sum(
            annual_net_revenue / (1 + discount_rate) ** t
            for t in range(1, project_life + 1)
        )

        # LCOE
        total_discounted_cost = total_investment + sum(
            annual_o_and_m / (1 + discount_rate) ** t
            for t in range(1, project_life + 1)
        )
        total_discounted_gen = sum(
            annual_generation * 0.995 ** t / (1 + discount_rate) ** t
            for t in range(1, project_life + 1)
        )
        lcoe = total_discounted_cost / total_discounted_gen if total_discounted_gen > 0 else 0

        return {
            "pv_economics": {
                "total_investment_cny": round(total_investment, 2),
                "capacity_kw": capacity_kw,
                "annual_generation_kwh": round(annual_generation, 2),
                "annual_revenue_cny": round(annual_revenue, 2),
                "annual_self_use_revenue_cny": round(annual_self_use_revenue, 2),
                "annual_feed_in_revenue_cny": round(annual_feed_in_revenue, 2),
                "annual_o_and_m_cny": round(annual_o_and_m, 2),
                "annual_net_revenue_cny": round(annual_net_revenue, 2),
                "simple_payback_years": round(simple_payback, 2),
                "irr": round(irr, 4),
                "npv_cny": round(npv, 2),
                "lcoe_cny_per_kwh": round(lcoe, 4),
                "project_life_years": project_life,
            },
        }

    @staticmethod
    def _analyze_storage(kwargs: Dict) -> Dict:
        """储能项目经济性分析"""
        capacity_kwh = kwargs.get("capacity_kwh", 5000.0)
        power_kw = kwargs.get("power_kw", 2500.0)
        unit_cost = kwargs.get("unit_cost_cny_per_kwh", 1200.0)
        daily_cycles = kwargs.get("daily_cycles", 1.0)
        cycle_life = kwargs.get("cycle_life", 6000)
        valley_price = kwargs.get("valley_price_cny_per_kwh", 0.35)
        peak_price = kwargs.get("peak_price_cny_per_kwh", 0.95)
        project_life = kwargs.get("project_life_years", 15)
        discount_rate = kwargs.get("discount_rate", 0.06)

        total_investment = capacity_kwh * unit_cost
        charge_discharge_efficiency = 0.90
        depth_of_discharge = 0.90

        annual_energy_throughput = capacity_kwh * daily_cycles * 365 * depth_of_discharge
        annual_revenue = annual_energy_throughput * charge_discharge_efficiency * (peak_price - valley_price)
        annual_o_and_m = total_investment * 0.015

        annual_net_revenue = annual_revenue - annual_o_and_m
        simple_payback = total_investment / annual_net_revenue if annual_net_revenue > 0 else float("inf")

        cash_flows = [-total_investment] + [annual_net_revenue] * project_life
        irr = EconomicAnalysisTool._calc_irr(cash_flows)

        npv = -total_investment + sum(
            annual_net_revenue / (1 + discount_rate) ** t
            for t in range(1, project_life + 1)
        )

        return {
            "storage_economics": {
                "total_investment_cny": round(total_investment, 2),
                "capacity_kwh": capacity_kwh,
                "power_kw": power_kw,
                "annual_energy_throughput_kwh": round(annual_energy_throughput, 2),
                "annual_revenue_cny": round(annual_revenue, 2),
                "annual_net_revenue_cny": round(annual_net_revenue, 2),
                "simple_payback_years": round(simple_payback, 2),
                "irr": round(irr, 4),
                "npv_cny": round(npv, 2),
                "price_spread_cny_per_kwh": round(peak_price - valley_price, 2),
                "project_life_years": project_life,
            },
        }

    @staticmethod
    def _analyze_comprehensive_energy(kwargs: Dict) -> Dict:
        """综合能源服务经济性分析"""
        total_investment = kwargs.get("total_investment_cny", 20000000.0)
        annual_energy_saving = kwargs.get("annual_energy_saving_kwh", 1500000.0)
        energy_price = kwargs.get("energy_price_cny_per_kwh", 0.80)
        project_life = kwargs.get("project_life_years", 20)
        discount_rate = kwargs.get("discount_rate", 0.06)

        annual_revenue = annual_energy_saving * energy_price
        annual_o_and_m = total_investment * 0.02
        annual_net_revenue = annual_revenue - annual_o_and_m

        simple_payback = total_investment / annual_net_revenue if annual_net_revenue > 0 else float("inf")

        cash_flows = [-total_investment] + [annual_net_revenue] * project_life
        irr = EconomicAnalysisTool._calc_irr(cash_flows)

        npv = -total_investment + sum(
            annual_net_revenue / (1 + discount_rate) ** t
            for t in range(1, project_life + 1)
        )

        carbon_reduction = annual_energy_saving * 0.581 / 1000  # tCO₂

        return {
            "comprehensive_energy": {
                "total_investment_cny": round(total_investment, 2),
                "annual_energy_saving_kwh": annual_energy_saving,
                "annual_revenue_cny": round(annual_revenue, 2),
                "annual_net_revenue_cny": round(annual_net_revenue, 2),
                "simple_payback_years": round(simple_payback, 2),
                "irr": round(irr, 4),
                "npv_cny": round(npv, 2),
                "annual_carbon_reduction_tco2": round(carbon_reduction, 2),
                "project_life_years": project_life,
            },
        }

    @staticmethod
    def _calc_irr(cash_flows: list) -> float:
        """简化 IRR 计算（牛顿法）"""
        rate = 0.1
        for _ in range(100):
            npv = sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))
            d_npv = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cash_flows))
            if abs(d_npv) < 1e-6:
                break
            rate -= npv / d_npv
            if rate < -0.99:
                rate = -0.5
        return rate

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型: pv_economics / storage_economics / comprehensive_energy",
                    "enum": ["pv_economics", "storage_economics", "comprehensive_energy"],
                },
                "capacity_kw": {"type": "number", "description": "装机容量（kW）"},
                "unit_cost_cny_per_kw": {"type": "number", "description": "单位造价（元/kW）"},
                "annual_sun_hours": {"type": "number", "description": "年利用小时数"},
                "self_use_ratio": {"type": "number", "description": "自发自用比例"},
                "capacity_kwh": {"type": "number", "description": "储能容量（kWh）"},
                "power_kw": {"type": "number", "description": "储能功率（kW）"},
                "total_investment_cny": {"type": "number", "description": "总投资（元）"},
                "annual_energy_saving_kwh": {"type": "number", "description": "年节能量（kWh）"},
            },
            "required": ["action"],
        }