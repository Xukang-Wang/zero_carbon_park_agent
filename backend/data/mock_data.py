"""
集中式模拟数据加载器
从 data/ 目录下的 JSON 文件加载静态模拟数据，不包含任何随机生成逻辑。
替换为真实数据时，只需替换对应的 JSON 文件即可。
"""
import json
import os
from typing import Dict, Any, List, Optional

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_json(subdir: str, filename: str) -> Any:
    """加载 JSON 数据文件"""
    path = os.path.join(DATA_DIR, subdir, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class MockDataGenerator:
    """模拟数据加载器（单例模式）
    
    从 data/ 目录下的 JSON 文件加载数据，零随机生成。
    替换为真实数据时，只需替换对应 JSON 文件内容。
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = {}
        return cls._instance

    def _get(self, subdir: str, filename: str) -> Any:
        """带缓存的 JSON 加载"""
        key = f"{subdir}/{filename}"
        if key not in self._cache:
            self._cache[key] = _load_json(subdir, filename)
        return self._cache[key]

    # ── 能源数据 ──────────────────────────────────────────

    def get_energy_status(self) -> Dict:
        return self._get("energy", "energy_status.json")

    def get_pv_forecast(self) -> List[Dict]:
        return self._get("energy", "pv_forecast.json")

    def get_wind_forecast(self) -> List[Dict]:
        return self._get("energy", "wind_forecast.json")

    def get_load_forecast(self) -> List[float]:
        return self._get("energy", "load_forecast.json")

    def get_grid_price(self) -> List[float]:
        return self._get("energy", "grid_price.json")

    # ── 碳排放数据 ────────────────────────────────────────

    def get_scope_emissions(self) -> Dict:
        return self._get("carbon", "scope_emissions.json")

    def get_carbon_portfolio(self) -> Dict:
        return self._get("carbon", "carbon_portfolio.json")

    def get_trading_strategy(self) -> Dict:
        return self._get("carbon", "trading_strategy.json")

    def get_carbon_trend(self, days: int = 30) -> List[Dict]:
        return self._get("carbon", "carbon_trend_30d.json")[:days]

    def get_cbam_report(self, product_type: str = "steel") -> Dict:
        valid_types = ["steel", "aluminum", "cement", "fertilizer"]
        pt = product_type if product_type in valid_types else "steel"
        return self._get("carbon", f"cbam_report_{pt}.json")

    # ── 评价数据 ──────────────────────────────────────────

    def get_evaluation(self) -> Dict:
        return self._get("evaluation", "indicators.json")

    def get_cert_progress(self) -> Dict:
        return self._get("evaluation", "cert_progress.json")

    # ── 经济性数据 ────────────────────────────────────────

    def get_pv_economics(self) -> Dict:
        return self._get("economic", "pv_economics.json")

    def get_storage_economics(self) -> Dict:
        return self._get("economic", "storage_economics.json")

    def get_comprehensive_economics(self) -> Dict:
        return self._get("economic", "comprehensive_economics.json")

    # ── 生物质数据 ────────────────────────────────────────

    def get_chp_analysis(self) -> Dict:
        return self._get("biomass", "chp_analysis.json")

    def get_biogas_analysis(self) -> Dict:
        return self._get("biomass", "biogas_analysis.json")

    # ── 工业节能数据 ──────────────────────────────────────

    def get_industrial_energy(self) -> Dict:
        return self._get("industrial", "industrial_energy.json")

    # ── CCUS数据 ──────────────────────────────────────────

    def get_ccus(self) -> Dict:
        return self._get("ccus", "ccus_analysis.json")

    # ── 共享储能数据 ──────────────────────────────────────

    def get_shared_storage(self) -> Dict:
        return self._get("storage", "shared_storage.json")

    # ── 园区综合数据 ──────────────────────────────────────

    def get_park_snapshot(self) -> Dict:
        return self._get("park", "snapshot.json")

    def get_park_nodes(self) -> Dict:
        return self._get("park", "nodes.json")

    def get_park_power_flow(self) -> Dict:
        return self._get("park", "power_flow.json")

    def get_park_vpp_aggregation(self) -> Dict:
        return self._get("park", "vpp_aggregation.json")

    def get_park_hourly_trend(self, hours: int = 24) -> List[Dict]:
        data = self._get("park", "hourly_trend.json")
        return data[:hours]


# ── 水质数据 ──────────────────────────────────────────

    def get_water_realtime(self, device_id: str = "WQ-001") -> Dict:
        return self._get("water", f"realtime_{device_id}.json")

    def get_water_history(self, device_id: str = "WQ-001", hours: int = 24) -> List[Dict]:
        data = self._get("water", f"history_{device_id}.json")
        return data[:hours]

    def get_water_prediction(self, device_id: str = "WQ-001", horizon: int = 24) -> List[Dict]:
        data = self._get("water", f"prediction_{device_id}.json")
        return data[:horizon]


# 全局单例
_mock_data = MockDataGenerator()


def get_mock_data() -> MockDataGenerator:
    """获取全局模拟数据加载器实例"""
    return _mock_data