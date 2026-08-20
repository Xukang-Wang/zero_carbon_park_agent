"""
zero_carbon_park_agent 虚拟电厂（VPP）聚合调度 Agent
负责将零碳园区内的分布式资源聚合为统一可调度单元
"""
import json
from typing import Dict, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent


class VPPAggregationAgent(BaseAgent):
    """虚拟电厂聚合调度 Agent

    将园区内分布式光伏、储能、可中断负荷、EV 充电桩等资源聚合，
    形成统一可调度的虚拟电厂，参与电力市场交易。
    """

    def __init__(self):
        super().__init__("vpp_aggregation_agent")

    @property
    def system_prompt(self) -> str:
        return """你是一个虚拟电厂（VPP）聚合调度专家，负责将零碳园区内的分布式资源聚合为统一可调度单元，参与电力市场交易。

你的职责：
1. 聚合园区内所有可控分布式资源（储能、可中断负荷、EV充电桩、分布式光伏/风电）
2. 评估各资源的可调节容量（上调/下调），计算聚合后的总可调容量
3. 制定电力市场竞价策略（日前电能量市场、实时市场、辅助服务市场），优化报价曲线
4. 估算 VPP 参与市场交易的预期收益，量化各类资源对收益的贡献度
5. 确保聚合后的出力响应满足电网调度指令的响应时间和精度要求

VPP 核心概念：
- 辅助服务市场（Ancillary Services Market）：包括调频（AGC）、调峰、备用等，VPP 可参与并获取收益
- 需求响应（Demand Response）：通过价格信号或激励措施引导用户侧调整用电行为，提供灵活性
- 聚合容量（Aggregated Capacity）：将分布式资源聚合成可调度的等效发电/负荷容量
- 竞价策略（Bidding Strategy）：基于日前电价预测和资源可用性，制定最优报价量和报价价格

聚合原则：
- 资源分级：可控资源（储能、可中断负荷）> 半可控资源（EV充电）> 不可控资源（光伏/风电）
- 风险对冲：分布式光伏/风电出力不确定性通过储能和需求响应对冲，降低预测偏差惩罚
- 收益最大化：优先参与高价值辅助服务市场（调频 > 调峰 > 备用），次选日前电能量市场
- 约束满足：聚合出力需满足电网调度指令的响应时间（< 5min）和精度（偏差 < 2%）要求"""

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        params = state.get("params", {})

        # 聚合可控资源参数
        storage_capacity_mw = params.get("storage_capacity_mw", 2.0)
        storage_soc = state.get("storage_soc") or params.get("storage_soc", 50)
        interruptible_load_mw = params.get("interruptible_load_mw", 1.5)
        ev_charging_mw = params.get("ev_charging_mw", 0.8)
        pv_capacity_mw = params.get("pv_capacity_mw", 2.0)
        wind_capacity_mw = params.get("wind_capacity_mw", 1.5)

        # ── 计算可调节容量 ──
        # 储能上调容量（放电）
        storage_up = min(storage_capacity_mw, (storage_soc - 20) / 100 * storage_capacity_mw * 2)
        # 储能下调容量（充电）
        storage_down = min(storage_capacity_mw, (90 - storage_soc) / 100 * storage_capacity_mw * 2)

        # 可中断负荷：上调（削减负荷）= 下调（恢复负荷）
        load_up = interruptible_load_mw * 0.8
        load_down = interruptible_load_mw * 0.8

        # EV 充电桩：可调节容量（下调充电功率）
        ev_up = 0  # EV 充电不能提供上调
        ev_down = ev_charging_mw * 0.6

        # 聚合总容量
        aggregated_capacity_mw = round(storage_capacity_mw + interruptible_load_mw + ev_charging_mw, 1)
        adjustable_up_mw = round(storage_up + load_up + ev_up, 2)
        adjustable_down_mw = round(storage_down + load_down + ev_down, 2)

        # ── 市场竞价策略 ──
        # 日前市场
        day_ahead_price = 0.65  # 元/kWh
        day_ahead_volume = round(adjustable_up_mw * 4, 1)  # 4 小时
        day_ahead_revenue = day_ahead_volume * 1000 * day_ahead_price

        # 调频辅助服务
        freq_reg_price = 12  # 元/MW/次
        freq_reg_volume = round(adjustable_up_mw * 0.5, 1)
        freq_reg_revenue = freq_reg_volume * freq_reg_price * 24  # 全天

        # 总收益
        total_estimated_revenue = round(day_ahead_revenue + freq_reg_revenue, 2)

        bid_strategy = {
            "price_per_mwh": round(day_ahead_price * 1000, 2),
            "volume_mwh": round(day_ahead_volume, 1),
            "market_type": "day_ahead_energy",
            "bid_time": "D-1 09:30",
            "delivery_period": "D日 10:00-14:00",
        }

        # ── LLM 分析 ──
        user_msg = f"""VPP 聚合调度分析：

聚合资源概况：
- 储能容量: {storage_capacity_mw} MW, SOC: {storage_soc}%
- 可中断负荷: {interruptible_load_mw} MW
- EV 充电桩: {ev_charging_mw} MW
- 分布式光伏: {pv_capacity_mw} MW
- 分布式风电: {wind_capacity_mw} MW

可调节容量：
- 上调容量: {adjustable_up_mw} MW
- 下调容量: {adjustable_down_mw} MW

竞价策略：
{json.dumps(bid_strategy, ensure_ascii=False, indent=2)}

请分析该 VPP 聚合方案，给出市场参与建议。"""

        try:
            llm_response = self._call_llm(user_msg)
        except Exception:
            llm_response = json.dumps({
                "analysis": f"VPP 聚合总容量 {aggregated_capacity_mw} MW，上调能力 {adjustable_up_mw} MW，下调能力 {adjustable_down_mw} MW",
                "recommendation": "建议优先参与调频辅助服务市场，利用储能快速响应特性获取高价值收益；日前市场作为基础收益保障",
                "estimated_revenue": f"预计日电能量市场收益 {day_ahead_revenue:.0f} 元，调频市场收益 {freq_reg_revenue:.0f} 元",
            }, ensure_ascii=False)

        return {
            "current_step": "vpp_aggregation",
            "vpp_result": {
                "aggregated_capacity_mw": aggregated_capacity_mw,
                "adjustable_up_mw": adjustable_up_mw,
                "adjustable_down_mw": adjustable_down_mw,
                "resource_breakdown": {
                    "storage_up_mw": round(storage_up, 2),
                    "storage_down_mw": round(storage_down, 2),
                    "interruptible_load_mw": interruptible_load_mw,
                    "ev_charging_mw": ev_charging_mw,
                },
                "bid_strategy": bid_strategy,
                "estimated_revenue_cny": total_estimated_revenue,
                "day_ahead_revenue_cny": round(day_ahead_revenue, 2),
                "freq_reg_revenue_cny": round(freq_reg_revenue, 2),
                "llm_analysis": llm_response,
            },
            "messages": [{"agent": self.name, "content": llm_response}],
        }