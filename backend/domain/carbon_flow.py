"""
碳流追踪领域模型 - 碳排放核算、碳流路径、碳足迹
"""
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class ScopeType(Enum):
    SCOPE_1 = "scope_1"  # 直接排放
    SCOPE_2 = "scope_2"  # 间接排放（外购电力）
    SCOPE_3 = "scope_3"  # 其他间接排放


@dataclass
class CarbonFlowTracker:
    """碳流追踪器 - 核算园区碳排放全生命周期"""
    grid_emission_factor: float = 0.581  # tCO₂/MWh （2023中国电网平均）
    
    # Scope 1 直接排放
    direct_emission_tco2: float = 0.0
    direct_emission_sources: Dict[str, float] = field(default_factory=dict)
    
    # Scope 2 间接排放
    indirect_emission_tco2: float = 0.0
    purchased_electricity_mwh: float = 0.0
    
    # Scope 3 其他间接排放
    scope3_emission_tco2: float = 0.0
    scope3_ratio: float = 0.35  # 估算为Scope2的35%
    
    # 碳抵消
    carbon_offset_tco2: float = 0.0
    renewable_generation_mwh: float = 0.0
    
    # 碳资产
    carbon_quota_tco2: float = 5000.0      # 碳配额
    ccer_holding_tco2: float = 2000.0      # CCER持有量
    green_certificate_mwh: float = 10000.0  # 绿证持有量
    
    # 价格
    carbon_price_yuan: float = 60.0        # 碳价 元/吨
    ccer_price_yuan: float = 50.0
    green_cert_price_yuan: float = 25.0    # 元/MWh
    
    @property
    def total_emission_tco2(self) -> float:
        """总排放量"""
        self.scope3_emission_tco2 = self.indirect_emission_tco2 * self.scope3_ratio
        return self.direct_emission_tco2 + self.indirect_emission_tco2 + self.scope3_emission_tco2
    
    @property
    def net_emission_tco2(self) -> float:
        """净排放量 = 总排放 - 碳抵消"""
        return max(0, self.total_emission_tco2 - self.carbon_offset_tco2)
    
    @property
    def emission_intensity(self) -> float:
        """碳排放强度 tCO₂/MWh"""
        total_gen = self.purchased_electricity_mwh + self.renewable_generation_mwh
        if total_gen <= 0:
            return 0
        return self.total_emission_tco2 / total_gen
    
    @property
    def compliance_gap_tco2(self) -> float:
        """履约缺口"""
        return self.total_emission_tco2 - self.carbon_quota_tco2
    
    @property
    def is_compliant(self) -> bool:
        return self.compliance_gap_tco2 <= 0
    
    def compute_indirect_emission(self, grid_power_mwh: float) -> float:
        """计算外购电力的间接排放"""
        self.purchased_electricity_mwh = grid_power_mwh
        self.indirect_emission_tco2 = grid_power_mwh * self.grid_emission_factor
        return self.indirect_emission_tco2
    
    def compute_carbon_offset(self, renewable_mwh: float) -> float:
        """计算可再生能源碳抵消"""
        self.renewable_generation_mwh = renewable_mwh
        self.carbon_offset_tco2 = renewable_mwh * self.grid_emission_factor
        return self.carbon_offset_tco2
    
    def get_scope_breakdown(self) -> Dict:
        """获取Scope 1/2/3 分项"""
        total = self.total_emission_tco2
        return {
            "scope_1": {
                "emission_tco2": round(self.direct_emission_tco2, 2),
                "ratio": round(self.direct_emission_tco2 / total * 100, 1) if total > 0 else 0,
                "sources": self.direct_emission_sources,
            },
            "scope_2": {
                "emission_tco2": round(self.indirect_emission_tco2, 2),
                "ratio": round(self.indirect_emission_tco2 / total * 100, 1) if total > 0 else 0,
                "purchased_electricity_mwh": round(self.purchased_electricity_mwh, 2),
                "grid_factor": self.grid_emission_factor,
            },
            "scope_3": {
                "emission_tco2": round(self.scope3_emission_tco2, 2),
                "ratio": round(self.scope3_emission_tco2 / total * 100, 1) if total > 0 else 0,
                "estimation_method": f"Scope2的{round(self.scope3_ratio * 100)}%",
            },
            "total_tco2": round(total, 2),
            "carbon_offset_tco2": round(self.carbon_offset_tco2, 2),
            "net_emission_tco2": round(self.net_emission_tco2, 2),
        }
    
    def get_carbon_asset_summary(self) -> Dict:
        """碳资产汇总"""
        return {
            "carbon_quota": {
                "holding_tco2": self.carbon_quota_tco2,
                "value_yuan": round(self.carbon_quota_tco2 * self.carbon_price_yuan, 2),
                "unit_price": self.carbon_price_yuan,
            },
            "ccer": {
                "holding_tco2": self.ccer_holding_tco2,
                "value_yuan": round(self.ccer_holding_tco2 * self.ccer_price_yuan, 2),
                "unit_price": self.ccer_price_yuan,
            },
            "green_certificate": {
                "holding_mwh": self.green_certificate_mwh,
                "value_yuan": round(self.green_certificate_mwh * self.green_cert_price_yuan, 2),
                "unit_price": self.green_cert_price_yuan,
            },
            "compliance": {
                "gap_tco2": round(self.compliance_gap_tco2, 2),
                "is_compliant": self.is_compliant,
                "recommendation": "配额充足，可出售盈余" if self.compliance_gap_tco2 < -1000
                else "配额紧张，需采购CCER" if self.compliance_gap_tco2 > 0
                else "配额基本平衡",
            },
        }