"""
zero_carbon_park_agent 工业节能 Agent
负责零碳园区工业设备的能效分析与节能改造建议
"""
import json
from typing import Dict, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent


class IndustrialEnergyAgent(BaseAgent):
    """工业节能 Agent

    负责工业设备能效分析、废热回收评估、变频优化建议等。
    使用内部模拟逻辑，无需注册外部工具。
    """

    def __init__(self):
        super().__init__("industrial_energy_agent")

    @property
    def system_prompt(self) -> str:
        return """你是一个工业节能专家，负责零碳园区工业设备的能效分析与节能改造建议。

你的职责：
1. 分析电机系统运行效率，评估 IE3/IE4/IE5 不同能效等级的节能潜力，给出电机更换建议
2. 评估废热回收潜力，按温度品位分级（高温 > 500℃、中温 200-500℃、低温 < 200℃）设计分级利用方案
3. 优化变频调速系统（VFD），降低泵和风机能耗，计算变频改造的节电率
4. 检测压缩空气系统泄漏率，评估泄漏损失（通常泄漏率 > 10% 即需治理），给出修复方案
5. 给出综合节能方案和投资回报分析，量化每项改造的年节能量和碳减排量

工业节能核心概念：
- 电机能效等级（IE Class）：IE3（Premium）、IE4（Super Premium）、IE5（Ultra Premium），每提升一级效率提升 2-4%
- 废热回收温度品位：高温（>500℃）可用于发电，中温（200-500℃）可用于工艺预热，低温（<200℃）可用于供暖/制冷
- 压缩空气泄漏率：行业平均水平 20-30%，优秀水平 < 10%，泄漏率每降低 10% 可节电 5-8%
- 变频调速（VFD）：离心泵/风机流量与转速成正比，功率与转速的三次方成正比，降速 20% 可节电约 50%

分析原则：
- 能效优先：优先采用高能效设备和系统优化，IE5 电机虽初始投资高但全生命周期成本最低
- 经济可行：确保节能改造投资回收期合理（< 3 年），优先实施投资回收期 < 1 年的措施
- 碳减排：量化每项改造的碳减排效果，折算为碳资产价值
- 可操作性：给出具体的设备选型和参数建议，注明适用工况条件"""

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # 工业节能审计模拟
        audit_result = self._simulate_energy_audit(state)

        # 构建 LLM 分析消息
        user_msg = f"""工业节能审计结果:
{json.dumps(audit_result, ensure_ascii=False, indent=2)}

请分析节能潜力，给出具体的改造建议。"""

        try:
            llm_response = self._call_llm(user_msg)
        except Exception:
            from agents.llm_client import MockLLMClient
            llm_response = MockLLMClient._industrial_energy_response("")

        return {
            "current_step": "industrial_energy_audit",
            "energy_saving_potential_kwh": audit_result["energy_saving_potential_kwh"],
            "motor_efficiency_analysis": audit_result["motor_efficiency_analysis"],
            "waste_heat_recovery_potential_kw": audit_result["waste_heat_recovery_potential_kw"],
            "vfd_saving_potential_kwh": audit_result["vfd_saving_potential_kwh"],
            "total_annual_saving_yuan": audit_result["total_annual_saving_yuan"],
            "recommended_actions": audit_result["recommended_actions"],
            "llm_analysis": llm_response,
            "messages": [{"agent": self.name, "content": llm_response}],
        }

    @staticmethod
    def _simulate_energy_audit(state: Dict[str, Any]) -> Dict:
        """模拟工业节能审计"""
        params = state.get("params", {})

        # 电机效率分析
        motor_power_kw = params.get("motor_power_kw", 2000.0)
        current_efficiency = params.get("current_efficiency", 0.88)
        optimal_efficiency = params.get("optimal_efficiency", 0.95)
        annual_hours = params.get("annual_hours", 8000.0)

        motor_saving = motor_power_kw * (optimal_efficiency - current_efficiency) * annual_hours
        motor_saving_cost = motor_saving * 0.8  # 元/kWh

        # 废热回收潜力
        waste_heat_source_power = params.get("waste_heat_source_power_kw", 1500.0)
        waste_heat_recovery_ratio = 0.40
        waste_heat_recoverable = waste_heat_source_power * waste_heat_recovery_ratio
        waste_heat_annual_saving = waste_heat_recoverable * annual_hours * 0.6  # 0.6元/kWh 热价

        # VFD 优化
        pump_power_kw = params.get("pump_power_kw", 800.0)
        vfd_saving_ratio = 0.25
        vfd_saving = pump_power_kw * vfd_saving_ratio * annual_hours
        vfd_saving_cost = vfd_saving * 0.8

        # 压缩空气泄漏
        compressor_power_kw = params.get("compressor_power_kw", 500.0)
        leak_rate = params.get("leak_rate", 0.20)
        leak_saving = compressor_power_kw * leak_rate * 0.8 * annual_hours
        leak_saving_cost = leak_saving * 0.8

        total_saving_kwh = motor_saving + vfd_saving + leak_saving
        total_saving_yuan = motor_saving_cost + waste_heat_annual_saving + vfd_saving_cost + leak_saving_cost

        recommended_actions = [
            {
                "action": "高效电机更换",
                "detail": f"将IE3电机更换为IE5超高效电机，效率从{current_efficiency*100:.0f}%提升至{optimal_efficiency*100:.0f}%",
                "annual_saving_kwh": round(motor_saving, 2),
                "annual_saving_yuan": round(motor_saving_cost, 2),
                "investment_yuan": round(motor_power_kw * 800, 2),
                "payback_years": round(motor_power_kw * 800 / motor_saving_cost, 2) if motor_saving_cost > 0 else 0,
                "carbon_reduction_tco2": round(motor_saving * 0.581 / 1000, 2),
            },
            {
                "action": "废热回收系统",
                "detail": f"安装ORC余热发电机组，回收{waste_heat_recoverable:.0f}kW废热",
                "annual_saving_kwh": round(waste_heat_recoverable * annual_hours * 0.18, 2),
                "annual_saving_yuan": round(waste_heat_annual_saving, 2),
                "investment_yuan": round(waste_heat_recoverable * 5000, 2),
                "payback_years": round(waste_heat_recoverable * 5000 / waste_heat_annual_saving, 2) if waste_heat_annual_saving > 0 else 0,
                "carbon_reduction_tco2": round(waste_heat_recoverable * annual_hours * 0.581 / 1000, 2),
            },
            {
                "action": "VFD变频改造",
                "detail": f"为{pump_power_kw:.0f}kW泵组加装变频器，预计节电{vfd_saving_ratio*100:.0f}%",
                "annual_saving_kwh": round(vfd_saving, 2),
                "annual_saving_yuan": round(vfd_saving_cost, 2),
                "investment_yuan": round(pump_power_kw * 1200, 2),
                "payback_years": round(pump_power_kw * 1200 / vfd_saving_cost, 2) if vfd_saving_cost > 0 else 0,
                "carbon_reduction_tco2": round(vfd_saving * 0.581 / 1000, 2),
            },
            {
                "action": "压缩空气泄漏治理",
                "detail": f"检测并修复压缩空气系统泄漏，泄漏率从{leak_rate*100:.0f}%降至5%",
                "annual_saving_kwh": round(leak_saving, 2),
                "annual_saving_yuan": round(leak_saving_cost, 2),
                "investment_yuan": 50000,
                "payback_years": round(50000 / leak_saving_cost, 2) if leak_saving_cost > 0 else 0,
                "carbon_reduction_tco2": round(leak_saving * 0.581 / 1000, 2),
            },
        ]

        return {
            "motor_efficiency_analysis": {
                "current_efficiency": current_efficiency,
                "optimal_efficiency": optimal_efficiency,
                "annual_saving_kwh": round(motor_saving, 2),
                "annual_saving_yuan": round(motor_saving_cost, 2),
            },
            "waste_heat_recovery_potential_kw": round(waste_heat_recoverable, 2),
            "vfd_saving_potential_kwh": round(vfd_saving, 2),
            "compressed_air_saving_kwh": round(leak_saving, 2),
            "energy_saving_potential_kwh": round(total_saving_kwh, 2),
            "total_annual_saving_yuan": round(total_saving_yuan, 2),
            "annual_carbon_reduction_tco2": round(total_saving_kwh * 0.581 / 1000, 2),
            "recommended_actions": recommended_actions,
        }