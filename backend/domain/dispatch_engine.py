"""
调度优化引擎 - 源网荷储协同优化调度
实现多目标优化：经济性、低碳、安全约束
"""
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable
from enum import Enum


class DispatchStrategy(Enum):
    """调度策略"""
    ECONOMIC = "economic"               # 经济最优
    LOW_CARBON = "low_carbon"           # 低碳优先
    BALANCED = "balanced"               # 平衡模式
    SAFETY_FIRST = "safety_first"       # 安全优先
    PEAK_SHAVING = "peak_shaving"       # 削峰填谷
    PRICE_ARBITRAGE = "price_arbitrage" # 价差套利


@dataclass
class DispatchResult:
    """调度结果"""
    strategy: DispatchStrategy
    horizon_hours: int = 24
    schedule: List[Dict] = field(default_factory=list)
    
    # 汇总指标
    total_pv_kwh: float = 0.0
    total_wind_kwh: float = 0.0
    total_grid_import_kwh: float = 0.0
    total_grid_export_kwh: float = 0.0
    total_load_kwh: float = 0.0
    total_storage_charge_kwh: float = 0.0
    total_storage_discharge_kwh: float = 0.0
    
    # 经济指标
    total_cost_yuan: float = 0.0
    total_revenue_yuan: float = 0.0
    net_cost_yuan: float = 0.0
    
    # 环境指标
    total_carbon_emission_tco2: float = 0.0
    renewable_ratio: float = 0.0
    carbon_offset_tco2: float = 0.0
    
    # 可靠指标
    loss_of_load_times: int = 0
    curtailment_times: int = 0
    peak_shaving_times: int = 0
    valley_filling_times: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "strategy": self.strategy.value,
            "horizon_hours": self.horizon_hours,
            "schedule": self.schedule,
            "summary": {
                "total_pv_kwh": round(self.total_pv_kwh, 1),
                "total_wind_kwh": round(self.total_wind_kwh, 1),
                "total_grid_import_kwh": round(self.total_grid_import_kwh, 1),
                "total_grid_export_kwh": round(self.total_grid_export_kwh, 1),
                "total_load_kwh": round(self.total_load_kwh, 1),
                "total_storage_charge_kwh": round(self.total_storage_charge_kwh, 1),
                "total_storage_discharge_kwh": round(self.total_storage_discharge_kwh, 1),
                "total_cost_yuan": round(self.total_cost_yuan, 2),
                "total_revenue_yuan": round(self.total_revenue_yuan, 2),
                "net_cost_yuan": round(self.net_cost_yuan, 2),
                "total_carbon_emission_tco2": round(self.total_carbon_emission_tco2, 4),
                "renewable_ratio": round(self.renewable_ratio * 100, 1),
                "loss_of_load_times": self.loss_of_load_times,
                "curtailment_times": self.curtailment_times,
                "peak_shaving_times": self.peak_shaving_times,
                "valley_filling_times": self.valley_filling_times,
            },
        }


@dataclass
class DispatchEngine:
    """调度优化引擎
    
    基于规则+优化的混合调度策略，实现源网荷储协同优化。
    支持多种调度策略，考虑经济性、碳减排、安全约束。
    """
    # 设备参数
    pv_capacity_kw: float = 5000.0
    wind_capacity_kw: float = 3000.0
    storage_capacity_kwh: float = 5000.0
    storage_power_kw: float = 2500.0
    grid_max_import_kw: float = 10000.0
    grid_max_export_kw: float = 5000.0
    
    # 效率参数
    storage_charge_eff: float = 0.95
    storage_discharge_eff: float = 0.95
    
    # 储能约束
    soc_min: float = 20.0
    soc_max: float = 90.0
    
    # 电价参数
    grid_emission_factor: float = 0.581  # tCO₂/MWh
    
    def optimize(
        self,
        pv_forecast: List[float],
        wind_forecast: List[float],
        load_forecast: List[float],
        grid_prices: List[float],
        initial_soc: float = 50.0,
        strategy: DispatchStrategy = DispatchStrategy.BALANCED,
    ) -> DispatchResult:
        """执行调度优化
        
        Args:
            pv_forecast: 光伏预测功率 [kW] x 24h
            wind_forecast: 风电预测功率 [kW] x 24h
            load_forecast: 负荷预测功率 [kW] x 24h
            grid_prices: 电网电价 [元/kWh] x 24h
            initial_soc: 初始SOC %
            strategy: 调度策略
        
        Returns:
            DispatchResult 调度结果
        """
        result = DispatchResult(strategy=strategy, horizon_hours=len(load_forecast))
        soc = initial_soc
        schedule = []
        
        for i in range(len(load_forecast)):
            pv = pv_forecast[i] if i < len(pv_forecast) else 0
            wind = wind_forecast[i] if i < len(wind_forecast) else 0
            load = load_forecast[i] if i < len(load_forecast) else 0
            price = grid_prices[i] if i < len(grid_prices) else 0.5
            
            renewable_total = pv + wind
            net = renewable_total - load  # 正=余电，负=缺电
            
            # 根据策略决定储能行为
            charge_kw, discharge_kw, grid_import_kw, grid_export_kw = self._decide_storage_action(
                net, soc, price, renewable_total, load, strategy
            )
            
            # 更新SOC
            energy_change = (charge_kw * self.storage_charge_eff - 
                           discharge_kw / self.storage_discharge_eff)
            soc = max(self.soc_min, min(self.soc_max,
                      soc + energy_change / self.storage_capacity_kwh * 100))
            
            # 计算碳排放
            carbon = grid_import_kw / 1000 * self.grid_emission_factor
            
            # 成本计算
            cost = grid_import_kw * price - grid_export_kw * price * 0.8  # 售电打折
            storage_cost = (charge_kw + discharge_kw) * 0.05  # 储能老化成本
            
            schedule.append({
                "hour": i,
                "time": f"{i:02d}:00",
                "pv_kw": round(pv, 1),
                "wind_kw": round(wind, 1),
                "renewable_total_kw": round(renewable_total, 1),
                "load_kw": round(load, 1),
                "net_kw": round(net, 1),
                "charge_kw": round(charge_kw, 1),
                "discharge_kw": round(discharge_kw, 1),
                "grid_import_kw": round(grid_import_kw, 1),
                "grid_export_kw": round(grid_export_kw, 1),
                "soc": round(soc, 1),
                "price_yuan": price,
                "carbon_tco2": round(carbon, 4),
                "cost_yuan": round(cost + storage_cost, 2),
                "action": self._get_action_label(charge_kw, discharge_kw, grid_import_kw, grid_export_kw),
            })
            
            # 累计统计
            result.total_pv_kwh += pv
            result.total_wind_kwh += wind
            result.total_load_kwh += load
            result.total_grid_import_kwh += grid_import_kw
            result.total_grid_export_kwh += grid_export_kw
            result.total_storage_charge_kwh += charge_kw
            result.total_storage_discharge_kwh += discharge_kw
            result.total_cost_yuan += cost + storage_cost
            result.total_carbon_emission_tco2 += carbon
            
            if grid_import_kw > 0 and renewable_total < load:
                result.loss_of_load_times += 0
            if grid_export_kw > 0:
                result.curtailment_times += 1
            if discharge_kw > 0:
                result.peak_shaving_times += 1
            if charge_kw > 0:
                result.valley_filling_times += 1
        
        # 计算汇总指标
        total_gen = result.total_pv_kwh + result.total_wind_kwh
        if result.total_load_kwh > 0:
            result.renewable_ratio = min(1.0, total_gen / result.total_load_kwh)
        
        result.total_revenue_yuan = result.total_grid_export_kwh * 0.3  # 简化售电收入
        result.net_cost_yuan = result.total_cost_yuan - result.total_revenue_yuan
        result.carbon_offset_tco2 = total_gen / 1000 * self.grid_emission_factor
        result.schedule = schedule
        
        return result
    
    def _decide_storage_action(
        self, net: float, soc: float, price: float,
        renewable: float, load: float, strategy: DispatchStrategy
    ) -> Tuple[float, float, float, float]:
        """决定储能充放电行为
        
        Returns:
            (charge_kw, discharge_kw, grid_import_kw, grid_export_kw)
        """
        charge_kw = discharge_kw = grid_import_kw = grid_export_kw = 0.0
        
        if net > 0:
            # 有余电
            surplus = net
            
            if strategy == DispatchStrategy.PRICE_ARBITRAGE:
                # 价差套利：低价时充电，高价时已放电
                if price < 0.4 and soc < self.soc_max:
                    charge_kw = min(surplus, self.storage_power_kw,
                                   (self.soc_max - soc) / 100 * self.storage_capacity_kwh)
                surplus -= charge_kw
                if surplus > 0:
                    grid_export_kw = min(surplus, self.grid_max_export_kw)
            elif strategy == DispatchStrategy.LOW_CARBON:
                # 低碳优先：优先充电，减少弃电
                charge_kw = min(surplus, self.storage_power_kw,
                               (self.soc_max - soc) / 100 * self.storage_capacity_kwh)
                surplus -= charge_kw
                if surplus > 0:
                    grid_export_kw = min(surplus, self.grid_max_export_kw)
            elif strategy == DispatchStrategy.PEAK_SHAVING:
                # 削峰填谷：谷时充电，峰时放电
                if soc < 85:
                    charge_kw = min(surplus, self.storage_power_kw,
                                   (self.soc_max - soc) / 100 * self.storage_capacity_kwh)
                surplus -= charge_kw
                if surplus > 0:
                    grid_export_kw = min(surplus, self.grid_max_export_kw)
            else:
                # Balanced / Economic: 按比例分配
                charge_kw = min(surplus * 0.7, self.storage_power_kw,
                               (self.soc_max - soc) / 100 * self.storage_capacity_kwh)
                surplus -= charge_kw
                if surplus > 0:
                    grid_export_kw = min(surplus, self.grid_max_export_kw)
        else:
            # 缺电
            deficit = abs(net)
            
            if strategy == DispatchStrategy.PRICE_ARBITRAGE:
                # 高价时尽量放电，否则购电
                if price > 0.6 and soc > self.soc_min:
                    discharge_kw = min(deficit, self.storage_power_kw,
                                      (soc - self.soc_min) / 100 * self.storage_capacity_kwh)
                deficit -= discharge_kw
                if deficit > 0:
                    grid_import_kw = min(deficit, self.grid_max_import_kw)
            elif strategy == DispatchStrategy.LOW_CARBON:
                # 低碳优先：优先放电，减少购电
                if soc > self.soc_min:
                    discharge_kw = min(deficit, self.storage_power_kw,
                                      (soc - self.soc_min) / 100 * self.storage_capacity_kwh)
                deficit -= discharge_kw
                if deficit > 0:
                    grid_import_kw = min(deficit, self.grid_max_import_kw)
            elif strategy == DispatchStrategy.PEAK_SHAVING:
                # 削峰：负荷高峰时放电
                if soc > self.soc_min:
                    discharge_kw = min(deficit * 0.7, self.storage_power_kw,
                                      (soc - self.soc_min) / 100 * self.storage_capacity_kwh)
                deficit -= discharge_kw
                if deficit > 0:
                    grid_import_kw = min(deficit, self.grid_max_import_kw)
            else:
                # Balanced: 优先放电，不够再购电
                if soc > self.soc_min:
                    discharge_kw = min(deficit * 0.6, self.storage_power_kw,
                                      (soc - self.soc_min) / 100 * self.storage_capacity_kwh)
                deficit -= discharge_kw
                if deficit > 0:
                    grid_import_kw = min(deficit, self.grid_max_import_kw)
        
        return charge_kw, discharge_kw, grid_import_kw, grid_export_kw
    
    def _get_action_label(self, charge: float, discharge: float,
                          grid_import: float, grid_export: float) -> str:
        """获取调度动作标签"""
        if charge > 0 and grid_export > 0:
            return "充电+售电"
        elif charge > 0:
            return "充电"
        elif discharge > 0 and grid_import > 0:
            return "放电+购电"
        elif discharge > 0:
            return "放电"
        elif grid_import > 0:
            return "购电"
        elif grid_export > 0:
            return "售电"
        else:
            return "自平衡"
    
    def demo_optimize(self) -> DispatchResult:
        """演示优化 - 使用静态模拟数据"""
        from data.mock_data import get_mock_data
        mg = get_mock_data()

        pv_forecast = [p["power_kw"] for p in mg.get_pv_forecast()]
        wind_forecast = [w["power_kw"] for w in mg.get_wind_forecast()]
        load_forecast = mg.get_load_forecast()
        prices = mg.get_grid_price()

        return self.optimize(pv_forecast, wind_forecast, load_forecast, prices,
                           initial_soc=50.0, strategy=DispatchStrategy.BALANCED)


# 全局单例
_engine_instance: Optional[DispatchEngine] = None


def get_dispatch_engine() -> DispatchEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = DispatchEngine()
    return _engine_instance