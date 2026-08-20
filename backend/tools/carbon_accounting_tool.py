"""
zero_carbon_park_agent 碳排放核算工具
供 Agent 进行碳排放核算、碳资产管理、CBAM 合规与碳交易策略
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


class CarbonAccountingTool(BaseTool):
    """碳排放核算工具

    支持 Scope 1/2/3 全覆盖碳排放核算、碳足迹计算、碳资产管理、
    CBAM 合规报告和碳交易策略推荐。
    """

    @property
    def name(self) -> str:
        return "carbon_accounting"

    @property
    def description(self) -> str:
        return (
            "碳排放核算工具，支持Scope 1/2/3全覆盖碳排放核算、碳足迹计算、碳资产管理。"
            "action 可选值: scope_emissions (Scope 1/2/3 核算), carbon_asset_value (碳资产估值), "
            "cbam_report (CBAM合规报告), carbon_trading_strategy (碳交易策略)"
        )

    def run(self, action: str = "scope_emissions", **kwargs) -> str:
        """碳排放核算与碳资产管理

        Args:
            action: 操作类型，可选 scope_emissions / carbon_asset_value / cbam_report / carbon_trading_strategy
            **kwargs: 各 action 对应的参数

        Returns:
            str: JSON 格式的碳排放核算结果或错误信息
        """
        valid_actions = ("scope_emissions", "carbon_asset_value", "cbam_report", "carbon_trading_strategy")
        if action not in valid_actions:
            return json.dumps({"error": f"无效 action: {action}，支持 {valid_actions}"}, ensure_ascii=False)

        logger.info(f"CarbonAccountingTool run: action={action}, kwargs={kwargs}")
        from graph.graph_builder import get_knowledge_graph

        try:
            kg = get_knowledge_graph()

            if action == "scope_emissions":
                result = kg.get_scope_emissions()
            elif action == "carbon_asset_value":
                result = self._calculate_carbon_asset_value(kwargs)
            elif action == "cbam_report":
                result = self._generate_cbam_report(kwargs)
            elif action == "carbon_trading_strategy":
                result = self._recommend_trading_strategy(kwargs)
            else:
                return json.dumps({"error": f"未知 action: {action}"}, ensure_ascii=False)

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"CarbonAccountingTool failed: {e}", exc_info=True)
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @staticmethod
    def _calculate_carbon_asset_value(kwargs: Dict) -> Dict:
        """计算碳资产组合价值"""
        carbon_quota = kwargs.get("carbon_quota", 50000)  # 吨
        ccer_holdings = kwargs.get("ccer_holdings", 15000)  # 吨
        green_certificates = kwargs.get("green_certificates", 8000)  # 张
        carbon_price = kwargs.get("carbon_price", 80.0)  # 元/吨CO₂
        ccer_price = kwargs.get("ccer_price", 65.0)  # 元/吨
        cert_price = kwargs.get("cert_price", 50.0)  # 元/张

        quota_value = carbon_quota * carbon_price
        ccer_value = ccer_holdings * ccer_price
        green_cert_value = green_certificates * cert_price
        total_asset_value = quota_value + ccer_value + green_cert_value

        return {
            "carbon_asset_portfolio": {
                "carbon_quota": {
                    "volume_tco2": carbon_quota,
                    "market_price_cny_per_ton": carbon_price,
                    "total_value_cny": round(quota_value, 2),
                },
                "ccer_holdings": {
                    "volume_tco2": ccer_holdings,
                    "market_price_cny_per_ton": ccer_price,
                    "total_value_cny": round(ccer_value, 2),
                },
                "green_certificates": {
                    "quantity": green_certificates,
                    "market_price_cny_per_cert": cert_price,
                    "total_value_cny": round(green_cert_value, 2),
                },
            },
            "total_asset_value_cny": round(total_asset_value, 2),
            "valuation_date": json.dumps({"note": "基于当前市场价格模拟"}),
        }

    @staticmethod
    def _generate_cbam_report(kwargs: Dict) -> Dict:
        """生成 CBAM 合规报告"""
        product_type = kwargs.get("product_type", "钢铁产品")
        embedded_emissions = kwargs.get("embedded_emissions", 1.85)  # tCO₂/吨产品
        eu_ets_price = kwargs.get("eu_ets_price", 75.0)  # 欧元/吨CO₂
        annual_export_volume = kwargs.get("annual_export_volume", 50000)  # 吨

        estimated_cbam_cost = embedded_emissions * eu_ets_price * annual_export_volume
        compliance_status = "需要购买CBAM证书" if estimated_cbam_cost > 500000 else "当前排放在豁免范围内"

        return {
            "cbam_report": {
                "product_type": product_type,
                "embedded_emissions_tco2_per_unit": embedded_emissions,
                "eu_ets_price_eur_per_tco2": eu_ets_price,
                "annual_export_volume_ton": annual_export_volume,
                "estimated_cbam_cost_eur": round(estimated_cbam_cost, 2),
                "estimated_cbam_cost_cny": round(estimated_cbam_cost * 7.8, 2),
                "compliance_status": compliance_status,
                "recommendation": "建议优化生产工艺降低嵌入碳排放，或采购绿电/CCER抵消部分排放",
            },
            "report_date": "2026",
        }

    @staticmethod
    def _recommend_trading_strategy(kwargs: Dict) -> Dict:
        """推荐碳交易策略"""
        current_quota = kwargs.get("current_quota", 50000)  # 吨
        actual_emissions = kwargs.get("actual_emissions", 45000)  # 吨
        market_price = kwargs.get("market_price", 80.0)  # 元/吨

        position = current_quota - actual_emissions
        if position > 0:
            current_position = "盈余"
            recommended_action = "sell"
            optimal_volume = round(position * 0.7, 0)  # 卖出 70% 盈余
            strategy_note = "当前碳配额盈余，建议在价格高位卖出部分配额获利"
        elif position < 0:
            current_position = "短缺"
            recommended_action = "buy"
            optimal_volume = abs(position)
            strategy_note = "当前碳配额不足，需在合规截止日前购买配额或CCER补足"
        else:
            current_position = "平衡"
            recommended_action = "hold"
            optimal_volume = 0
            strategy_note = "当前碳配额与排放持平，建议观望市场变化"

        return {
            "trading_strategy": {
                "current_position": current_position,
                "position_volume_tco2": position,
                "current_market_price_cny": market_price,
                "recommended_action": recommended_action,
                "optimal_volume_tco2": optimal_volume,
                "expected_price_range": f"{round(market_price * 0.9, 0)} - {round(market_price * 1.1, 0)} 元/吨",
                "strategy_note": strategy_note,
                "risk_reminder": "碳市场价格波动较大，建议分批操作，避免一次性大额交易",
            },
        }

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型: scope_emissions / carbon_asset_value / cbam_report / carbon_trading_strategy",
                    "enum": ["scope_emissions", "carbon_asset_value", "cbam_report", "carbon_trading_strategy"],
                },
                "carbon_quota": {"type": "number", "description": "碳配额量（吨）"},
                "ccer_holdings": {"type": "number", "description": "CCER持有量（吨）"},
                "green_certificates": {"type": "number", "description": "绿证数量（张）"},
                "carbon_price": {"type": "number", "description": "碳配额市场价（元/吨）"},
                "product_type": {"type": "string", "description": "CBAM产品类型"},
                "embedded_emissions": {"type": "number", "description": "嵌入碳排放（tCO₂/吨）"},
                "eu_ets_price": {"type": "number", "description": "EU ETS价格（欧元/吨）"},
                "actual_emissions": {"type": "number", "description": "实际排放量（吨）"},
            },
            "required": ["action"],
        }