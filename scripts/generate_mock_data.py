"""
一次性生成所有模拟数据 JSON 文件
运行此脚本生成静态数据，供主程序读取
生成后此脚本不再被主程序引用
"""
import json
import numpy as np
import os
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "data")
SEED = 42
rng = np.random.default_rng(SEED)
_now = datetime.now()

# 园区基础参数
PV_CAPACITY_KW = 5000
WIND_CAPACITY_KW = 3000
STORAGE_CAPACITY_KWH = 5000
STORAGE_POWER_KW = 2500
BASE_LOAD_KW = 4500


def save_json(subdir: str, filename: str, data):
    path = os.path.join(DATA_DIR, subdir, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {subdir}/{filename}")


# ── 能源预测数据 ──────────────────────────────────────

def generate_pv_forecast():
    forecast = []
    for i in range(24):
        hour = (_now + timedelta(hours=i)).hour
        if 6 <= hour <= 18:
            peak_hour = 12
            power = PV_CAPACITY_KW * max(0, 1 - ((hour - peak_hour) / 6) ** 2)
            power += rng.normal(0, 80)
            power = max(0, round(power, 1))
        else:
            power = 0.0
        forecast.append({
            "time": (_now + timedelta(hours=i)).isoformat(),
            "power_kw": power,
            "confidence": round(0.85 + rng.uniform(-0.05, 0.05), 2),
        })
    return forecast


def generate_wind_forecast():
    forecast = []
    for i in range(24):
        power = WIND_CAPACITY_KW * (0.3 + 0.4 * np.sin(i * np.pi / 12))
        power += rng.normal(0, 200)
        power = max(0, round(power, 1))
        forecast.append({
            "time": (_now + timedelta(hours=i)).isoformat(),
            "power_kw": power,
            "confidence": round(0.72 + rng.uniform(-0.08, 0.08), 2),
        })
    return forecast


def generate_load_forecast():
    return [round(BASE_LOAD_KW + rng.normal(0, 300), 1) for _ in range(24)]


def generate_grid_price():
    prices = []
    for i in range(24):
        hour = (_now + timedelta(hours=i)).hour
        if 0 <= hour < 6 or 22 <= hour <= 23:
            prices.append(round(0.30 + rng.uniform(-0.02, 0.02), 2))
        elif 8 <= hour < 11 or 18 <= hour < 21:
            prices.append(round(0.85 + rng.uniform(-0.05, 0.05), 2))
        else:
            prices.append(round(0.55 + rng.uniform(-0.03, 0.03), 2))
    return prices


# ── 能源状态 ──────────────────────────────────────────

def generate_energy_status():
    pv_forecast = generate_pv_forecast()
    return {
        "timestamp": _now.isoformat(),
        "pv_station": {
            "id": "PV-001", "name": "1号光伏电站", "rated_capacity_kw": PV_CAPACITY_KW,
            "current_power_kw": round(pv_forecast[0]["power_kw"], 1),
            "status": "running", "generation_today_kwh": 15200.0,
        },
        "grid": {
            "id": "GRID-001", "current_power_kw": 2800.0,
            "voltage_level_kv": 10, "emission_factor": 0.581,
        },
        "storage": {
            "id": "BAT-001", "name": "1号锂电池储能系统",
            "capacity_kwh": STORAGE_CAPACITY_KWH, "current_soc": 62.5,
            "charge_power_kw": 850.0, "discharge_power_kw": 0.0, "status": "charging",
        },
        "total_load": {"current_power_kw": 4800.0, "renewable_ratio": 0.41},
        "dispatch_strategy": "peak_shaving_and_valley_filling",
    }


# ── 碳排放数据 ────────────────────────────────────────

def generate_scope_emissions():
    return {
        "period": "2026-08",
        "scope_1": {
            "label": "直接排放", "total_tco2": 356.42,
            "breakdown": [
                {"source": "工业过程排放", "emission_tco2": 178.21, "ratio": 0.50},
                {"source": "化石燃料燃烧", "emission_tco2": 124.75, "ratio": 0.35},
                {"source": "园区交通", "emission_tco2": 35.64, "ratio": 0.10},
                {"source": "制冷剂泄漏", "emission_tco2": 17.82, "ratio": 0.05},
            ],
        },
        "scope_2": {
            "label": "间接排放（外购电力）", "total_tco2": 2088.72,
            "breakdown": [{
                "source": "外购电力", "consumption_mwh": 3595.04,
                "emission_factor": 0.581, "emission_tco2": 2088.72,
            }],
            "grid_emission_factor": 0.581,
        },
        "scope_3": {
            "label": "其他间接排放", "total_tco2": 987.35,
            "breakdown": [
                {"source": "供应链上游", "emission_tco2": 444.31, "ratio": 0.45},
                {"source": "产品运输", "emission_tco2": 197.47, "ratio": 0.20},
                {"source": "员工通勤", "emission_tco2": 98.74, "ratio": 0.10},
                {"source": "废弃物处理", "emission_tco2": 148.10, "ratio": 0.15},
                {"source": "其他", "emission_tco2": 98.73, "ratio": 0.10},
            ],
        },
        "total_emission_tco2": 3432.49,
        "carbon_intensity_tco2_per_million_yuan": 0.98,
    }


def generate_carbon_portfolio():
    return {
        "total_asset_value_yuan": 2985000.00,
        "assets": [
            {"id": "CEA-001", "type": "碳配额（CEA）", "amount_tco2": 5000, "unit_price_yuan": 60.00,
             "total_value_yuan": 300000.00, "allocation_year": 2026, "status": "持有", "expiry": "2026-12-31"},
            {"id": "CCER-001", "type": "CCER", "amount_tco2": 2000, "unit_price_yuan": 50.00,
             "total_value_yuan": 100000.00, "project_type": "光伏发电", "status": "持有", "expiry": "2027-06-30"},
            {"id": "CCER-002", "type": "CCER", "amount_tco2": 1500, "unit_price_yuan": 45.00,
             "total_value_yuan": 67500.00, "project_type": "沼气利用", "status": "待签发", "expected_issuance": "2026-09-15"},
            {"id": "GEC-001", "type": "绿证（GEC）", "amount_mwh": 10000, "unit_price_yuan": 30.00,
             "total_value_yuan": 300000.00, "source": "光伏发电", "status": "持有"},
        ],
        "risk_analysis": {
            "compliance_gap_tco2": 120.00, "surplus_tco2": 1200.00,
            "recommendation": "当前碳配额盈余，建议出售 500 tCO2 CEA 配额",
            "market_trend": "看涨", "expected_price_change_percent": 5.5,
        },
    }


def generate_trading_strategy():
    return {
        "market_overview": {
            "cea_price_yuan": 60.50, "ccer_price_yuan": 50.20, "gec_price_yuan": 30.00,
            "market_sentiment": "bullish", "trading_volume_tco2": 650000,
        },
        "strategies": [
            {"name": "配额盈余出售", "action": "sell", "asset_type": "CEA", "volume_tco2": 500,
             "target_price_yuan": 62, "expected_revenue_yuan": 31000, "timing": "2026年Q3",
             "rationale": "碳价处于上升通道，建议分批出售锁定利润"},
            {"name": "CCER 置换", "action": "swap", "asset_type": "CCER->CEA", "volume_tco2": 1000,
             "target_price_yuan": 50, "expected_cost_yuan": 50000, "timing": "2026年Q3-Q4",
             "rationale": "CCER 价格低于 CEA，可置换降低成本"},
            {"name": "绿证采购", "action": "buy", "asset_type": "GEC", "volume_mwh": 5000,
             "target_price_yuan": 28, "expected_cost_yuan": 140000, "timing": "2026年Q4",
             "rationale": "满足可再生能源消纳责任权重，对冲碳成本"},
        ],
        "recommendation": "建议优先执行配额盈余出售策略，在 Q3 碳价高位分批出售 500 tCO2 CEA，预计获利 3.1 万元",
    }


def generate_carbon_trend(days=30):
    """生成碳排放趋势（静态预计算）"""
    trend = []
    base_net = 2.5 * 24  # ~60 tCO2/day
    base_direct = 0.5 * 24  # ~12 tCO2/day
    base_renewable = 0.41
    for i in range(days):
        date = (datetime.now() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        noise = rng.normal(0, 2)
        trend.append({
            "date": date,
            "net_emission_tco2": round(base_net + noise, 2),
            "direct_emission_tco2": round(base_direct + noise * 0.3, 2),
            "renewable_ratio": round(base_renewable + rng.normal(0, 0.02), 2),
        })
    return trend


def generate_cbam_report(product_type="steel"):
    configs = {
        "steel": {"name": "钢铁产品", "cn_code": "7208", "default_emission": 1.8},
        "aluminum": {"name": "铝产品", "cn_code": "7601", "default_emission": 8.5},
        "cement": {"name": "水泥产品", "cn_code": "2523", "default_emission": 0.6},
        "fertilizer": {"name": "化肥产品", "cn_code": "3102", "default_emission": 2.2},
    }
    config = configs.get(product_type, configs["steel"])
    return {
        "product": {"type": product_type, "name": config["name"], "cn_code": config["cn_code"]},
        "emissions": {
            "direct_emission_tco2_per_ton": config["default_emission"],
            "indirect_emission_tco2_per_ton": round(config["default_emission"] * 0.4, 2),
            "total_embedded_emission_tco2_per_ton": round(config["default_emission"] * 1.4, 2),
            "annual_production_ton": 100000.0,
            "annual_total_emission_tco2": round(config["default_emission"] * 1.4 * 100000, 0),
        },
        "cbam_obligation": {
            "eu_carbon_price_eur": 80.0, "free_allocation_ratio": 0.0,
            "cbam_certificate_cost_eur_per_ton": round(config["default_emission"] * 1.4 * 80, 2),
            "estimated_annual_cost_eur": round(config["default_emission"] * 1.4 * 80 * 100000, 0),
            "estimated_annual_cost_cny": round(config["default_emission"] * 1.4 * 80 * 100000 * 7.8, 0),
        },
        "compliance_status": {
            "reporting_ready": True, "verification_status": "第三方核查中",
            "next_reporting_deadline": "2026-10-31", "risk_level": "medium",
            "recommendations": ["建立产品级碳排放核算体系", "加快绿电采购，降低间接排放",
                              "评估碳捕集技术应用可行性", "定期更新CBAM规则变化跟踪"],
        },
    }


# ── 评价数据 ──────────────────────────────────────────

def generate_evaluation():
    return {
        "standard": "T/CSTE 0042-2022 零碳园区评价规范",
        "categories": [
            {
                "name": "能源结构", "weight": 0.25, "indicators": [
                    {"name": "可再生能源占比", "current_value": 41.0, "unit": "%", "target": 50, "score": 82.0, "status": "warning", "trend": "up"},
                    {"name": "清洁能源装机占比", "current_value": 64.5, "unit": "%", "target": 60, "score": 92.0, "status": "pass", "trend": "up"},
                ]
            },
            {
                "name": "碳排放", "weight": 0.30, "indicators": [
                    {"name": "碳排放强度", "current_value": 0.98, "unit": "tCO2/万元", "target": 0.5, "score": 68.0, "status": "warning", "trend": "down"},
                    {"name": "碳排放总量下降率", "current_value": 12.5, "unit": "%", "target": 10, "score": 85.0, "status": "pass", "trend": "up"},
                    {"name": "碳抵消比例", "current_value": 35.0, "unit": "%", "target": 100, "score": 48.0, "status": "critical", "trend": "up"},
                ]
            },
            {
                "name": "资源利用", "weight": 0.20, "indicators": [
                    {"name": "能源综合利用率", "current_value": 78.5, "unit": "%", "target": 75, "score": 88.0, "status": "pass", "trend": "up"},
                    {"name": "余热回收利用率", "current_value": 52.3, "unit": "%", "target": 50, "score": 82.0, "status": "pass", "trend": "up"},
                    {"name": "水资源循环利用率", "current_value": 91.2, "unit": "%", "target": 90, "score": 95.0, "status": "pass", "trend": "stable"},
                ]
            },
            {
                "name": "管理与创新", "weight": 0.15, "indicators": [
                    {"name": "能源管理体系认证", "current_value": "已认证", "unit": "-", "target": "已认证", "score": 100, "status": "pass", "trend": "stable"},
                    {"name": "碳管理体系", "current_value": "建设中", "unit": "-", "target": "已建立", "score": 60, "status": "warning", "trend": "up"},
                    {"name": "数字化管理平台", "current_value": "已部署", "unit": "-", "target": "已部署", "score": 100, "status": "pass", "trend": "stable"},
                ]
            },
            {
                "name": "生态与环境", "weight": 0.10, "indicators": [
                    {"name": "绿化覆盖率", "current_value": 35.5, "unit": "%", "target": 30, "score": 95.0, "status": "pass", "trend": "stable"},
                    {"name": "固废综合利用率", "current_value": 90.5, "unit": "%", "target": 90, "score": 88.0, "status": "pass", "trend": "up"},
                ]
            },
        ],
        "total_score": 78.5,
        "grade": "二星（达标）",
        "grade_levels": {"一星": "60-70分", "二星": "70-80分", "三星": "80-90分", "四星": "90-95分", "五星": "95-100分"},
    }


def generate_cert_progress():
    return {
        "target_certification": "零碳园区（三星级）",
        "overall_progress": 62.5,
        "estimated_completion": (_now + timedelta(days=165)).strftime("%Y-%m-%d"),
        "milestones": [
            {"name": "碳排放核算体系建立", "progress": 100, "status": "completed", "completed_date": "2026-03-15", "description": "完成Scope 1/2/3碳排放核算方法学建立"},
            {"name": "能源管理体系认证", "progress": 100, "status": "completed", "completed_date": "2026-05-20", "description": "通过ISO 50001能源管理体系认证"},
            {"name": "可再生能源占比提升", "progress": 72, "status": "in_progress", "target_date": "2026-10-31", "description": "光伏扩容至8MW，可再生能源占比提升至50%以上"},
            {"name": "碳足迹抵消方案", "progress": 40, "status": "in_progress", "target_date": "2026-12-31", "description": "采购CCER/绿证实现100%碳抵消"},
            {"name": "零碳数字化平台", "progress": 85, "status": "in_progress", "target_date": "2026-09-30", "description": "完成碳管理数字化平台部署与数据对接"},
            {"name": "第三方核查", "progress": 0, "status": "pending", "target_date": "2027-01-31", "description": "委托第三方机构进行零碳园区核查"},
            {"name": "认证申报", "progress": 0, "status": "pending", "target_date": "2027-03-31", "description": "向认证机构提交零碳园区认证申请"},
        ],
        "key_gaps": [
            {"area": "可再生能源占比", "current": "41%", "target": "≥50%", "gap": "9%", "action": "推进屋顶光伏二期建设（3MW）"},
            {"area": "碳抵消比例", "current": "约35%", "target": "100%", "gap": "65%", "action": "采购CCER和绿证，开发生物质能碳汇项目"},
            {"area": "碳排放强度", "current": "0.98 tCO2/万元", "target": "≤0.5 tCO2/万元", "gap": "约49%", "action": "实施能效提升改造，优化生产工艺"},
        ],
    }


# ── 经济性数据 ────────────────────────────────────────

def generate_pv_economics():
    return {
        "project": {"name": "园区屋顶光伏电站（一期+二期）", "total_capacity_kw": 8000, "annual_generation_mwh": 9200.0, "lifetime_years": 25},
        "investment": {"total_investment_yuan": 32000000, "unit_cost_yuan_per_kw": 4000, "subsidy_yuan": 800000, "net_investment_yuan": 31200000},
        "revenue": {"annual_electricity_saving_yuan": 6500000, "annual_carbon_revenue_yuan": 300000, "annual_total_revenue_yuan": 6800000},
        "costs": {"annual_om_cost_yuan": 320000, "annual_depreciation_yuan": 1248000, "annual_total_cost_yuan": 1568000},
        "financial_indicators": {"irr_percent": 12.8, "npv_yuan": 11500000, "payback_period_years": 6.5, "roi_percent": 15.2, "lcoe_yuan_per_kwh": 0.30},
        "carbon_benefit": {"annual_carbon_reduction_tco2": 5300.0, "lifetime_carbon_reduction_tco2": 132500},
        "sensitivity_analysis": {
            "electricity_price": [
                {"change_percent": -20, "irr_percent": 7.2}, {"change_percent": -10, "irr_percent": 10.1},
                {"change_percent": 0, "irr_percent": 12.8}, {"change_percent": 10, "irr_percent": 15.3},
                {"change_percent": 20, "irr_percent": 17.5},
            ],
            "investment_cost": [
                {"change_percent": -20, "irr_percent": 16.8}, {"change_percent": -10, "irr_percent": 14.5},
                {"change_percent": 0, "irr_percent": 12.8}, {"change_percent": 10, "irr_percent": 10.2},
                {"change_percent": 20, "irr_percent": 8.1},
            ],
        },
    }


def generate_storage_economics():
    return {
        "project": {"name": "园区锂电池储能系统", "capacity_kwh": 5000, "rated_power_kw": 2500, "lifetime_years": 15, "cycle_life": 6000},
        "investment": {"total_investment_yuan": 7500000, "unit_cost_yuan_per_kwh": 1500, "battery_replacement_yuan": 2500000, "total_lifetime_investment_yuan": 10000000},
        "revenue_streams": [
            {"name": "峰谷套利", "annual_revenue_yuan": 720000, "description": "利用峰谷电价差（0.85 vs 0.30元/kWh）充放电"},
            {"name": "需量管理", "annual_revenue_yuan": 240000, "description": "削减峰值负荷降低基本电费"},
            {"name": "辅助服务", "annual_revenue_yuan": 180000, "description": "参与电网调频辅助服务"},
            {"name": "碳减排收益", "annual_revenue_yuan": 60000, "description": "减少弃光，增加绿电消纳"},
        ],
        "total_annual_revenue_yuan": 1200000, "annual_om_cost_yuan": 150000,
        "financial_indicators": {"irr_percent": 10.2, "npv_yuan": 2200000, "payback_period_years": 7.2, "roi_percent": 10.5, "lcos_yuan_per_kwh": 0.40},
        "scenario_analysis": {
            "optimistic": {"irr_percent": 14.5, "payback_years": 4.8, "assumption": "电价差扩大至1.0元/kWh"},
            "baseline": {"irr_percent": 10.2, "payback_years": 7.2, "assumption": "当前电价差和政策环境"},
            "pessimistic": {"irr_percent": 4.5, "payback_years": 10.5, "assumption": "电价差缩小至0.3元/kWh"},
        },
    }


def generate_comprehensive_economics():
    return {
        "project": {"name": "零碳园区综合能源项目", "components": ["光伏发电", "储能系统", "能源管理系统", "碳管理平台"], "analysis_period_years": 20},
        "total_investment": {"pv_system_yuan": 32000000, "storage_system_yuan": 7500000, "ems_platform_yuan": 2000000, "carbon_platform_yuan": 1500000, "other_yuan": 1000000, "total_yuan": 44000000},
        "annual_revenue": {"electricity_saving_yuan": 6600000, "carbon_trading_yuan": 400000, "ancillary_service_yuan": 200000, "green_certificate_yuan": 250000, "total_yuan": 7450000},
        "annual_cost": {"om_cost_yuan": 800000, "depreciation_yuan": 2200000, "total_yuan": 3000000},
        "annual_net_profit_yuan": 4450000,
        "financial_indicators": {"irr_percent": 11.5, "npv_yuan": 16000000, "payback_period_years": 7.5, "roi_percent": 12.8, "benefit_cost_ratio": 1.45},
        "carbon_benefit": {"annual_emission_reduction_tco2": 6000, "lifetime_emission_reduction_tco2": 120000, "carbon_cost_saving_yuan_per_year": 650000},
        "risk_assessment": {"overall_risk_level": "中低", "key_risks": [
            {"risk": "电价政策变化", "level": "中", "mitigation": "签订长期购电协议（PPA）"},
            {"risk": "光伏出力波动", "level": "低", "mitigation": "配置储能平滑出力"},
            {"risk": "碳价波动", "level": "中", "mitigation": "多元化碳资产管理策略"},
            {"risk": "技术迭代", "level": "低", "mitigation": "预留升级空间，采用模块化设计"},
        ]},
    }


# ── 生物质数据 ────────────────────────────────────────

def generate_chp_analysis():
    return {
        "project": {"name": "园区生物质热电联产（CHP）项目", "technology": "直接燃烧 + 蒸汽轮机", "feedstock": "农林废弃物、园区有机废弃物",
                    "capacity": {"electric_power_kw": 3000, "thermal_power_kw": 6000, "total_efficiency": 80.5}},
        "feedstock": {"annual_consumption_ton": 30000, "types": [
            {"name": "农林废弃物", "ratio": 0.55, "annual_ton": 16500},
            {"name": "园区有机废弃物", "ratio": 0.25, "annual_ton": 7500},
            {"name": "污泥", "ratio": 0.20, "annual_ton": 6000},
        ], "cost_yuan_per_ton": 200, "annual_feedstock_cost_yuan": 6000000},
        "production": {"annual_electricity_mwh": 22500, "annual_heat_gj": 58500, "capacity_factor": 0.85, "self_consumption_rate": 0.10},
        "economic": {"total_investment_yuan": 45000000, "annual_revenue": {"electricity_yuan": 13000000, "heat_yuan": 3500000, "subsidy_yuan": 2500000, "total_yuan": 19000000},
                     "annual_cost": {"feedstock_yuan": 6000000, "om_yuan": 2500000, "total_yuan": 8500000}, "irr_percent": 10.5, "payback_period_years": 7.5},
        "carbon_benefit": {"annual_carbon_reduction_tco2": 17500, "carbon_neutral": True, "note": "生物质燃烧排放的CO2被视为碳中和"},
        "environmental": {"ash_production_ton_per_year": 2000, "ash_utilization": "农业肥料", "emission_control": "布袋除尘 + SNCR脱硝",
                          "so2_emission_mg_per_nm3": 75.0, "nox_emission_mg_per_nm3": 175.0, "pm_emission_mg_per_nm3": 20.0},
    }


def generate_biogas_analysis():
    return {
        "project": {"name": "园区厌氧消化沼气工程", "technology": "中温厌氧消化（CSTR）", "feedstock": "有机废水、污泥、餐厨垃圾",
                    "capacity": {"daily_feedstock_ton": 100.0, "daily_biogas_production_nm3": 5000.0, "methane_content": 60.0}},
        "feedstock": {"types": [
            {"name": "有机废水", "ratio": 0.45, "daily_ton": 45.0, "ts_percent": 3},
            {"name": "剩余污泥", "ratio": 0.30, "daily_ton": 30.0, "ts_percent": 5},
            {"name": "餐厨垃圾", "ratio": 0.25, "daily_ton": 25.0, "ts_percent": 15},
        ], "annual_total_ton": 36500},
        "biogas_utilization": {"daily_biogas_nm3": 5000.0, "chp_electricity_kwh_per_day": 10000.0, "chp_heat_gj_per_day": 40.0,
                               "biogas_upgrading": {"biomethane_nm3_per_day": 2500.0, "biomethane_quality": "≥97% CH4", "grid_injection": True}},
        "digestate": {"daily_production_ton": 85.0, "utilization": "有机肥料", "nutrient_content": {"n_percent": 0.40, "p_percent": 0.15, "k_percent": 0.25}},
        "economic": {"total_investment_yuan": 28000000, "annual_revenue": {"electricity_yuan": 3000000, "biomethane_yuan": 3500000, "fertilizer_yuan": 650000, "waste_treatment_fee_yuan": 1250000, "total_yuan": 8400000},
                     "annual_cost_yuan": 4000000, "irr_percent": 9.5, "payback_period_years": 8.5},
        "carbon_benefit": {"methane_avoided_tco2e_per_year": 10000, "fossil_fuel_displaced_tco2_per_year": 6000, "fertilizer_displaced_tco2_per_year": 750, "total_carbon_reduction_tco2e_per_year": 16750},
        "operational_parameters": {"temperature_c": 37, "hrt_days": 20, "olr_kg_vs_per_m3_per_day": 3.0, "ph": 7.0, "vfa_mg_per_l": 1000, "alkalinity_mg_per_l": 4000},
    }


# ── 工业节能数据 ──────────────────────────────────────

def generate_industrial_energy():
    return {
        "overview": {
            "total_motors": 85, "annual_electricity_consumption_mwh": 12400,
            "motor_energy_ratio": 0.68, "compressed_air_annual_cost_yuan": 850000,
            "waste_heat_recoverable_kw": 1200,
        },
        "motors": [
            {"id": "M-001", "name": "冷却水泵", "rated_power_kw": 200, "efficiency_class": "IE3", "load_factor": 0.72, "annual_runtime_h": 8000, "annual_consumption_mwh": 1152, "saving_potential_kw": 15, "replacement_ie4_payback_years": 2.5},
            {"id": "M-002", "name": "空压机", "rated_power_kw": 350, "efficiency_class": "IE2", "load_factor": 0.85, "annual_runtime_h": 7500, "annual_consumption_mwh": 2231, "saving_potential_kw": 35, "replacement_ie4_payback_years": 1.8},
            {"id": "M-003", "name": "引风机", "rated_power_kw": 150, "efficiency_class": "IE3", "load_factor": 0.65, "annual_runtime_h": 8200, "annual_consumption_mwh": 800, "saving_potential_kw": 8, "replacement_ie4_payback_years": 3.2},
            {"id": "M-004", "name": "搅拌器", "rated_power_kw": 75, "efficiency_class": "IE1", "load_factor": 0.90, "annual_runtime_h": 8600, "annual_consumption_mwh": 581, "saving_potential_kw": 18, "replacement_ie4_payback_years": 1.5},
        ],
        "compressed_air": {
            "system_pressure_bar": 7.0, "leakage_rate_percent": 22.0,
            "leakage_cost_yuan_per_year": 187000, "recommended_pressure_bar": 6.0,
            "pressure_reduction_saving_yuan": 45000, "vfd_saving_potential_yuan": 120000,
        },
        "waste_heat_recovery": [
            {"source": "空压机余热", "temperature_c": 85, "recoverable_kw": 350, "utilization": "预热锅炉给水", "annual_saving_yuan": 280000},
            {"source": "烟气余热", "temperature_c": 250, "recoverable_kw": 520, "utilization": "ORC发电", "annual_saving_yuan": 450000},
            {"source": "工艺冷却水", "temperature_c": 45, "recoverable_kw": 180, "utilization": "供暖预热", "annual_saving_yuan": 95000},
            {"source": "烘干废气", "temperature_c": 120, "recoverable_kw": 150, "utilization": "新风预热", "annual_saving_yuan": 72000},
        ],
        "vfd_analysis": [
            {"motor_id": "M-001", "current_control": "节流阀", "vfd_saving_percent": 30, "vfd_investment_yuan": 85000, "annual_saving_yuan": 52000, "payback_years": 1.6},
            {"motor_id": "M-002", "current_control": "启停控制", "vfd_saving_percent": 25, "vfd_investment_yuan": 120000, "annual_saving_yuan": 78000, "payback_years": 1.5},
            {"motor_id": "M-003", "current_control": "导叶调节", "vfd_saving_percent": 20, "vfd_investment_yuan": 65000, "annual_saving_yuan": 28000, "payback_years": 2.3},
        ],
        "recommendations": [
            {"action": "M-002 空压机升级 IE4", "investment_yuan": 350000, "annual_saving_yuan": 210000, "payback_years": 1.7, "priority": "high"},
            {"action": "M-004 搅拌器升级 IE4", "investment_yuan": 120000, "annual_saving_yuan": 95000, "payback_years": 1.3, "priority": "high"},
            {"action": "压缩空气泄漏检测修复", "investment_yuan": 50000, "annual_saving_yuan": 150000, "payback_years": 0.3, "priority": "critical"},
            {"action": "空压机余热回收（预热锅炉给水）", "investment_yuan": 200000, "annual_saving_yuan": 280000, "payback_years": 0.7, "priority": "high"},
            {"action": "烟气余热ORC发电", "investment_yuan": 1800000, "annual_saving_yuan": 450000, "payback_years": 4.0, "priority": "medium"},
            {"action": "M-001 加装VFD", "investment_yuan": 85000, "annual_saving_yuan": 52000, "payback_years": 1.6, "priority": "high"},
        ],
    }


# ── CCUS数据 ──────────────────────────────────────────

def generate_ccus():
    return {
        "project": {"name": "园区碳捕集利用与封存（CCUS）项目", "target_emission_source": "燃煤锅炉烟气", "co2_concentration_percent": 12.5},
        "capture": {
            "technology": "化学吸收法（胺法）", "capture_rate_percent": 90.0,
            "capture_capacity_tco2_per_year": 50000, "energy_penalty_kwh_per_tco2": 280,
            "amine_degradation_kg_per_tco2": 1.2, "capture_cost_yuan_per_tco2": 280,
        },
        "transport": {
            "method": "管道输送", "distance_km": 15, "transport_cost_yuan_per_tco2": 25,
            "pipeline_diameter_mm": 200, "pressure_mpa": 10,
        },
        "utilization": [
            {"path": "化工利用（合成甲醇）", "capacity_tco2_per_year": 20000, "product": "甲醇", "revenue_yuan_per_tco2": 800, "technology_readiness": "TRL 7"},
            {"path": "矿化利用（建材）", "capacity_tco2_per_year": 15000, "product": "轻质碳酸钙", "revenue_yuan_per_tco2": 500, "technology_readiness": "TRL 8"},
            {"path": "生物利用（微藻固碳）", "capacity_tco2_per_year": 5000, "product": "藻粉/生物柴油", "revenue_yuan_per_tco2": 1200, "technology_readiness": "TRL 6"},
        ],
        "storage": {
            "method": "咸水层封存", "capacity_tco2_per_year": 10000, "storage_cost_yuan_per_tco2": 80,
            "monitoring": "4D地震 + 井下监测", "leakage_risk": "低（<0.1%/年）",
        },
        "economic": {
            "total_investment_yuan": 120000000, "annual_capture_cost_yuan": 14000000,
            "annual_transport_cost_yuan": 1250000, "annual_utilization_revenue_yuan": 22000000,
            "annual_storage_cost_yuan": 800000, "annual_net_cost_yuan": -5950000,
            "irr_percent": 8.5, "payback_period_years": 9.5,
        },
        "carbon_benefit": {
            "net_carbon_reduction_tco2_per_year": 45000, "carbon_credit_value_yuan_per_year": 2700000,
            "contribution_to_zero_carbon_percent": 65,
        },
    }


# ── 共享储能数据 ──────────────────────────────────────

def generate_shared_storage():
    return {
        "market_analysis": {"total_shared_capacity_kwh": 20000, "subscribed_users": 8, "utilization_rate": 0.75, "monthly_revenue_yuan": 120000},
        "business_models": [
            {"model": "容量租赁", "description": "园区企业按需租赁储能容量", "unit_price_yuan_per_kwh_month": 80, "estimated_annual_revenue_yuan": 960000, "pros": "收入稳定，客户粘性高", "cons": "需要较大初始投资"},
            {"model": "辅助服务", "description": "参与电网调频、调峰辅助服务", "unit_price_yuan_per_kw": 150, "estimated_annual_revenue_yuan": 540000, "pros": "利润空间大，政策支持", "cons": "技术要求高，调度复杂"},
            {"model": "峰谷套利", "description": "利用峰谷电价差充放电套利", "daily_cycles": 2, "estimated_annual_revenue_yuan": 720000, "pros": "模式成熟，风险可控", "cons": "依赖电价差，政策风险"},
        ],
        "recommendation": {"best_model": "容量租赁 + 峰谷套利", "expected_roi_years": 4.5, "irr_percent": 15.2, "payback_period_years": 5.2, "carbon_benefit_tco2_per_year": 1200},
    }


# ── 水质数据 ──────────────────────────────────────────

def generate_water_realtime(device_id="WQ-001"):
    """生成水质实时数据（单条最新记录）"""
    base = {"WQ-001": {"cod": 185.5, "ammonia": 16.2, "nitrate": 1.75, "ph": 7.15, "temp": 24.8, "do": 3.8, "inflow": 780.0, "sludge": 4520.0},
            "WQ-002": {"cod": 172.3, "ammonia": 14.8, "nitrate": 1.62, "ph": 7.22, "temp": 25.1, "do": 4.1, "inflow": 720.0, "sludge": 4380.0}}
    b = base.get(device_id, base["WQ-001"])
    return {
        "device_id": device_id,
        "timestamp": _now.isoformat(),
        "cod": b["cod"],
        "ammonia_nitrogen": b["ammonia"],
        "nitrate_nitrogen": b["nitrate"],
        "ph": b["ph"],
        "temperature": b["temp"],
        "dissolved_oxygen": b["do"],
        "inflow_rate": b["inflow"],
        "sludge_conc": b["sludge"],
        "source": "simulated",
    }


def generate_water_history(device_id="WQ-001", hours=168):
    """生成水质历史数据（逐小时）"""
    base = {"WQ-001": {"cod": 200, "ammonia": 18, "nitrate": 1.8, "ph": 7.2, "temp": 25, "do": 3.5, "inflow": 800, "sludge": 4500},
            "WQ-002": {"cod": 180, "ammonia": 16, "nitrate": 1.6, "ph": 7.3, "temp": 24, "do": 3.8, "inflow": 750, "sludge": 4300}}
    b = base.get(device_id, base["WQ-001"])
    records = []
    for i in range(hours):
        t = _now - timedelta(hours=hours - 1 - i)
        hour_angle = t.hour * np.pi / 12
        daily = np.sin(hour_angle)
        records.append({
            "timestamp": t.isoformat(),
            "cod": round(b["cod"] + 60 * daily * 0.15 + rng.normal(0, 3), 1),
            "ammonia_nitrogen": round(b["ammonia"] + 8 * daily * 0.15 + rng.normal(0, 0.5), 2),
            "nitrate_nitrogen": round(b["nitrate"] + 0.8 * daily * 0.15 + rng.normal(0, 0.05), 2),
            "ph": round(b["ph"] + rng.normal(0, 0.1), 2),
            "temperature": round(b["temp"] + 3 * daily + rng.normal(0, 0.3), 1),
            "dissolved_oxygen": round(b["do"] + rng.normal(0, 0.2), 2),
            "inflow_rate": round(b["inflow"] + 200 * daily * 0.15 + rng.normal(0, 15), 1),
            "sludge_conc": round(b["sludge"] + rng.normal(0, 80), 0),
        })
    return records


def generate_water_prediction(device_id="WQ-001", horizon=24):
    """生成水质预测数据（未来24h）"""
    base = {"WQ-001": 200, "WQ-002": 180}
    b = base.get(device_id, 200)
    preds = []
    for i in range(horizon):
        t = _now + timedelta(hours=i + 1)
        cod_trend = 60 * np.sin(i * np.pi / 12) * 0.15
        preds.append({
            "target_timestamp": t.isoformat(),
            "cod": round(b + cod_trend + rng.normal(0, 3), 1),
            "ammonia_nitrogen": round(18 + 0.3 * cod_trend + rng.normal(0, 0.5), 2),
            "nitrate_nitrogen": round(1.8 + 0.05 * cod_trend + rng.normal(0, 0.05), 2),
        })
    return preds


# ── 园区数据（park_service 用） ─────────────────────────

def generate_park_hourly_trend(hours=24):
    """生成园区逐小时趋势数据"""
    trend = []
    pv_f = generate_pv_forecast()
    wind_f = generate_wind_forecast()
    load_f = generate_load_forecast()
    price_f = generate_grid_price()
    soc = 62.5
    for i in range(hours):
        hour = (_now - timedelta(hours=hours - 1 - i)).strftime("%Y-%m-%d %H:00")
        pv = pv_f[i]["power_kw"] if i < len(pv_f) else 0
        wind = wind_f[i]["power_kw"] if i < len(wind_f) else 0
        load = load_f[i] if i < len(load_f) else 4500
        renewable = pv + wind
        net = renewable - load
        if net > 0:
            charge = min(net * 0.8, 2500)
            discharge = 0
            grid = 0
        else:
            discharge = min(abs(net) * 0.6, 2500)
            grid = round(abs(net) - discharge, 1)
            charge = 0
        soc += (charge * 0.92 - discharge / 0.92) / 5000 * 100
        soc = max(20, min(90, soc))
        trend.append({
            "time": hour,
            "pv_power_kw": round(pv, 1),
            "wind_power_kw": round(wind, 1),
            "load_power_kw": round(load, 1),
            "storage_power_kw": round(charge - discharge, 1),
            "grid_power_kw": round(grid, 1),
            "soc": round(soc, 1),
            "carbon_tco2": round(grid * 0.581 / 1000, 4),
            "electricity_price": price_f[i] if i < len(price_f) else 0.55,
            "renewable_ratio": round(renewable / load * 100, 1) if load > 0 else 0,
        })
    return trend


def generate_park_snapshot():
    """生成园区静态快照"""
    pv_f = generate_pv_forecast()
    wind_f = generate_wind_forecast()
    pv_now = pv_f[_now.hour % 24]["power_kw"]
    wind_now = wind_f[_now.hour % 24]["power_kw"]
    return {
        "timestamp": _now.isoformat(),
        "generation": {
            "pv": {"id": "PV-001", "name": "1号光伏电站", "capacity_kw": 5000, "current_power_kw": pv_now, "status": "running", "generation_today_kwh": 15200.0},
            "wind": {"id": "WIND-001", "name": "1号风力发电场", "capacity_kw": 3000, "current_power_kw": wind_now, "status": "running", "generation_today_kwh": 8500.0},
            "biomass_chp": {"id": "BIO-001", "name": "生物质CHP", "capacity_kw": 3000, "current_electric_kw": 2100.0, "current_thermal_kw": 4200.0, "total_efficiency": 80.5},
            "total_renewable_kw": round(pv_now + wind_now, 1),
            "total_generation_kw": round(pv_now + wind_now + 2100.0, 1),
        },
        "storage": {
            "id": "BAT-001", "name": "1号锂电池储能系统", "capacity_kwh": 5000, "rated_power_kw": 2500,
            "current_soc": 62.5, "current_power_kw": 850.0, "mode": "charging",
            "state_of_health": 95.2, "temperature_c": 28.5, "cycle_count": 1200,
            "available_energy_kwh": 3125.0, "remaining_charge_kwh": 1875.0, "remaining_discharge_kwh": 2125.0,
        },
        "grid": {
            "id": "GRID-001", "name": "10kV市电馈线", "voltage_kv": 10.0,
            "current_power_kw": 2800.0, "is_importing": True,
            "emission_factor": 0.581, "max_import_kw": 10000, "max_export_kw": 8000,
            "current_emission_tco2_per_h": 1.627,
        },
        "loads": {
            "total_power_kw": 4800.0,
            "breakdown": [
                {"id": "LOAD-001", "name": "关键生产线", "type": "critical", "current_power_kw": 1200.0, "flexibility": "fixed"},
                {"id": "LOAD-002", "name": "制造车间", "type": "manufacturing", "current_power_kw": 950.0, "flexibility": "shiftable"},
                {"id": "LOAD-003", "name": "HVAC系统", "type": "hvac", "current_power_kw": 680.0, "flexibility": "flexible"},
                {"id": "LOAD-004", "name": "照明系统", "type": "lighting", "current_power_kw": 320.0, "flexibility": "flexible"},
                {"id": "LOAD-005", "name": "充电桩", "type": "ev_charging", "current_power_kw": 450.0, "flexibility": "shiftable"},
                {"id": "LOAD-006", "name": "污水处理", "type": "wastewater", "current_power_kw": 380.0, "flexibility": "shiftable"},
                {"id": "LOAD-007", "name": "数据中心", "type": "data_center", "current_power_kw": 520.0, "flexibility": "flexible"},
                {"id": "LOAD-008", "name": "办公区", "type": "office", "current_power_kw": 300.0, "flexibility": "flexible"},
            ],
            "critical_load_kw": 1200.0,
            "flexible_load_kw": 3600.0,
            "demand_response_capacity_kw": 2160.0,
        },
        "micro_grid": {
            "id": "MG-001", "name": "园区微电网", "total_generation_kw": round(pv_now + wind_now + 2100.0, 1),
            "total_load_kw": 4800.0, "total_storage_power_kw": 850.0,
            "grid_power_kw": 2800.0, "power_balance": 50.0, "is_balanced": True,
            "self_sufficiency_rate": 41.7, "renewable_ratio": 41.0,
            "status": "grid_connected",
        },
        "carbon": {
            "current_emission_tco2_per_h": 2.85,
            "carbon_offset_tco2_per_h": 1.68,
            "net_emission_tco2_per_h": 1.17,
            "renewable_ratio": 41.0,
            "total_emission_today_tco2": 18.5,
            "scope_breakdown": {
                "scope_1": {"emission_tco2": 1.22, "name": "直接排放", "sources": ["锅炉", "工艺排放", "柴油发电机"]},
                "scope_2": {"emission_tco2": 1.05, "name": "外购电力", "sources": ["电网购电"]},
                "scope_3": {"emission_tco2": 0.58, "name": "其他间接", "sources": ["供应链运输", "员工通勤", "废弃物处理"]},
            },
            "carbon_offset_tco2": 1.68,
            "assets": {
                "total_value_yuan": 2985000.00,
                "compliance": {"carbon_quota_tco2": 5000, "total_emission_tco2": 3432.49, "compliance_gap_tco2": -1567.51, "is_compliant": True},
                "recommendation": "配额充足，可出售盈余",
            },
        },
        "alerts": {
            "total_alerts": 2, "critical": 0, "warning": 2, "info": 0,
            "system_status": "warning",
            "items": [
                {"node_id": "PV-001", "node_type": "pv", "level": "warning", "message": "当前时刻光伏出力偏低（容量因子23.3%），建议检查", "value": 23.3, "threshold": 30.0, "timestamp": _now.isoformat(), "acknowledged": False},
                {"node_id": "SYS-001", "node_type": "system", "level": "warning", "message": "可再生能源占比41.0%，低于目标50%", "value": 41.0, "threshold": 50.0, "timestamp": _now.isoformat(), "acknowledged": False},
            ],
        },
        "economics": {
            "current_electricity_price_yuan_per_kwh": 0.55,
            "current_cost_yuan_per_h": 2640.0,
            "renewable_saving_yuan_per_h": 2255.0,
        },
    }


def generate_park_nodes():
    """生成园区节点列表"""
    return {
        "total_nodes": 12,
        "nodes": [
            {"id": "PV-001", "name": "1号光伏电站", "type": "solar", "category": "generation", "capacity_kw": 5000, "current_power_kw": 1165.5, "status": "running"},
            {"id": "WIND-001", "name": "1号风力发电场", "type": "wind", "category": "generation", "capacity_kw": 3000, "current_power_kw": 900.0, "status": "running"},
            {"id": "BIO-001", "name": "生物质CHP", "type": "biomass_chp", "category": "generation", "capacity_kw": 3000, "current_power_kw": 2100.0, "status": "running"},
            {"id": "GRID-001", "name": "10kV市电馈线", "type": "grid", "category": "grid", "capacity_kw": 10000, "current_power_kw": 2800.0, "status": "online"},
            {"id": "BAT-001", "name": "1号锂电池储能系统", "type": "battery", "category": "storage", "capacity_kwh": 5000, "current_soc": 62.5, "status": "charging"},
            {"id": "LOAD-001", "name": "关键生产线", "type": "critical", "category": "load", "current_power_kw": 1200.0, "status": "running"},
            {"id": "LOAD-002", "name": "制造车间", "type": "manufacturing", "category": "load", "current_power_kw": 950.0, "status": "running"},
            {"id": "LOAD-003", "name": "HVAC系统", "type": "hvac", "category": "load", "current_power_kw": 680.0, "status": "running"},
            {"id": "LOAD-004", "name": "照明系统", "type": "lighting", "category": "load", "current_power_kw": 320.0, "status": "running"},
            {"id": "LOAD-005", "name": "充电桩", "type": "ev_charging", "category": "load", "current_power_kw": 450.0, "status": "running"},
            {"id": "LOAD-006", "name": "污水处理", "type": "wastewater", "category": "load", "current_power_kw": 380.0, "status": "running"},
            {"id": "LOAD-007", "name": "数据中心", "type": "data_center", "category": "load", "current_power_kw": 520.0, "status": "running"},
        ],
    }


def generate_park_power_flow():
    """生成园区功率流向"""
    pv_f = generate_pv_forecast()
    wind_f = generate_wind_forecast()
    pv_now = pv_f[_now.hour % 24]["power_kw"]
    wind_now = wind_f[_now.hour % 24]["power_kw"]
    renewable = pv_now + wind_now
    total_load = 4800.0
    total_gen = renewable + 2100.0 + 2800.0
    return {
        "generation": {
            "pv_kw": pv_now, "wind_kw": wind_now, "biomass_chp_kw": 2100.0,
            "grid_import_kw": 2800.0, "total_kw": total_gen,
        },
        "consumption": {
            "load_kw": total_load, "storage_charge_kw": 850.0, "grid_export_kw": 0.0, "total_kw": total_load + 850.0,
        },
        "balance": {
            "power_gap_kw": round(total_gen - total_load - 850.0, 1),
            "renewable_ratio": round(renewable / total_load * 100, 1) if total_load > 0 else 0,
            "self_sufficiency": round(renewable / total_load * 100, 1) if total_load > 0 else 0,
        },
        "flows": [
            {"from": "光伏", "to": "负荷", "power_kw": round(pv_now, 1), "type": "renewable"},
            {"from": "风电", "to": "负荷", "power_kw": round(wind_now, 1), "type": "renewable"},
            {"from": "生物质CHP", "to": "负荷", "power_kw": 2100.0, "type": "carbon_neutral"},
            {"from": "电网", "to": "负荷", "power_kw": 2800.0, "type": "grid"},
            {"from": "电网", "to": "储能", "power_kw": 850.0, "type": "charging"},
        ],
    }


def generate_park_vpp():
    """生成VPP聚合状态"""
    return {
        "vpp_id": "VPP-ZC-001",
        "aggregated_capacity_mw": 12.18,
        "breakdown": {
            "renewable_generation_mw": 8.0,
            "energy_storage_mw": 5.0,
            "flexible_load_mw": 3.6,
            "grid_connection_mw": 10.0,
        },
        "current_operation": {
            "total_power_mw": 6.5,
            "renewable_ratio": 48.0,
            "dispatchable_power_mw": 3.8,
            "status": "online",
        },
        "market_participation": {
            "spot_market": "active",
            "ancillary_service": "registered",
            "demand_response": "active",
            "capacity_market": "pending",
        },
        "flexible_resources": {
            "total_demand_response_capacity_kw": 2160.0,
            "shiftable_load_kw": 1780.0,
            "curtailable_load_kw": 380.0,
            "storage_dispatchable_kw": 2500.0,
            "estimated_annual_revenue_yuan": 648480.0,
        },
    }


# ── 主入口 ────────────────────────────────────────────

def main():
    print("Generating mock data files...")
    print()

    # 能源模块
    print("[energy]")
    save_json("energy", "energy_status.json", generate_energy_status())
    save_json("energy", "pv_forecast.json", generate_pv_forecast())
    save_json("energy", "wind_forecast.json", generate_wind_forecast())
    save_json("energy", "load_forecast.json", generate_load_forecast())
    save_json("energy", "grid_price.json", generate_grid_price())

    # 碳排放模块
    print("[carbon]")
    save_json("carbon", "scope_emissions.json", generate_scope_emissions())
    save_json("carbon", "carbon_portfolio.json", generate_carbon_portfolio())
    save_json("carbon", "trading_strategy.json", generate_trading_strategy())
    save_json("carbon", "carbon_trend_30d.json", generate_carbon_trend(30))
    for pt in ["steel", "aluminum", "cement", "fertilizer"]:
        save_json("carbon", f"cbam_report_{pt}.json", generate_cbam_report(pt))

    # 评价模块
    print("[evaluation]")
    save_json("evaluation", "indicators.json", generate_evaluation())
    save_json("evaluation", "cert_progress.json", generate_cert_progress())

    # 经济性模块
    print("[economic]")
    save_json("economic", "pv_economics.json", generate_pv_economics())
    save_json("economic", "storage_economics.json", generate_storage_economics())
    save_json("economic", "comprehensive_economics.json", generate_comprehensive_economics())

    # 生物质模块
    print("[biomass]")
    save_json("biomass", "chp_analysis.json", generate_chp_analysis())
    save_json("biomass", "biogas_analysis.json", generate_biogas_analysis())

    # 工业节能模块
    print("[industrial]")
    save_json("industrial", "industrial_energy.json", generate_industrial_energy())

    # CCUS模块
    print("[ccus]")
    save_json("ccus", "ccus_analysis.json", generate_ccus())

    # 储能模块
    print("[storage]")
    save_json("storage", "shared_storage.json", generate_shared_storage())

    # 园区模块
    print("[park]")
    save_json("park", "snapshot.json", generate_park_snapshot())
    save_json("park", "nodes.json", generate_park_nodes())
    save_json("park", "power_flow.json", generate_park_power_flow())
    save_json("park", "vpp_aggregation.json", generate_park_vpp())
    save_json("park", "hourly_trend.json", generate_park_hourly_trend(24))

    # 水质模块
    print("[water]")
    for dev_id in ["WQ-001", "WQ-002"]:
        save_json("water", f"realtime_{dev_id}.json", generate_water_realtime(dev_id))
        save_json("water", f"history_{dev_id}.json", generate_water_history(dev_id, 168))
        save_json("water", f"prediction_{dev_id}.json", generate_water_prediction(dev_id, 24))

    print()
    print(f"All data files generated in: {DATA_DIR}")


if __name__ == "__main__":
    main()