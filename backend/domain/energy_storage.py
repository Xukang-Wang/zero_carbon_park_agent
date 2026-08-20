"""
储能系统领域模型 - 电池储能、SOC管理、健康状态、循环寿命
"""
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class StorageType(Enum):
    LI_ION = "li_ion"
    NA_ION = "na_ion"
    FLOW_BATTERY = "flow_battery"
    LEAD_ACID = "lead_acid"
    FLYWHEEL = "flywheel"
    HYDROGEN = "hydrogen"


class StorageMode(Enum):
    IDLE = "idle"
    CHARGING = "charging"
    DISCHARGING = "discharging"
    STANDBY = "standby"


@dataclass
class BatteryStorage:
    """电池储能系统 - 含SOC、SOH、循环寿命、衰减模型"""
    id: str
    name: str
    capacity_kwh: float = 5000.0
    rated_power_kw: float = 2500.0
    storage_type: StorageType = StorageType.LI_ION
    
    # SOC 约束
    soc_min: float = 20.0          # 最低SOC %
    soc_max: float = 90.0          # 最高SOC %
    current_soc: float = 60.0      # 当前SOC %
    
    # 效率参数
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    self_discharge_rate: float = 0.0001  # 每小时自放电率
    
    # 健康状态
    soh: float = 95.0              # 健康状态 %
    cycle_count: int = 1200
    design_cycle_life: int = 6000
    current_temp_c: float = 28.0
    
    # 成本参数
    cycle_degradation_cost: float = 0.05  # 元/kWh/循环
    install_cost_per_kwh: float = 1500.0  # 元/kWh
    
    mode: StorageMode = StorageMode.IDLE
    current_power_kw: float = 0.0  # 正=充电，负=放电
    status: str = "online"
    
    @property
    def available_energy_kwh(self) -> float:
        """可用能量 kWh"""
        return self.capacity_kwh * self.current_soc / 100.0 * self.soh / 100.0
    
    @property
    def remaining_capacity_kwh(self) -> float:
        """剩余可充电容量"""
        return self.capacity_kwh * (self.soc_max - self.current_soc) / 100.0 * self.soh / 100.0
    
    @property
    def dischargeable_energy_kwh(self) -> float:
        """可放电能量"""
        return self.capacity_kwh * (self.current_soc - self.soc_min) / 100.0 * self.soh / 100.0
    
    @property
    def remaining_cycles(self) -> int:
        return max(0, self.design_cycle_life - self.cycle_count)
    
    @property
    def capacity_retention(self) -> float:
        """容量保持率"""
        return self.soh / 100.0
    
    def charge(self, power_kw: float, duration_h: float = 1.0) -> Dict:
        """充电操作
        
        Args:
            power_kw: 充电功率（正数）
            duration_h: 持续时间 h
        
        Returns:
            充电结果
        """
        power_kw = min(power_kw, self.rated_power_kw)
        max_charge = self.remaining_capacity_kwh / duration_h
        actual_power = min(power_kw, max_charge)
        
        energy_in = actual_power * duration_h * self.charge_efficiency
        soc_increase = energy_in / (self.capacity_kwh * self.soh / 100.0) * 100
        self.current_soc = min(self.soc_max, self.current_soc + soc_increase)
        
        self.current_power_kw = actual_power
        self.mode = StorageMode.CHARGING
        
        # 自放电
        self.current_soc -= self.self_discharge_rate * duration_h * 100
        
        return {
            "action": "charge",
            "power_kw": round(actual_power, 1),
            "energy_kwh": round(energy_in, 1),
            "soc_before": round(self.current_soc - soc_increase, 1),
            "soc_after": round(self.current_soc, 1),
            "efficiency": round(self.charge_efficiency * 100, 1),
            "degradation_cost": round(energy_in * self.cycle_degradation_cost, 2),
        }
    
    def discharge(self, power_kw: float, duration_h: float = 1.0) -> Dict:
        """放电操作
        
        Args:
            power_kw: 放电功率（正数）
            duration_h: 持续时间 h
        
        Returns:
            放电结果
        """
        power_kw = min(power_kw, self.rated_power_kw)
        max_discharge = self.dischargeable_energy_kwh / duration_h
        actual_power = min(power_kw, max_discharge)
        
        energy_out = actual_power * duration_h
        soc_decrease = energy_out / (self.capacity_kwh * self.soh / 100.0) * 100 / self.discharge_efficiency
        self.current_soc = max(self.soc_min, self.current_soc - soc_decrease)
        
        self.current_power_kw = -actual_power
        self.mode = StorageMode.DISCHARGING
        self.cycle_count += int(duration_h)
        
        # 更新SOH（简化线性衰减）
        cycle_ratio = self.cycle_count / self.design_cycle_life
        self.soh = max(70, 100 - cycle_ratio * 30)
        
        return {
            "action": "discharge",
            "power_kw": round(actual_power, 1),
            "energy_kwh": round(energy_out, 1),
            "soc_before": round(self.current_soc + soc_decrease, 1),
            "soc_after": round(self.current_soc, 1),
            "efficiency": round(self.discharge_efficiency * 100, 1),
            "degradation_cost": round(energy_out * self.cycle_degradation_cost, 2),
        }
    
    def idle(self):
        """待机状态"""
        self.current_power_kw = 0.0
        self.mode = StorageMode.IDLE
        self.current_soc -= self.self_discharge_rate * 100
    
    def get_status_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.storage_type.value,
            "capacity_kwh": self.capacity_kwh,
            "rated_power_kw": self.rated_power_kw,
            "current_soc": round(self.current_soc, 1),
            "available_energy_kwh": round(self.available_energy_kwh, 1),
            "dischargeable_energy_kwh": round(self.dischargeable_energy_kwh, 1),
            "soh": round(self.soh, 1),
            "cycle_count": self.cycle_count,
            "remaining_cycles": self.remaining_cycles,
            "temp_c": self.current_temp_c,
            "mode": self.mode.value,
            "current_power_kw": round(self.current_power_kw, 1),
            "status": self.status,
            "lifetime_progress": round(self.cycle_count / self.design_cycle_life * 100, 1),
        }


@dataclass
class StorageBank:
    """储能电站 - 管理多个储能单元"""
    id: str
    name: str
    batteries: List[BatteryStorage] = field(default_factory=list)
    
    @property
    def total_capacity_kwh(self) -> float:
        return sum(b.capacity_kwh for b in self.batteries)
    
    @property
    def total_power_kw(self) -> float:
        return sum(b.rated_power_kw for b in self.batteries)
    
    @property
    def aggregate_soc(self) -> float:
        if not self.batteries:
            return 0.0
        capacities = [b.capacity_kwh for b in self.batteries]
        socs = [b.current_soc for b in self.batteries]
        total = sum(c * s for c, s in zip(capacities, socs))
        return total / sum(capacities) if sum(capacities) > 0 else 0.0
    
    @property
    def average_soh(self) -> float:
        if not self.batteries:
            return 100.0
        return sum(b.soh for b in self.batteries) / len(self.batteries)
    
    def get_status_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "total_capacity_kwh": self.total_capacity_kwh,
            "total_power_kw": self.total_power_kw,
            "aggregate_soc": round(self.aggregate_soc, 1),
            "average_soh": round(self.average_soh, 1),
            "unit_count": len(self.batteries),
            "units": [b.get_status_dict() for b in self.batteries],
        }