"""
园区数据服务 - 从静态JSON数据加载园区运行状态
整合领域模型，提供一致性的数据访问接口
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from domain.energy_source import PVSource, WindSource, GridSource, BiomassCHPSource
from domain.energy_storage import BatteryStorage, StorageBank, StorageType
from domain.energy_load import EnergyLoad, LoadCluster, LoadType, LoadFlexibility
from domain.energy_network import MicroGrid, PowerBus, BusType
from domain.carbon_flow import CarbonFlowTracker
from domain.dispatch_engine import DispatchEngine, DispatchStrategy
from services.monitoring_service import MonitoringService, get_monitoring_service


@dataclass
class ParkDataService:
    """园区数据服务 - 从静态JSON加载数据，不包含随机生成
    
    替换为真实数据时，只需替换 data/ 目录下的 JSON 文件。
    """

    park_name: str = "零碳智慧园区"
    park_area_m2: float = 500000.0

    # 领域模型（用于调度优化等计算）
    pv_station: PVSource = field(default_factory=lambda: PVSource(
        id="PV-001", name="1号光伏电站", capacity_kw=5000,
        area_m2=25000, latitude=31.2, longitude=121.5
    ))
    wind_farm: WindSource = field(default_factory=lambda: WindSource(
        id="WIND-001", name="1号风电场", capacity_kw=3000
    ))
    grid_connection: GridSource = field(default_factory=lambda: GridSource(
        id="GRID-001", name="市电馈线"
    ))
    biomass_chp: BiomassCHPSource = field(default_factory=lambda: BiomassCHPSource(
        id="BIOCHP-001", name="生物质CHP电厂"
    ))
    battery: BatteryStorage = field(default_factory=lambda: BatteryStorage(
        id="BAT-001", name="1号锂电池储能系统",
        capacity_kwh=5000, rated_power_kw=2500
    ))
    load_cluster: LoadCluster = field(default_factory=lambda: LoadCluster(id="CLUSTER-001", name="园区负荷集群"))
    micro_grid: MicroGrid = field(default_factory=lambda: MicroGrid(id="MG-001", name="园区微电网"))
    carbon_tracker: CarbonFlowTracker = field(default_factory=CarbonFlowTracker)
    dispatch_engine: DispatchEngine = field(default_factory=DispatchEngine)
    monitor: MonitoringService = field(default_factory=get_monitoring_service)

    def __post_init__(self):
        self._init_loads()
        self._init_storage_bank()

    def _init_loads(self):
        loads = [
            EnergyLoad(
                id="LOAD-001", name="一号生产线",
                load_type=LoadType.MANUFACTURING, flexibility=LoadFlexibility.SHIFTABLE,
                rated_power_kw=2000, department="制造一部", min_power_kw=500, shift_window_h=4.0,
            ),
            EnergyLoad(
                id="LOAD-002", name="二号生产线",
                load_type=LoadType.MANUFACTURING, flexibility=LoadFlexibility.SHIFTABLE,
                rated_power_kw=1800, department="制造二部", min_power_kw=400, shift_window_h=3.0,
            ),
            EnergyLoad(
                id="WWTP-001", name="污水处理厂",
                load_type=LoadType.WWTP, flexibility=LoadFlexibility.CURTAILABLE,
                rated_power_kw=1500, department="环保部", min_power_kw=800, curtailment_cost=0.8,
            ),
            EnergyLoad(
                id="HVAC-001", name="中央空调系统",
                load_type=LoadType.HVAC, flexibility=LoadFlexibility.FLEXIBLE,
                rated_power_kw=800, department="设施部", min_power_kw=200, temp_setpoint_c=24.0,
            ),
            EnergyLoad(
                id="EV-001", name="充电桩集群",
                load_type=LoadType.EV_CHARGING, flexibility=LoadFlexibility.SHIFTABLE,
                rated_power_kw=600, department="后勤部", min_power_kw=0, shift_window_h=6.0,
            ),
            EnergyLoad(
                id="DC-001", name="数据中心",
                load_type=LoadType.DATA_CENTER, flexibility=LoadFlexibility.FIXED,
                rated_power_kw=500, department="IT部", min_power_kw=400,
            ),
            EnergyLoad(
                id="OFFICE-001", name="办公区",
                load_type=LoadType.OFFICE, flexibility=LoadFlexibility.CURTAILABLE,
                rated_power_kw=300, department="行政部", min_power_kw=100, curtailment_cost=0.3,
            ),
        ]
        self.load_cluster = LoadCluster(id="CLUSTER-001", name="园区负荷集群", loads=loads)

    def _init_storage_bank(self):
        self.storage_bank = StorageBank(
            id="BANK-001", name="储能电站", batteries=[self.battery]
        )

    # ── 数据加载（从静态JSON） ──────────────────────────────

    def update_realtime_data(self, timestamp: datetime = None) -> Dict:
        """从静态JSON加载园区实时数据快照"""
        from data.mock_data import get_mock_data
        return get_mock_data().get_park_snapshot()

    def get_snapshot(self) -> Dict:
        """获取园区完整状态快照"""
        from data.mock_data import get_mock_data
        return get_mock_data().get_park_snapshot()

    def get_dispatch_optimization(self, strategy: str = "balanced") -> Dict:
        """获取调度优化方案（基于领域模型计算）"""
        from data.mock_data import get_mock_data

        strategy_map = {
            "economic": DispatchStrategy.ECONOMIC,
            "low_carbon": DispatchStrategy.LOW_CARBON,
            "balanced": DispatchStrategy.BALANCED,
            "safety_first": DispatchStrategy.SAFETY_FIRST,
            "peak_shaving": DispatchStrategy.PEAK_SHAVING,
            "price_arbitrage": DispatchStrategy.PRICE_ARBITRAGE,
        }
        dispatch_strategy = strategy_map.get(strategy, DispatchStrategy.BALANCED)

        # 从静态数据加载预测值
        md = get_mock_data()
        pv_f = [f["power_kw"] for f in md.get_pv_forecast()]
        wind_f = [f["power_kw"] for f in md.get_wind_forecast()]
        load_f = md.get_load_forecast()
        price_f = md.get_grid_price()

        # 使用领域模型进行调度计算（传入实际策略和预测数据）
        result = self.dispatch_engine.optimize(
            pv_forecast=pv_f,
            wind_forecast=wind_f,
            load_forecast=load_f,
            grid_prices=price_f,
            initial_soc=50.0,
            strategy=dispatch_strategy,
        )

        # 注入静态预测数据
        data = result.to_dict()
        data["forecast"] = {
            "pv": pv_f,
            "wind": wind_f,
            "load": load_f,
            "price": price_f,
        }
        return data

    def get_vpp_aggregation(self) -> Dict:
        """获取虚拟电厂聚合状态"""
        from data.mock_data import get_mock_data
        return get_mock_data().get_park_vpp_aggregation()


# 全局单例
_park_service: Optional[ParkDataService] = None


def get_park_service() -> ParkDataService:
    global _park_service
    if _park_service is None:
        _park_service = ParkDataService()
    return _park_service