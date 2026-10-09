"""Reproducible, explicitly synthetic hourly operations dataset (no API keys)."""
import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path


def generate():
    rng = random.Random(42)
    rows = []
    start = datetime(2026, 9, 9)
    for i in range(30 * 24):
        t = start + timedelta(hours=i)
        h = t.hour
        sun = max(0, math.sin((h - 6) * math.pi / 12))
        load = 2600 + (1550 if 8 <= h <= 20 else 150) + 320 * math.sin(h / 24 * 2 * math.pi) + rng.uniform(-160, 160)
        rows.append({
            "timestamp": t.isoformat() + "+08:00",
            "load_kw": round(load, 2),
            "pv_kw": round(4900 * sun * rng.uniform(.7, 1), 2),
            "wind_kw": round(900 + 420 * math.sin(i / 9) + rng.uniform(-150, 150), 2),
            "price_cny_kwh": 1.12 if h in (10, 11, 18, 19, 20, 21) else .32 if h < 7 else .68,
            "gas_m3": round(85 + 20 * (8 <= h <= 20) + rng.uniform(-5, 5), 2),
            "water_m3": round(100 + 35 * (8 <= h <= 20) + rng.uniform(-10, 10), 2),
            "reused_water_m3": round(65 + rng.uniform(-7, 7), 2),
        })
    payload = {
        "schema_version": 1, "is_simulated": True, "seed": 42,
        "park_name": "青屿 · 零碳示范园区", "timezone": "Asia/Shanghai", "interval_hours": 1,
        "assumptions": {
            "grid_kgco2_kwh": .58, "gas_kgco2_m3": 2.16,
            "factor_note": "演示情景假设，非官方核算因子；不含 Scope 3、抵消和绿证减排。",
            "battery_capacity_kwh": 5000, "battery_power_kw": 2000,
            "charge_efficiency": .95, "discharge_efficiency": .95,
            "soc_min": .2, "soc_max": .9, "soc_initial": .5,
            "degradation_cny_kwh": .05, "export_cny_kwh": .25,
            "grid_limit_kw": 5000,
        },
        "assets": [
            {"id": "PV-01", "name": "屋顶光伏阵列", "type": "光伏", "capacity": "5.0 MW", "zone": "制造片区"},
            {"id": "WT-01", "name": "分散式风电", "type": "风电", "capacity": "3.0 MW", "zone": "北部能源站"},
            {"id": "ESS-01", "name": "共享储能电站", "type": "储能", "capacity": "2 MW / 5 MWh", "zone": "综合能源站"},
            {"id": "LOAD-01", "name": "园区综合负荷", "type": "负荷", "capacity": "5.0 MW 接入", "zone": "全园区"},
            {"id": "WATER-01", "name": "中水回用系统", "type": "水务", "capacity": "150 m³/h", "zone": "生态处理站"},
        ], "records": rows,
    }
    path = Path(__file__).resolve().parents[1] / "data" / "operations.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(rows)} hourly records: {path}")


if __name__ == "__main__":
    generate()
