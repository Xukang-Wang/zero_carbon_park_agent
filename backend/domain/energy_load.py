"""
负荷侧领域模型 - 工业负荷、柔性负荷、可中断负荷、可转移负荷
"""
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class LoadType(Enum):
    """负荷类型"""
    CRITICAL = "critical"           # 关键负荷 - 不可中断
    MANUFACTURING = "manufacturing"  # 生产负荷
    HVAC = "hvac"                   # 暖通空调
    LIGHTING = "lighting"           # 照明
    EV_CHARGING = "ev_charging"     # 充电桩
    WWTP = "wastewater_treatment"   # 污水处理
    DATA_CENTER = "data_center"     # 数据中心
    OFFICE = "office"               # 办公用电


class LoadFlexibility(Enum):
    """负荷柔性等级"""
    FIXED = "fixed"                 # 固定负荷，不可调节
    SHIFTABLE = "shiftable"         # 可转移负荷（时间平移）
    CURTAILABLE = "curtailable"     # 可削减负荷
    FLEXIBLE = "flexible"           # 完全柔性负荷


@dataclass
class EnergyLoad:
    """能源负荷单元 - 含柔性调节能力建模"""
    id: str
    name: str
    load_type: LoadType
    flexibility: LoadFlexibility = LoadFlexibility.FIXED
    rated_power_kw: float = 1000.0
    current_power_kw: float = 0.0
    department: str = ""
    
    # 柔性参数
    min_power_kw: float = 0.0       # 最小运行功率
    max_power_kw: float = 1000.0    # 最大运行功率
    ramp_rate_kw_per_min: float = 100.0  # 爬坡率
    min_runtime_h: float = 1.0      # 最短运行时间
    min_downtime_h: float = 0.5     # 最短停机时间
    shift_window_h: float = 4.0    # 可转移时间窗口
    curtailment_cost: float = 0.5   # 削减成本 元/kWh
    
    # 碳排放
    carbon_intensity_kg_per_kwh: float = 0.0  # 单位用电碳排放
    
    # 运行状态
    status: str = "online"
    uptime_h: float = 0.0
    downtime_h: float = 0.0
    
    # 温度敏感参数（HVAC用）
    temp_setpoint_c: float = 24.0
    temp_deadband_c: float = 2.0
    
    # 生产计划（制造负荷用）
    production_schedule: List[Dict] = field(default_factory=list)
    
    def can_shift(self, hours: float) -> bool:
        """是否可以转移 hours 小时"""
        return (self.flexibility in [LoadFlexibility.SHIFTABLE, LoadFlexibility.FLEXIBLE]
                and hours <= self.shift_window_h)
    
    def can_curtail(self, power_kw: float) -> bool:
        """是否可以削减 power_kw"""
        if self.flexibility not in [LoadFlexibility.CURTAILABLE, LoadFlexibility.FLEXIBLE]:
            return False
        return (self.current_power_kw - power_kw) >= self.min_power_kw
    
    def compute_demand_response_capacity(self) -> float:
        """计算需求响应可调容量"""
        if self.flexibility == LoadFlexibility.FIXED:
            return 0.0
        elif self.flexibility == LoadFlexibility.SHIFTABLE:
            return self.current_power_kw * 0.5
        elif self.flexibility == LoadFlexibility.CURTAILABLE:
            return max(0, self.current_power_kw - self.min_power_kw)
        elif self.flexibility == LoadFlexibility.FLEXIBLE:
            return self.current_power_kw * 0.8
        return 0.0
    
    def simulate_hourly_profile(self, date: datetime, base_power: float = None) -> List[Dict]:
        """模拟24小时负荷曲线"""
        if base_power is None:
            base_power = self.rated_power_kw * 0.7
        
        profile = []
        for hour in range(24):
            time_label = (date + timedelta(hours=hour)).strftime("%H:00")
            
            if self.load_type == LoadType.MANUFACTURING:
                # 制造负荷：8-18点高，夜间低
                if 8 <= hour < 18:
                    factor = 0.85 + 0.15 * np.sin(np.pi * (hour - 8) / 10)
                elif 18 <= hour < 22:
                    factor = 0.5
                else:
                    factor = 0.2
            elif self.load_type == LoadType.HVAC:
                # HVAC：随室外温度变化
                outdoor_temp = 25 + 10 * np.sin(np.pi * (hour - 14) / 12)
                cooling_demand = max(0, (outdoor_temp - self.temp_setpoint_c) / 10)
                factor = 0.3 + 0.7 * cooling_demand
            elif self.load_type == LoadType.EV_CHARGING:
                # 充电桩：夜间和午间充电
                if 0 <= hour < 6 or 12 <= hour < 14:
                    factor = 0.8
                elif 8 <= hour < 11 or 18 <= hour < 21:
                    factor = 0.3
                else:
                    factor = 0.5
            elif self.load_type == LoadType.WWTP:
                # 污水处理厂：全天稳定运行
                factor = 0.75 + 0.1 * np.sin(np.pi * hour / 12)
            elif self.load_type == LoadType.DATA_CENTER:
                # 数据中心：几乎恒定
                factor = 0.9
            else:
                factor = 0.6 + 0.1 * np.sin(np.pi * hour / 12)
            
            power = round(base_power * factor, 1)
            profile.append({
                "time": time_label,
                "hour": hour,
                "power_kw": power,
                "load_factor": round(factor, 2),
                "flex_capacity_kw": round(power * 0.3 if self.flexibility != LoadFlexibility.FIXED else 0, 1),
            })
        
        return profile


@dataclass
class LoadCluster:
    """负荷集群 - 管理多个负荷单元"""
    id: str
    name: str
    loads: List[EnergyLoad] = field(default_factory=list)
    
    @property
    def total_power_kw(self) -> float:
        return sum(ld.current_power_kw for ld in self.loads)
    
    @property
    def total_rated_power_kw(self) -> float:
        return sum(ld.rated_power_kw for ld in self.loads)
    
    @property
    def total_demand_response_capacity_kw(self) -> float:
        """总需求响应容量"""
        return sum(ld.compute_demand_response_capacity() for ld in self.loads)
    
    @property
    def critical_load_kw(self) -> float:
        return sum(ld.current_power_kw for ld in self.loads
                   if ld.flexibility == LoadFlexibility.FIXED)
    
    @property
    def flexible_load_kw(self) -> float:
        return sum(ld.current_power_kw for ld in self.loads
                   if ld.flexibility != LoadFlexibility.FIXED)
    
    @property
    def renewable_ratio(self) -> float:
        """计算可再生能源占比（需外部设定）"""
        return 0.0
    
    def get_status_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "total_power_kw": round(self.total_power_kw, 1),
            "total_rated_power_kw": self.total_rated_power_kw,
            "demand_response_capacity_kw": round(self.total_demand_response_capacity_kw, 1),
            "critical_load_kw": round(self.critical_load_kw, 1),
            "flexible_load_kw": round(self.flexible_load_kw, 1),
            "load_count": len(self.loads),
            "loads": [
                {
                    "id": ld.id, "name": ld.name,
                    "type": ld.load_type.value,
                    "power_kw": round(ld.current_power_kw, 1),
                    "flexibility": ld.flexibility.value,
                    "dr_capacity_kw": round(ld.compute_demand_response_capacity(), 1),
                    "status": ld.status,
                }
                for ld in self.loads
            ],
        }