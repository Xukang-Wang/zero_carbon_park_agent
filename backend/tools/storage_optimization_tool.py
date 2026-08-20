"""
zero_carbon_park_agent 储能优化调度工具
支持峰谷套利策略、需量管理、共享储能收益分析
"""
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class StorageOptimizationTool(BaseTool):
    """储能优化调度工具

    支持峰谷套利策略、需量管理、共享储能收益分析三种模式。
    """

    @property
    def name(self) -> str:
        return "storage_optimization"

    @property
    def description(self) -> str:
        return (
            "储能优化调度工具，支持峰谷套利策略、需量管理、共享储能收益分析。"
            "action 可选值: optimize (优化调度), shared_storage_analysis (共享储能分析)"
        )

    def run(self, action: str = "optimize", current_soc: float = 50,
            electricity_price: dict = None, peak_hours: list = None) -> str:
        """储能优化调度

        Args:
            action: 操作类型，"optimize" 或 "shared_storage_analysis"
            current_soc: 当前储能 SOC (%)，范围 0-100
            electricity_price: 分时电价配置 {peak, flat, valley}
            peak_hours: 峰时段小时列表

        Returns:
            str: JSON 格式的储能优化结果或错误信息
        """
        if action not in ("optimize", "shared_storage_analysis"):
            return json.dumps({"error": f"无效 action: {action}，支持 optimize / shared_storage_analysis"}, ensure_ascii=False)
        if not isinstance(current_soc, (int, float)) or current_soc < 0 or current_soc > 100:
            return json.dumps({"error": f"无效 current_soc: {current_soc}，应在 0-100 范围内"}, ensure_ascii=False)

        logger.info(f"StorageOptimizationTool run: action={action}, current_soc={current_soc}")
        try:
            if action == "optimize":
                result = self._optimize_storage(current_soc, electricity_price, peak_hours)
            elif action == "shared_storage_analysis":
                result = self._shared_storage_analysis()

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"StorageOptimizationTool failed: {e}", exc_info=True)
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def _optimize_storage(self, current_soc, electricity_price, peak_hours):
        """储能优化调度（模拟 24 小时充放电计划）"""
        soc = current_soc

        # 默认分时电价（元/kWh）
        if electricity_price is None:
            electricity_price = {
                "peak": 1.2,     # 峰段 10:00-12:00, 14:00-19:00
                "flat": 0.75,    # 平段 8:00-10:00, 12:00-14:00, 19:00-22:00
                "valley": 0.35,  # 谷段 0:00-8:00, 22:00-24:00
            }

        # 默认峰时段
        if peak_hours is None:
            peak_hours = [10, 11, 14, 15, 16, 17, 18]

        # 模拟 24 小时充放电调度
        schedule = []
        storage_capacity = 2000  # kWh
        battery_power = 500      # kW 额定功率

        for hour in range(24):
            is_peak = hour in peak_hours
            is_valley = hour < 8 or hour >= 22

            if is_valley and soc < 90:
                # 谷段充电
                charge_power = min(battery_power, (90 - soc) / 100 * storage_capacity)
                soc = min(90, soc + charge_power / storage_capacity * 100)
                schedule.append({
                    "hour": hour,
                    "action": "charge",
                    "power_kw": round(charge_power, 1),
                    "soc_after_percent": round(soc, 1),
                    "price_cny_per_kwh": electricity_price["valley"],
                })
            elif is_peak and soc > 25:
                # 峰段放电
                discharge_power = min(battery_power, (soc - 25) / 100 * storage_capacity)
                soc = max(25, soc - discharge_power / storage_capacity * 100)
                schedule.append({
                    "hour": hour,
                    "action": "discharge",
                    "power_kw": round(discharge_power, 1),
                    "soc_after_percent": round(soc, 1),
                    "price_cny_per_kwh": electricity_price["peak"],
                })
            else:
                # 平段 / 不可充放电
                schedule.append({
                    "hour": hour,
                    "action": "idle",
                    "power_kw": 0,
                    "soc_after_percent": round(soc, 1),
                    "price_cny_per_kwh": electricity_price["flat"] if 8 <= hour < 22 else electricity_price["valley"],
                })

        # 计算收益
        total_charge_kwh = sum(abs(s["power_kw"]) for s in schedule if s["action"] == "charge")
        total_discharge_kwh = sum(s["power_kw"] for s in schedule if s["action"] == "discharge")

        # 峰谷套利日收益
        valley_cost = total_charge_kwh * electricity_price["valley"]
        peak_revenue = total_discharge_kwh * electricity_price["peak"]
        daily_arbitrage_revenue = round(peak_revenue - valley_cost * 0.9, 2)  # 考虑 90% 充放电效率

        # 需量管理节省（假设最大需量降低 300 kW，需量电价 40 元/kW/月）
        peak_shaving_power_kw = 300
        demand_charge_saving = round(peak_shaving_power_kw * 40, 2)

        # 日总收益
        total_daily_benefit = round(daily_arbitrage_revenue + demand_charge_saving / 30, 2)

        return {
            "current_soc_percent": current_soc,
            "schedule": schedule,
            "summary": {
                "peak_shaving_power_kw": peak_shaving_power_kw,
                "daily_arbitrage_revenue_cny": daily_arbitrage_revenue,
                "demand_charge_saving_monthly_cny": demand_charge_saving,
                "total_daily_benefit_cny": total_daily_benefit,
                "total_charge_kwh": round(total_charge_kwh, 1),
                "total_discharge_kwh": round(total_discharge_kwh, 1),
                "round_trip_efficiency_percent": 90.0,
            },
            "strategy": "谷段充电、峰段放电，同时削减尖峰需量以降低基本电费",
        }

    def _shared_storage_analysis(self):
        """共享储能商业模式分析（模拟）"""
        # 基本参数
        installed_capacity_kwh = 5000
        installed_power_kw = 1000
        total_investment = 7500000  # 750万元（1.5元/Wh）
        annual_days = 330

        # 容量租赁收入
        lease_rate = 300  # 元/kWh/年
        capacity_lease_revenue = installed_capacity_kwh * lease_rate

        # 峰谷套利收入
        daily_arbitrage = 800  # 元/天
        arbitrage_revenue = daily_arbitrage * annual_days

        # 辅助服务收入（调频）
        ancillary_daily = 200  # 元/天
        ancillary_service_revenue = ancillary_daily * annual_days

        # 总收入
        total_annual_revenue = capacity_lease_revenue + arbitrage_revenue + ancillary_service_revenue

        # 运营成本
        annual_opex = total_investment * 0.02  # 年运维成本 2%

        # 净收益
        annual_net_profit = total_annual_revenue - annual_opex

        # 投资回收期
        payback_period_years = round(total_investment / annual_net_profit, 1) if annual_net_profit > 0 else 99

        # 内部收益率 IRR（简化估算，假设 15 年寿命）
        total_lifetime_profit = annual_net_profit * 15 - total_investment
        irr = round((total_lifetime_profit / total_investment) / 15 * 100, 1)

        return {
            "basic_params": {
                "installed_capacity_kwh": installed_capacity_kwh,
                "installed_power_kw": installed_power_kw,
                "total_investment_cny": total_investment,
                "unit_cost_cny_per_wh": 1.5,
                "design_life_years": 15,
            },
            "revenue_breakdown": {
                "capacity_lease_revenue_cny": capacity_lease_revenue,
                "arbitrage_revenue_cny": arbitrage_revenue,
                "ancillary_service_revenue_cny": ancillary_service_revenue,
                "total_annual_revenue_cny": total_annual_revenue,
            },
            "cost_breakdown": {
                "annual_opex_cny": annual_opex,
                "annual_net_profit_cny": annual_net_profit,
            },
            "investment_metrics": {
                "payback_period_years": payback_period_years,
                "irr_percent": irr,
                "roi_percent": round(annual_net_profit / total_investment * 100, 1),
            },
            "recommendations": [
                "建议优先与园区内用电大户签订容量租赁协议，锁定基础收益",
                "参与电力现货市场，在电价尖峰时段提供调频服务获得额外收益",
                "结合光伏+储能模式，可申请国家新型储能示范项目补贴",
            ],
        }

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型: optimize / shared_storage_analysis",
                    "enum": ["optimize", "shared_storage_analysis"],
                },
                "current_soc": {
                    "type": "number",
                    "description": "当前储能 SOC (%)",
                },
                "electricity_price": {
                    "type": "object",
                    "description": "分时电价配置 {peak, flat, valley}",
                },
                "peak_hours": {
                    "type": "array",
                    "description": "峰时段小时列表",
                    "items": {"type": "integer"},
                },
            },
            "required": ["action"],
        }