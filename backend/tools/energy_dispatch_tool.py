"""
zero_carbon_park_agent 多能互补调度优化工具
提供光伏/风电/储能/负荷的协同优化调度策略
"""
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class MultiEnergyDispatchTool(BaseTool):
    """多能互补调度优化工具

    基于光伏/风电出力预测和负荷预测，优化源网荷储运行策略，
    支持优化调度和绿电追溯两种模式。
    """

    @property
    def name(self) -> str:
        return "multi_energy_dispatch"

    @property
    def description(self) -> str:
        return (
            "多能互补调度优化工具，基于光伏/风电出力预测和负荷预测，优化源网荷储运行策略。"
            "action 可选值: optimize (优化调度), green_power_trace (绿电追溯)"
        )

    def run(self, action: str = "optimize", pv_forecast: float = None,
            wind_forecast: float = None, load_forecast: float = None,
            storage_soc: float = 50) -> str:
        """多能互补调度优化

        Args:
            action: 操作类型，"optimize" 或 "green_power_trace"
            pv_forecast: 光伏出力预测 (kW)
            wind_forecast: 风电出力预测 (kW)
            load_forecast: 负荷预测 (kW)
            storage_soc: 储能当前 SOC (%)

        Returns:
            str: JSON 格式的调度结果或错误信息
        """
        if action not in ("optimize", "green_power_trace"):
            return json.dumps({"error": f"无效 action: {action}，支持 optimize / green_power_trace"}, ensure_ascii=False)

        logger.info(f"MultiEnergyDispatchTool run: action={action}, pv_forecast={pv_forecast}, "
                     f"wind_forecast={wind_forecast}, load_forecast={load_forecast}, storage_soc={storage_soc}")
        try:
            if action == "optimize":
                result = self._optimize_dispatch(pv_forecast, wind_forecast, load_forecast, storage_soc)
            elif action == "green_power_trace":
                result = self._green_power_trace()

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"MultiEnergyDispatchTool failed: {e}", exc_info=True)
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def _optimize_dispatch(self, pv_forecast, wind_forecast, load_forecast, storage_soc):
        """多能互补优化调度核心算法（模拟）"""
        pv = pv_forecast if pv_forecast is not None else 1200.0
        wind = wind_forecast if wind_forecast is not None else 800.0
        load = load_forecast if load_forecast is not None else 1500.0
        soc = storage_soc

        # 可再生能源总出力
        renewable_total = pv + wind

        # 光伏利用率：优先使用光伏，剩余考虑储能
        pv_utilization = min(pv, load) / pv * 100 if pv > 0 else 0
        wind_utilization = min(wind, max(0, load - pv)) / wind * 100 if wind > 0 else 0

        # 储能充放电决策
        net_power = renewable_total - load
        if net_power > 0:
            # 可再生能源过剩，储能充电
            storage_charge_discharge = -min(net_power * 0.8, (100 - soc) / 100 * 500)
            grid_import = 0
        else:
            # 可再生能源不足，储能放电或购电
            deficit = abs(net_power)
            storage_discharge_capacity = (soc - 20) / 100 * 500 if soc > 20 else 0
            if storage_discharge_capacity >= deficit:
                storage_charge_discharge = deficit
                grid_import = 0
            else:
                storage_charge_discharge = storage_discharge_capacity
                grid_import = deficit - storage_discharge_capacity

        # 可再生能源占比
        renewable_ratio = (renewable_total + max(0, storage_charge_discharge)) / (load + abs(min(0, storage_charge_discharge))) * 100
        renewable_ratio = min(100, max(0, round(renewable_ratio, 1)))

        # 碳排放节省（vs 纯电网供电，电网碳排放因子 0.581 kgCO₂/kWh）
        carbon_saving = (renewable_total + max(0, storage_charge_discharge)) * 0.581 / 1000  # 吨

        # 估计算成本（元）
        grid_price = 0.8  # 元/kWh
        renewable_cost = renewable_total * 0.35  # 可再生能源平准化度电成本
        grid_cost = grid_import * grid_price
        total_cost = round(renewable_cost + grid_cost, 2)

        return {
            "pv_forecast_kw": pv,
            "wind_forecast_kw": wind,
            "load_forecast_kw": load,
            "storage_soc_percent": soc,
            "dispatch_plan": {
                "pv_utilization_percent": round(pv_utilization, 1),
                "wind_utilization_percent": round(wind_utilization, 1),
                "grid_import_kw": round(grid_import, 1),
                "storage_charge_discharge_kw": round(storage_charge_discharge, 1),
                "renewable_ratio_percent": renewable_ratio,
                "estimated_carbon_saving_tco2": round(carbon_saving, 3),
                "total_cost_cny": total_cost,
            },
            "strategy": "优先消纳光伏，其次风电，储能削峰填谷，电网兜底" if grid_import > 0 else "完全依靠可再生能源与储能，无需电网供电",
            "recommendations": [
                "建议储能系统在电价谷段（0:00-8:00）充电，峰段（10:00-15:00, 18:00-21:00）放电",
                "光伏出力高峰期（11:00-14:00）优先供给负荷，余电存入储能",
                "当可再生能源占比低于70%时，建议启动需求响应机制",
            ],
        }

    def _green_power_trace(self):
        """绿电追溯（模拟）"""
        return {
            "green_power_supply_chain": [
                {
                    "source": "园区屋顶光伏",
                    "installed_capacity_kw": 2000,
                    "current_output_kw": 1200,
                    "carbon_factor_kgco2_kwh": 0.048,
                    "supply_to": ["污水处理站", "办公楼", "储能系统"],
                    "supply_ratio": 0.55,
                },
                {
                    "source": "园区风力发电",
                    "installed_capacity_kw": 1500,
                    "current_output_kw": 800,
                    "carbon_factor_kgco2_kwh": 0.011,
                    "supply_to": ["污水处理站", "充电桩"],
                    "supply_ratio": 0.35,
                },
                {
                    "source": "储能系统",
                    "installed_capacity_kwh": 2000,
                    "current_soc_percent": 65,
                    "carbon_factor_kgco2_kwh": 0.0,
                    "supply_to": ["应急备用", "峰谷套利"],
                    "supply_ratio": 0.10,
                },
            ],
            "total_green_ratio_percent": 78.5,
            "grid_import_ratio_percent": 21.5,
            "certificate_info": {
                "green_certificates_held": 1200,
                "certificate_type": "GEC (Green Electricity Certificate)",
                "equivalent_carbon_offset_tco2": 696.0,
            },
        }

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型: optimize / green_power_trace",
                    "enum": ["optimize", "green_power_trace"],
                },
                "pv_forecast": {
                    "type": "number",
                    "description": "光伏出力预测 (kW)",
                },
                "wind_forecast": {
                    "type": "number",
                    "description": "风电出力预测 (kW)",
                },
                "load_forecast": {
                    "type": "number",
                    "description": "负荷预测 (kW)",
                },
                "storage_soc": {
                    "type": "number",
                    "description": "储能当前 SOC (%)",
                },
            },
            "required": ["action"],
        }