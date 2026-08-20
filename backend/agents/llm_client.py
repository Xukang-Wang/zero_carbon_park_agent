"""
zero_carbon_park_agent LLM 客户端（云端 API）
基于 OpenAI 兼容接口，支持 GPT、DeepSeek 等模型
"""
import json
import logging
import time
from typing import List, Dict, Optional, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)


class LLMClient:
    """云端 LLM 客户端

    使用 OpenAI 兼容 API，支持 Function Calling。
    用户需在 .env 中配置 API Key 和 Base URL。
    """

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None,
                 timeout: int = 30, max_retries: int = 2):
        self.api_key = api_key or LLM_API_KEY
        self.base_url = base_url or LLM_BASE_URL
        self.model = model or LLM_MODEL
        self.timeout = timeout
        self.max_retries = max_retries

    def _get_client(self):
        """获取 OpenAI 客户端"""
        try:
            from openai import OpenAI
            return OpenAI(api_key=self.api_key, base_url=self.base_url)
        except ImportError:
            raise ImportError("请安装 openai: pip install openai")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3,
             max_tokens: int = 2000) -> str:
        """基础对话（带重试和超时）"""
        client = self._get_client()
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self.timeout,
                )
                return response.choices[0].message.content
            except Exception as e:
                last_error = e
                logger.warning(f"LLM chat API call failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
        raise last_error

    def chat_with_tools(self, messages: List[Dict[str, str]],
                        tools: List[Dict[str, Any]],
                        temperature: float = 0.3) -> Dict:
        """带 Function Calling 的对话"""
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            temperature=temperature,
            tool_choice="auto",
        )
        return response.choices[0].message

    def is_configured(self) -> bool:
        """检查 API Key 是否已配置"""
        return self.api_key and self.api_key != "your-api-key-here"


# 全局 LLM 客户端
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取 LLM 客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


class MockLLMClient:
    """模拟 LLM 客户端（无 API Key 时使用）

    当用户未配置 API Key 时，返回预设的模拟响应，
    确保项目可以完整运行和演示。
    """

    @staticmethod
    def chat(messages: List[Dict[str, str]], **kwargs) -> str:
        """根据消息内容返回模拟响应"""
        last_msg = messages[-1]["content"] if messages else ""

        if "异常检测" in last_msg:
            return MockLLMClient._anomaly_detection_response(last_msg)
        elif "根因分析" in last_msg or "root cause" in last_msg.lower():
            return MockLLMClient._root_cause_response(last_msg)
        elif "能源调度" in last_msg or "多能互补" in last_msg:
            return MockLLMClient._energy_dispatch_response(last_msg)
        elif "储能优化" in last_msg or "storage optimization" in last_msg.lower():
            return MockLLMClient._storage_optimization_response(last_msg)
        elif "调度决策" in last_msg or "dispatch" in last_msg.lower():
            return MockLLMClient._dispatch_response(last_msg)
        elif "任务派发" in last_msg or "task assignment" in last_msg.lower():
            return MockLLMClient._task_assignment_response(last_msg)
        elif "碳资产" in last_msg or "carbon asset" in last_msg.lower():
            return MockLLMClient._carbon_asset_response(last_msg)
        elif "查询" in last_msg or "问答" in last_msg:
            return MockLLMClient._nl_query_response(last_msg)
        elif "节能" in last_msg or "industrial energy" in last_msg.lower():
            return MockLLMClient._industrial_energy_response(last_msg)
        elif "虚拟电厂" in last_msg or "VPP" in last_msg:
            return MockLLMClient._vpp_response(last_msg)
        elif "报告" in last_msg or "report" in last_msg.lower():
            return MockLLMClient._report_response(last_msg)
        else:
            return MockLLMClient._default_response(last_msg)

    @staticmethod
    def _anomaly_detection_response(msg: str) -> str:
        return json.dumps({
            "anomaly_detected": True,
            "anomaly_type": "cod_exceeded",
            "description": "COD 预测值将在未来6小时内超过阈值(300 mg/L)，当前预测值为320.5 mg/L",
            "severity": "critical",
            "predicted_value": 320.5,
            "threshold": 300.0,
            "predicted_time": "未来6小时",
            "recommendation": "建议立即触发根因分析",
        }, ensure_ascii=False)

    @staticmethod
    def _root_cause_response(msg: str) -> str:
        return json.dumps({
            "root_cause": "1号生产线在过去2小时内排放负荷增加35%，导致COD浓度上升",
            "related_entities": ["LOAD-001", "TRANS-001", "WWTP-001"],
            "historical_match": "该模式与2025年7月15日发生的异常事件相似度85%，当时处置方案为：降低厌氧罐进料速率20%",
            "upstream_sources": [
                {"entity": "1号生产线", "contribution": "65%", "current_load_kw": 2100},
                {"entity": "2号生产线", "contribution": "25%", "current_load_kw": 1700},
            ],
            "carbon_impact": "该异常预计增加碳排放0.5 tCO₂",
        }, ensure_ascii=False)

    @staticmethod
    def _dispatch_response(msg: str) -> str:
        return json.dumps({
            "dispatch_plan": {
                "actions": [
                    {"action": "调节厌氧罐进料速率", "detail": "降低20%，从800 m³/h降至640 m³/h", "priority": "high"},
                    {"action": "启动备用曝气风机", "detail": "提升DO至3.5 mg/L以上", "priority": "high"},
                    {"action": "通知1号生产线", "detail": "建议调整排放速率，减少高峰排放", "priority": "medium"},
                ],
                "estimated_recovery_time_h": 4,
                "human_approval_required": True,
                "reason": "异常等级为 critical，涉及多部门协调，需人工确认处置方案",
            },
        }, ensure_ascii=False)

    @staticmethod
    def _task_assignment_response(msg: str) -> str:
        return json.dumps({
            "task_id": "TASK-20250806-001",
            "assignee": "环保部-运维组",
            "priority": "P0",
            "deadline": "2小时内",
            "notification_sent": True,
            "notification_channel": "simulated_feishu",
        }, ensure_ascii=False)

    @staticmethod
    def _report_response(msg: str) -> str:
        return """# 水质异常处置报告

## 事件概述
- **事件类型**: 水质异常 - COD 超标
- **检测时间**: 2025-08-06 14:30:00
- **严重程度**: ⚠️ Critical
- **预测值**: COD 320.5 mg/L（阈值 300.0 mg/L）

## 根因分析
1号生产线在过去2小时内排放负荷增加35%，导致进水COD浓度持续上升。
该模式与2025年7月15日异常事件相似度85%。

## 处置方案
1. **调节厌氧罐进料速率**: 降低20%，从800 m³/h降至640 m³/h
2. **启动备用曝气风机**: 提升DO至3.5 mg/L以上
3. **通知1号生产线**: 建议调整排放速率，减少高峰排放

## 预计影响
- 恢复时间: 约4小时
- 碳排放影响: +0.5 tCO₂
- 甲烷回收影响: 短期降低15%

## 后续跟进
- 持续监控COD变化趋势
- 2小时后评估处置效果
- 记录至知识库用于后续案例匹配

---
*报告由 zero_carbon_park_agent 报告生成 Agent 自动生成*
"""

    @staticmethod
    def _energy_dispatch_response(msg: str) -> str:
        return json.dumps({
            "dispatch_plan": {
                "strategy": "多能互补优化调度",
                "actions": [
                    {
                        "device": "PV-001",
                        "action": "满发运行",
                        "power_setpoint_kw": 4200,
                        "reason": "当前光照充足，优先消纳光伏电力",
                    },
                    {
                        "device": "BAT-001",
                        "action": "充电",
                        "power_setpoint_kw": 1800,
                        "reason": "光伏余电存储，SOC当前45%，目标75%",
                    },
                    {
                        "device": "GRID-001",
                        "action": "降功率",
                        "power_setpoint_kw": 2000,
                        "reason": "光伏出力充足，降低外购电力比例",
                    },
                    {
                        "device": "WWTP-001",
                        "action": "维持运行",
                        "power_setpoint_kw": 1200,
                        "reason": "污水处理不可中断，按需运行",
                    },
                ],
                "renewable_ratio_target": 0.72,
                "expected_carbon_reduction_tco2": 3.5,
                "economic_benefit_cny": 2800,
            },
        }, ensure_ascii=False)

    @staticmethod
    def _storage_optimization_response(msg: str) -> str:
        return json.dumps({
            "storage_optimization": {
                "current_soc_pct": 45.0,
                "charging_plan": [
                    {"time": "09:00-12:00", "action": "充电", "power_kw": 1800, "target_soc": 75},
                    {"time": "12:00-14:00", "action": "静置", "power_kw": 0, "target_soc": 75},
                    {"time": "14:00-17:00", "action": "充电", "power_kw": 1200, "target_soc": 90},
                    {"time": "17:00-22:00", "action": "放电", "power_kw": 2000, "target_soc": 30},
                ],
                "peak_shaving_power_kw": 2000,
                "daily_arbitrage_revenue_cny": 1500,
                "cycle_degradation_cost_cny": 120,
                "net_daily_revenue_cny": 1380,
                "strategy": "谷电充电、峰电放电，最大化峰谷价差收益",
            },
        }, ensure_ascii=False)

    @staticmethod
    def _carbon_asset_response(msg: str) -> str:
        return json.dumps({
            "carbon_asset_analysis": {
                "summary": "园区碳资产管理现状良好，碳配额盈余5000吨，建议在碳价高位分批卖出",
                "scope_emissions": {
                    "scope1": 109500.0,
                    "scope2": 396828.0,
                    "scope3": 138889.8,
                    "net_total": 442886.3,
                },
                "asset_portfolio": {
                    "carbon_quota_value_cny": 4000000,
                    "ccer_value_cny": 975000,
                    "green_cert_value_cny": 400000,
                    "total_cny": 5375000,
                },
                "trading_strategy": {
                    "current_position": "盈余",
                    "recommended_action": "sell",
                    "optimal_volume_tco2": 3500,
                    "expected_price_range": "72 - 88 元/吨",
                },
                "cbam_status": "当前出口产品嵌入碳排放可控，需持续跟踪EU ETS价格走势",
                "recommendations": [
                    "建议在碳价80元以上分批卖出3500吨碳配额",
                    "CCER价格较低，暂不建议出售，等待政策利好",
                    "加快开发分布式光伏CCER项目，增加碳资产来源",
                ],
            },
        }, ensure_ascii=False)

    @staticmethod
    def _nl_query_response(msg: str) -> str:
        return json.dumps({
            "response": "根据当前园区数据，您的查询结果如下：\n\n"
                       "**碳排放概况**：园区年碳排放总量约64.5万吨CO₂，其中Scope 1直接排放10.95万吨，"
                       "Scope 2间接排放39.68万吨，可再生能源占比约41.2%。\n\n"
                       "**零碳评价**：园区综合评分85.0分，已达到零碳园区标准，"
                       "各项指标基本达标，建议继续提升可再生能源占比。\n\n"
                       "**新能源运行**：光伏电站当前出力3500kW，预计今日发电量28000kWh；"
                       "风电出力约1200kW，预计今日发电量28800kWh。\n\n"
                       "**碳资产**：碳资产组合价值约537.5万元，碳配额盈余5000吨，建议在碳价高位优化交易策略。\n\n"
                       "如需更详细的分析，请告诉我具体关注的方向。",
            "status": "success",
        }, ensure_ascii=False)

    @staticmethod
    def _industrial_energy_response(msg: str) -> str:
        return json.dumps({
            "industrial_energy_audit": {
                "summary": "工业节能审计完成，发现4项改造机会，总节能潜力185.6万kWh/年，年节约费用约148万元",
                "audit_items": [
                    {
                        "item": "电机系统",
                        "current_status": "IE3电机，平均效率88%",
                        "improvement": "更换IE5超高效电机，效率提升至95%",
                        "annual_saving_kwh": 112000,
                        "annual_saving_cny": 89600,
                        "investment_cny": 1600000,
                        "payback_years": 1.79,
                    },
                    {
                        "item": "废热回收",
                        "current_status": "600kW废热未利用",
                        "improvement": "安装ORC余热发电机组",
                        "annual_saving_kwh": 432000,
                        "annual_saving_cny": 259200,
                        "investment_cny": 3000000,
                        "payback_years": 1.16,
                    },
                    {
                        "item": "VFD变频",
                        "current_status": "泵组工频运行",
                        "improvement": "加装变频器，节电25%",
                        "annual_saving_kwh": 160000,
                        "annual_saving_cny": 128000,
                        "investment_cny": 960000,
                        "payback_years": 0.75,
                    },
                    {
                        "item": "压缩空气",
                        "current_status": "泄漏率20%",
                        "improvement": "检测修复泄漏点",
                        "annual_saving_kwh": 64000,
                        "annual_saving_cny": 51200,
                        "investment_cny": 50000,
                        "payback_years": 0.98,
                    },
                ],
                "total_annual_saving_kwh": 1856000,
                "total_annual_saving_cny": 1484800,
                "total_carbon_reduction_tco2": 1078.3,
                "recommended_priority": ["VFD变频", "压缩空气泄漏治理", "废热回收", "高效电机更换"],
            },
        }, ensure_ascii=False)

    @staticmethod
    def _vpp_response(msg: str) -> str:
        return json.dumps({
            "vpp_optimization": {
                "aggregated_capacity_kw": 12000,
                "dispatchable_resources": [
                    {"type": "光伏", "capacity_kw": 5000, "current_output_kw": 3500, "curtailable": True},
                    {"type": "风电", "capacity_kw": 3000, "current_output_kw": 1800, "curtailable": False},
                    {"type": "储能", "capacity_kw": 2500, "soc_pct": 65, "available_kw": 2000},
                    {"type": "需求响应", "capacity_kw": 1500, "available_kw": 800},
                ],
                "grid_service_plan": {
                    "peak_shaving": {"power_kw": 3000, "duration_h": 2, "revenue_cny": 4500},
                    "frequency_regulation": {"power_kw": 500, "revenue_cny": 1200},
                    "demand_response": {"power_kw": 800, "revenue_cny": 2000},
                },
                "total_daily_revenue_cny": 7700,
                "strategy": "聚合分布式资源参与电力辅助服务市场，最大化VPP收益",
                "risk_note": "需关注现货市场价格波动，避免在负电价时段发电",
            },
        }, ensure_ascii=False)

    @staticmethod
    def _default_response(msg: str) -> str:
        return json.dumps({
            "response": "已收到您的请求，正在分析中...",
            "status": "acknowledged",
        }, ensure_ascii=False)