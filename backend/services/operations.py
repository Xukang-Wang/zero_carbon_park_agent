"""Source-backed analytics and constrained dispatch; all power is kW, energy kWh.

The strategy is a transparent hourly heuristic, not a claim of global optimality.
Every horizon ends at its initial SOC to prevent fictitious battery benefits.
"""
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "operations.json"


def read_source():
    raw = SOURCE.read_bytes()
    data = json.loads(raw)
    data["fingerprint"] = hashlib.sha256(raw).hexdigest()[:16]
    return data


def quality(data):
    rows = data["records"]
    issues, seen = [], set()
    if data.get("interval_hours") != 1:
        issues.append("当前模型只支持 1 小时采样间隔")
    if not data.get("is_simulated"):
        issues.append("此工作台仅接受明确标注的模拟数据")
    a = data.get("assumptions", {})
    for key in ("grid_kgco2_kwh", "gas_kgco2_m3", "battery_capacity_kwh", "battery_power_kw", "degradation_cny_kwh", "export_cny_kwh", "grid_limit_kw"):
        value = a.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            issues.append(f"模型参数 {key} 必须为有限非负值")
    for key in ("charge_efficiency", "discharge_efficiency"):
        value = a.get(key)
        if not isinstance(value, (int, float)) or not 0 < value <= 1:
            issues.append(f"效率参数 {key} 必须在 (0, 1] 范围")
    try:
        if not 0 <= a["soc_min"] <= a["soc_initial"] <= a["soc_max"] <= 1:
            issues.append("SOC 参数必须满足 0 ≤ 最低 ≤ 初始 ≤ 最高 ≤ 1")
    except (KeyError, TypeError):
        issues.append("SOC 参数缺失或无效")
    previous = None
    fields = ("load_kw", "pv_kw", "wind_kw", "price_cny_kwh", "gas_m3", "water_m3", "reused_water_m3")
    for i, row in enumerate(rows):
        stamp = row.get("timestamp")
        if stamp in seen:
            issues.append(f"第 {i + 1} 行时间戳重复")
        seen.add(stamp)
        try:
            current = datetime.fromisoformat(stamp)
            if current.utcoffset() is None or current.utcoffset().total_seconds() != 28800:
                issues.append(f"第 {i + 1} 行必须使用 +08:00 时区")
            if previous and (current - previous).total_seconds() != 3600:
                issues.append(f"第 {i + 1} 行小时采样不连续")
            previous = current
        except (TypeError, ValueError):
            issues.append(f"第 {i + 1} 行时间戳无效")
        for field in fields:
            value = row.get(field)
            if not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
                issues.append(f"第 {i + 1} 行 {field} 无效")
        if isinstance(row.get("water_m3"), (int, float)) and isinstance(row.get("reused_water_m3"), (int, float)) and row["reused_water_m3"] > row["water_m3"]:
            issues.append(f"第 {i + 1} 行回用水量大于总用水量")
    if not rows:
        issues.append("数据集为空")
    return {"valid": not issues, "rows": len(rows), "issues": issues[:30], "issue_count": len(issues), "checks": ["字段完整与有限值", "时间唯一与小时连续", "非负约束", "水量边界"]}


def dispatch(rows, a, strategy="balanced", pv_scale=1, load_scale=1, capacity=None):
    capacity = capacity if capacity is not None else a["battery_capacity_kwh"]
    energy = initial = capacity * a["soc_initial"]
    low, high = capacity * a["soc_min"], capacity * a["soc_max"]
    power, ce, de = a["battery_power_kw"], a["charge_efficiency"], a["discharge_efficiency"]
    result = []
    for i, row in enumerate(rows):
        load, pv, wind = row["load_kw"] * load_scale, row["pv_kw"] * pv_scale, row["wind_kw"]
        net = load - pv - wind
        charge = discharge = 0.
        if strategy != "baseline":
            if net < 0 or (strategy != "carbon" and row["price_cny_kwh"] <= .35):
                charge = min(power, max(0, (high - energy) / ce), -net if net < 0 else power)
            elif net > 0 and (strategy == "carbon" or row["price_cny_kwh"] >= 1 or (strategy == "balanced" and net > 3200)):
                discharge = min(power, net, max(0, (energy - low) * de))
            # Reserve sufficient remaining power to recover the initial SOC.
            remaining = len(rows) - i - 1
            floor = max(low, initial - remaining * power * ce)
            ceiling = min(high, initial + remaining * power / de)
            proposed = energy + charge * ce - discharge / de
            target = min(ceiling, max(floor, proposed))
            charge = max(0., (target - energy) / ce)
            discharge = max(0., (energy - target) * de)
            energy = target
        grid = net + charge - discharge
        imported, exported = max(0, grid), max(0, -grid)
        cost = imported * row["price_cny_kwh"] - exported * a["export_cny_kwh"] + (charge + discharge) * a["degradation_cny_kwh"]
        result.append({**row, "load_kw": load, "pv_kw": pv, "charge_kw": charge, "discharge_kw": discharge,
                       "grid_import_kw": imported, "grid_export_kw": exported, "soc": energy / capacity * 100 if capacity else 0,
                       "cost_cny": cost, "scope1_kg": row["gas_m3"] * a["gas_kgco2_m3"],
                       "scope2_kg": imported * a["grid_kgco2_kwh"],
                       "balance_error_kw": pv + wind + imported + discharge - load - charge - exported})
    return result


def summarize(rows):
    total = lambda key: sum(r[key] for r in rows)
    renewable = total("pv_kw") + total("wind_kw")
    return {"load_mwh": total("load_kw") / 1000, "renewable_mwh": renewable / 1000,
            "grid_mwh": total("grid_import_kw") / 1000, "export_mwh": total("grid_export_kw") / 1000,
            "cost_cny": total("cost_cny"), "scope1_t": total("scope1_kg") / 1000,
            "scope2_t": total("scope2_kg") / 1000, "carbon_t": (total("scope1_kg") + total("scope2_kg")) / 1000,
            "renewable_ratio": min(100, renewable / total("load_kw") * 100) if total("load_kw") else 0,
            "self_consumption": (1 - total("grid_export_kw") / renewable) * 100 if renewable else 0,
            "peak_kw": max(r["grid_import_kw"] for r in rows),
            "water_reuse": total("reused_water_m3") / total("water_m3") * 100 if total("water_m3") else 0,
            "max_balance_error_kw": max(abs(r["balance_error_kw"]) for r in rows)}


def select_rows(data, day=None, days=1):
    report = quality(data)
    if not report["valid"]:
        raise ValueError("源数据校验失败：" + "; ".join(report["issues"][:3]))
    dates = sorted({r["timestamp"][:10] for r in data["records"]})
    day = day or dates[-1]
    if day not in dates:
        raise ValueError("所选日期没有模拟数据")
    end = dates.index(day) + 1
    selected = dates[max(0, end - days):end]
    rows = [r for r in data["records"] if r["timestamp"][:10] in selected]
    if len(rows) != len(selected) * 24:
        raise ValueError("分析窗口必须包含完整的 24 小时采样")
    return rows, dates


def overview(day=None, days=1):
    data = read_source()
    rows, dates = select_rows(data, day, days)
    plan = dispatch(rows, data["assumptions"])
    baseline = summarize(dispatch(rows, data["assumptions"], "baseline"))
    summary = summarize(plan)
    daily = []
    for date in sorted({r["timestamp"][:10] for r in plan}):
        daily.append({"date": date, **summarize([r for r in plan if r["timestamp"].startswith(date)])})
    return {"park_name": data["park_name"], "simulated": True, "dates": dates, "quality": quality(data),
            "source": "data/operations.json", "fingerprint": data["fingerprint"], "assumptions": data["assumptions"],
            "period": {"start": rows[0]["timestamp"], "end": rows[-1]["timestamp"], "hours": len(rows)},
            "summary": summary, "baseline": baseline, "series": plan, "daily": daily, "assets": data["assets"],
            "savings_cny": baseline["cost_cny"] - summary["cost_cny"],
            "alerts": alerts(plan, data["assumptions"])}


def alerts(rows, assumptions):
    result = []
    peak = max(rows, key=lambda r: r["grid_import_kw"])
    if peak["grid_import_kw"] > assumptions["grid_limit_kw"] * .8:
        result.append({"severity": "warning", "title": "电网接入容量接近边界", "detail": f"峰值购电 {peak['grid_import_kw']:.0f} kW，接入上限 {assumptions['grid_limit_kw']:.0f} kW", "owner": "风险复核 Agent"})
    exported = sum(r["grid_export_kw"] for r in rows)
    if exported > 0:
        result.append({"severity": "info", "title": "存在新能源余电外送", "detail": f"窗口外送 {exported / 1000:.2f} MWh，可评估可转移负荷与储能扩容", "owner": "能源调度 Agent"})
    result.append({"severity": "info", "title": "当前为离线模拟数据", "detail": "数据时间以所选窗口为准；所有策略仅用于仿真分析。", "owner": "数据质量 Agent"})
    return result


def scenario(day, strategy, pv_scale, load_scale, capacity):
    data = read_source()
    rows, _ = select_rows(data, day)
    base = summarize(dispatch(rows, data["assumptions"], "baseline", pv_scale, load_scale, capacity))
    plan = dispatch(rows, data["assumptions"], strategy, pv_scale, load_scale, capacity)
    summary = summarize(plan)
    return {"baseline": base, "summary": summary, "series": plan, "savings_cny": base["cost_cny"] - summary["cost_cny"],
            "carbon_saving_t": base["carbon_t"] - summary["carbon_t"], "alerts": alerts(plan, data["assumptions"]),
            "parameters": {"day": rows[0]["timestamp"][:10], "strategy": strategy, "pv_scale": pv_scale, "load_scale": load_scale, "capacity_kwh": capacity},
            "source_fingerprint": data["fingerprint"], "method": "逐小时约束启发式；同情景无储能基线；期末 SOC 回归初始值；成本含充放电吞吐衰减费，不含投资、需量与辅助服务收益。"}
