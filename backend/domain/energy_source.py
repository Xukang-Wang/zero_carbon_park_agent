"""
能源源端领域模型 - 光伏、风电、市电、生物质CHP等发电单元
基于物理建模，模拟真实出力特性
"""
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class SourceType(Enum):
    SOLAR = "solar"
    WIND = "wind"
    GRID = "grid"
    BIOMASS_CHP = "biomass_chp"
    HYDRO = "hydro"
    HYDROGEN = "hydrogen"


@dataclass
class PVSource:
    """光伏发电单元 - 基于辐照度和温度物理模型"""
    id: str
    name: str
    capacity_kw: float                          # 装机容量 kW
    area_m2: float = 0.0                        # 面板面积 m²
    efficiency_stc: float = 0.21                # STC下的转换效率
    temp_coefficient: float = -0.0035           # 温度系数 /°C
    tilt_angle: float = 30.0                    # 倾角 °
    azimuth: float = 180.0                      # 方位角 °（南=180）
    latitude: float = 31.2                      # 纬度
    longitude: float = 121.5                    # 经度
    degradation_rate: float = 0.005             # 年衰减率
    operational_years: float = 2.0              # 已运行年数
    status: str = "online"
    
    # 运行时状态
    current_power_kw: float = 0.0
    current_irradiance: float = 0.0             # W/m²
    current_temp_c: float = 25.0
    daily_generation_kwh: float = 0.0
    total_generation_kwh: float = 0.0
    
    @property
    def degraded_efficiency(self) -> float:
        return self.efficiency_stc * (1 - self.degradation_rate) ** self.operational_years
    
    def compute_power(self, irradiance_wm2: float, temp_c: float) -> float:
        """根据辐照度和温度计算光伏出力
        
        P = P_stc * G/G_stc * [1 + γ*(Tc - 25)]
        """
        if irradiance_wm2 <= 0:
            return 0.0
        
        temp_adjusted = self.capacity_kw * (irradiance_wm2 / 1000.0)
        temp_effect = 1 + self.temp_coefficient * (temp_c - 25)
        degradation = self.degraded_efficiency / self.efficiency_stc
        
        power = temp_adjusted * temp_effect * degradation
        return max(0.0, min(self.capacity_kw, power))
    
    def simulate_hourly_profile(self, date: datetime, cloud_cover: float = 0.2) -> List[Dict]:
        """模拟24小时光伏出力曲线"""
        profile = []
        day_of_year = date.timetuple().tm_yday
        
        for hour in range(24):
            # 太阳高度角简化计算
            hour_angle = (hour - 12) * 15  # 度
            declination = 23.45 * np.sin(np.radians(360 * (284 + day_of_year) / 365))
            lat_rad = np.radians(self.latitude)
            dec_rad = np.radians(declination)
            ha_rad = np.radians(hour_angle)
            
            elevation = np.arcsin(
                np.sin(lat_rad) * np.sin(dec_rad) +
                np.cos(lat_rad) * np.cos(dec_rad) * np.cos(ha_rad)
            )
            elevation_deg = np.degrees(elevation)
            
            if elevation_deg <= 0:
                irradiance = 0.0
            else:
                # 大气质量修正
                air_mass = 1 / max(np.sin(elevation), 0.1)
                irradiance = 1000 * np.sin(elevation) * np.exp(-0.1 * air_mass)
                irradiance *= (1 - cloud_cover)
                irradiance = max(0, irradiance)
            
            temp_c = 25 + 15 * np.sin(np.pi * (hour - 14) / 12) if hour >= 6 else 20
            time_label = (date + timedelta(hours=hour)).strftime("%H:00")
            power = round(self.compute_power(irradiance, temp_c), 1)
            
            profile.append({
                "time": time_label,
                "hour": hour,
                "power_kw": power,
                "irradiance_wm2": round(irradiance, 1),
                "temp_c": round(temp_c, 1),
                "efficiency": round(self.degraded_efficiency * 100, 2),
            })
        
        return profile


@dataclass
class WindSource:
    """风力发电单元 - 基于风速-功率曲线建模"""
    id: str
    name: str
    capacity_kw: float
    cut_in_speed: float = 3.0       # 切入风速 m/s
    rated_speed: float = 12.0       # 额定风速 m/s
    cut_out_speed: float = 25.0     # 切出风速 m/s
    hub_height_m: float = 100.0
    rotor_diameter_m: float = 120.0
    status: str = "online"
    
    current_power_kw: float = 0.0
    current_wind_speed: float = 0.0
    
    def compute_power(self, wind_speed_ms: float) -> float:
        """根据风速计算风电出力 - 分段函数"""
        v = wind_speed_ms
        if v < self.cut_in_speed or v >= self.cut_out_speed:
            return 0.0
        elif self.cut_in_speed <= v < self.rated_speed:
            # 立方关系
            ratio = (v**3 - self.cut_in_speed**3) / (self.rated_speed**3 - self.cut_in_speed**3)
            return self.capacity_kw * ratio
        else:
            return self.capacity_kw
    
    def simulate_hourly_profile(self, date: datetime, base_wind: float = 6.0,
                                 gustiness: float = 0.3) -> List[Dict]:
        """模拟24小时风电出力曲线"""
        profile = []
        for hour in range(24):
            # 模拟风速日变化（夜间风大，白天风小）
            diurnal = base_wind * (1 + 0.3 * np.sin(np.pi * (hour - 2) / 12))
            wind_speed = max(0, diurnal)
            
            power = round(self.compute_power(wind_speed), 1)
            time_label = (date + timedelta(hours=hour)).strftime("%H:00")
            
            profile.append({
                "time": time_label,
                "hour": hour,
                "power_kw": power,
                "wind_speed_ms": round(wind_speed, 2),
                "capacity_factor": round(power / self.capacity_kw * 100, 1) if self.capacity_kw > 0 else 0,
            })
        
        return profile


@dataclass
class GridSource:
    """市电/电网接入点"""
    id: str
    name: str
    voltage_level_kv: float = 10.0
    max_import_kw: float = 10000.0
    max_export_kw: float = 5000.0
    emission_factor: float = 0.581      # tCO₂/MWh
    current_power_kw: float = 0.0       # 正=购电，负=售电
    status: str = "online"
    
    @property
    def is_importing(self) -> bool:
        return self.current_power_kw > 0
    
    @property
    def carbon_emission_tco2_per_h(self) -> float:
        if self.current_power_kw > 0:
            return self.current_power_kw / 1000 * self.emission_factor
        return 0.0


@dataclass
class BiomassCHPSource:
    """生物质热电联产单元"""
    id: str
    name: str
    electric_capacity_kw: float = 2000.0
    thermal_capacity_kw: float = 3000.0
    feedstock_type: str = "农林废弃物"
    feedstock_consumption_t_per_day: float = 50.0
    biogas_yield_m3_per_t: float = 120.0
    methane_ratio: float = 0.60
    total_efficiency: float = 0.80
    
    current_electric_kw: float = 0.0
    current_thermal_kw: float = 0.0
    status: str = "online"
    
    @property
    def is_carbon_neutral(self) -> bool:
        return True  # 生物质排放视为碳中和
    
    def compute_output(self, utilization: float = 0.85) -> Tuple[float, float]:
        """计算热电出力"""
        electric = self.electric_capacity_kw * utilization
        thermal = self.thermal_capacity_kw * utilization
        return electric, thermal