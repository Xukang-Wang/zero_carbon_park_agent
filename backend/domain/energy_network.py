"""
微电网/能源网络领域模型 - 电力总线、潮流计算、源网荷储协调
"""
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class BusType(Enum):
    SLACK = "slack"         # 平衡节点
    PV_BUS = "pv_bus"       # PV节点
    PQ_BUS = "pq_bus"       # PQ节点


@dataclass
class PowerBus:
    """电力总线 - 微电网中的一个节点"""
    id: str
    name: str
    bus_type: BusType = BusType.PQ_BUS
    voltage_kv: float = 10.0
    voltage_pu: float = 1.0      # 标幺值
    angle_deg: float = 0.0
    
    # 注入功率 (正=注入, 负=消耗)
    p_injection_kw: float = 0.0
    q_injection_kvar: float = 0.0
    
    # 连接设备
    connected_sources: List[str] = field(default_factory=list)
    connected_loads: List[str] = field(default_factory=list)
    connected_storage: List[str] = field(default_factory=list)
    
    @property
    def net_power_kw(self) -> float:
        return self.p_injection_kw
    
    def get_status(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "voltage_kv": self.voltage_kv,
            "voltage_pu": round(self.voltage_pu, 4),
            "angle_deg": round(self.angle_deg, 2),
            "p_injection_kw": round(self.p_injection_kw, 1),
            "q_injection_kvar": round(self.q_injection_kvar, 1),
            "sources": self.connected_sources,
            "loads": self.connected_loads,
            "storage": self.connected_storage,
        }


@dataclass
class MicroGrid:
    """微电网 - 园区能源网络的核心"""
    id: str
    name: str
    voltage_level_kv: float = 10.0
    frequency_hz: float = 50.0
    
    # 功率平衡
    total_generation_kw: float = 0.0
    total_load_kw: float = 0.0
    total_storage_power_kw: float = 0.0  # 正=充电，负=放电
    net_grid_power_kw: float = 0.0       # 正=购电，负=售电
    
    # 可再生占比
    renewable_generation_kw: float = 0.0
    renewable_ratio: float = 0.0
    
    # 碳排放
    carbon_emission_tco2_per_h: float = 0.0
    
    # 运行状态
    is_islanded: bool = False
    status: str = "normal"
    
    buses: List[PowerBus] = field(default_factory=list)
    
    @property
    def power_balance(self) -> float:
        """功率平衡偏差 (应接近0)"""
        return self.total_generation_kw + self.net_grid_power_kw - self.total_load_kw - self.total_storage_power_kw
    
    @property
    def is_balanced(self) -> bool:
        return abs(self.power_balance) < 10.0
    
    @property
    def self_sufficiency_ratio(self) -> float:
        """自给自足率"""
        if self.total_load_kw <= 0:
            return 1.0
        return min(1.0, self.total_generation_kw / self.total_load_kw)
    
    def update_power_balance(self, generation_kw: float, load_kw: float,
                              storage_power_kw: float, grid_power_kw: float):
        """更新功率平衡"""
        self.total_generation_kw = generation_kw
        self.total_load_kw = load_kw
        self.total_storage_power_kw = storage_power_kw
        self.net_grid_power_kw = grid_power_kw
        
        # 计算可再生占比
        self.renewable_ratio = (self.renewable_generation_kw / generation_kw
                                if generation_kw > 0 else 0)
    
    def get_status_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "voltage_kv": self.voltage_level_kv,
            "frequency_hz": self.frequency_hz,
            "total_generation_kw": round(self.total_generation_kw, 1),
            "total_load_kw": round(self.total_load_kw, 1),
            "total_storage_power_kw": round(self.total_storage_power_kw, 1),
            "net_grid_power_kw": round(self.net_grid_power_kw, 1),
            "power_balance": round(self.power_balance, 1),
            "is_balanced": self.is_balanced,
            "renewable_ratio": round(self.renewable_ratio * 100, 1),
            "self_sufficiency_ratio": round(self.self_sufficiency_ratio * 100, 1),
            "carbon_emission_tco2_per_h": round(self.carbon_emission_tco2_per_h, 4),
            "is_islanded": self.is_islanded,
            "status": self.status,
            "bus_count": len(self.buses),
            "buses": [b.get_status() for b in self.buses],
        }