"""Dependency-aware analytical agents with immutable evidence and persisted traces.

These agents are deterministic domain workers, not simulated LLM conversations.
Independent nodes execute concurrently; every edge is an actual input dependency.
"""
import json
import sqlite3
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from backend.services.operations import read_source, select_rows, quality, dispatch, summarize

DB = Path(__file__).resolve().parents[2] / "data" / "operations_runs.db"
AGENTS = [
    {"id": "quality", "name": "数据质量", "role": "验证采样、完整性与物理边界", "depends": [], "x": 110, "y": 210},
    {"id": "forecast", "name": "负荷预测", "role": "近 7 日同小时均值预测与留出日检验", "depends": ["quality"], "x": 320, "y": 105},
    {"id": "carbon", "name": "碳核算", "role": "核算无储能基线 Scope 1 / 2", "depends": ["quality"], "x": 320, "y": 315},
    {"id": "dispatch", "name": "能源调度", "role": "预测驱动源荷储逐小时平衡", "depends": ["forecast"], "x": 540, "y": 105},
    {"id": "economics", "name": "经济评估", "role": "同口径无储能基线成本对比", "depends": ["dispatch", "carbon"], "x": 750, "y": 315},
    {"id": "risk", "name": "风险复核", "role": "校验功率、SOC、期末能量与并网约束", "depends": ["dispatch"], "x": 750, "y": 105},
    {"id": "report", "name": "决策报告", "role": "汇总证据，生成可解释策略结论", "depends": ["economics", "risk"], "x": 960, "y": 210},
]


@contextmanager
def connect():
    conn = sqlite3.connect(DB, timeout=15)
    try:
        with conn:
            conn.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created_at TEXT, status TEXT, payload TEXT)")
            yield conn
    finally:
        conn.close()


def save(run):
    with connect() as conn:
        conn.execute("INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?)", (run["id"], run["created_at"], run["status"], json.dumps(run, ensure_ascii=False)))


def history():
    with connect() as conn:
        return [{"id": r[0], "created_at": r[1], "status": r[2]} for r in conn.execute("SELECT id, created_at, status FROM runs ORDER BY created_at DESC LIMIT 20")]


def get_run(run_id):
    with connect() as conn:
        row = conn.execute("SELECT payload FROM runs WHERE id = ?", (run_id,)).fetchone()
    return json.loads(row[0]) if row else None


def execute(day=None, strategy="balanced"):
    data = read_source()
    rows, _ = select_rows(data, day)
    a = data["assumptions"]
    run = {"id": uuid.uuid4().hex, "created_at": datetime.now(timezone.utc).isoformat(), "status": "running",
           "mode": "deterministic", "day": rows[0]["timestamp"][:10], "strategy": strategy,
           "source": "data/operations.json", "source_fingerprint": data["fingerprint"],
           "model_version": "hourly-heuristic-v1", "assumptions": a, "events": [], "outputs": {}}
    save(run)
    started = time.perf_counter()
    outputs = run["outputs"]

    def work(node):
        if node == "quality":
            return quality(data)
        if node == "forecast":
            before = [r for r in data["records"] if r["timestamp"][:10] < run["day"]][-168:]
            if len(before) < 24:
                raise ValueError("预测至少需要 1 个完整历史日，请选择较晚日期")
            predicted = []
            for row in rows:
                peers = [r for r in before if r["timestamp"][11:13] == row["timestamp"][11:13]]
                predicted.append({**row, **{key: sum(r[key] for r in peers) / len(peers) for key in ("load_kw", "pv_kw", "wind_kw")}})
            errors = [abs(p["load_kw"] - r["load_kw"]) / r["load_kw"] for p, r in zip(predicted, rows) if r["load_kw"] > 0]
            mape = sum(errors) / len(errors) * 100 if errors else None
            return {"method": "历史同小时均值；所选日为留出验证日；电价和燃气量采用情景输入", "history_hours": len(before), "load_mape": mape, "records": predicted}
        if node == "carbon":
            return {"observed_baseline": summarize(dispatch(rows, a, "baseline")), "factors": {"grid_kgco2_kwh": a["grid_kgco2_kwh"], "gas_kgco2_m3": a["gas_kgco2_m3"]}, "boundary": "Scope 1 燃气 + Scope 2 外购电；不含 Scope 3"}
        if node == "dispatch":
            plan = dispatch(outputs["forecast"]["records"], a, strategy)
            return {"series": plan, "summary": summarize(plan), "strategy": strategy}
        if node == "economics":
            base = summarize(dispatch(outputs["forecast"]["records"], a, "baseline"))
            planned = outputs["dispatch"]["summary"]
            return {"baseline": base, "savings_cny": base["cost_cny"] - planned["cost_cny"], "carbon_saving_t": base["carbon_t"] - planned["carbon_t"], "boundary": outputs["carbon"]["boundary"], "method": "相同预测曲线的无储能基线，含电量费、上网收入与储能吞吐衰减费"}
        if node == "risk":
            plan = outputs["dispatch"]["series"]
            checks = {"power_balance": max(abs(r["balance_error_kw"]) for r in plan) < 1e-6,
                      "soc_bounds": all(a["soc_min"] * 100 - 1e-6 <= r["soc"] <= a["soc_max"] * 100 + 1e-6 for r in plan),
                      "terminal_soc": abs(plan[-1]["soc"] - a["soc_initial"] * 100) < 1e-6,
                      "power_limit": all(max(r["charge_kw"], r["discharge_kw"]) <= a["battery_power_kw"] + 1e-6 for r in plan),
                      "grid_limit": max(r["grid_import_kw"] for r in plan) <= a["grid_limit_kw"]}
            return {"passed": all(checks.values()), "checks": checks, "recommendation": "仿真策略通过约束复核" if all(checks.values()) else "策略未通过复核，需调整参数"}
        if node == "report":
            e, risk = outputs["economics"], outputs["risk"]
            return {"title": "园区协同分析报告", "accepted": risk["passed"], "text": f"{run['day']} 留出日分析：预计相对同情景无储能基线节省 {e['savings_cny']:.2f} 元，Scope 1+2 排放变化 {e['carbon_saving_t']:.3f} tCO₂（正值为减排）。{risk['recommendation']}。结果为规则驱动仿真，未下发设备；收益可能为负，需结合投资与实际预测误差评估。"}
        raise ValueError(node)

    pending = {n["id"]: n for n in AGENTS}
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            while pending:
                ready = [n for n in pending.values() if all(d in outputs for d in n["depends"])]
                if not ready:
                    raise RuntimeError("Agent 依赖图存在环或缺失节点")
                futures = {}
                for n in ready:
                    run["events"].append({"agent": n["id"], "status": "running", "elapsed_ms": round((time.perf_counter() - started) * 1000, 3), "message": n["role"], "inputs": n["depends"]})
                    futures[pool.submit(work, n["id"])] = n
                failure = None
                for future in as_completed(futures):
                    n = futures[future]
                    try:
                        outputs[n["id"]] = future.result()
                    except Exception as exc:
                        run["events"].append({"agent": n["id"], "status": "failed", "elapsed_ms": round((time.perf_counter() - started) * 1000, 3), "message": str(exc), "inputs": n["depends"]})
                        failure = exc
                        del pending[n["id"]]
                        continue
                    run["events"].append({"agent": n["id"], "status": "completed", "elapsed_ms": round((time.perf_counter() - started) * 1000, 3), "message": "完成计算，证据已写入共享上下文", "inputs": n["depends"]})
                    del pending[n["id"]]
                if failure:
                    raise failure
        run["status"] = "completed" if outputs["risk"]["passed"] else "needs_review"
    except Exception as exc:
        run["status"], run["error"] = "failed", str(exc)
        for n in pending.values():
            run["events"].append({"agent": n["id"], "status": "skipped", "elapsed_ms": round((time.perf_counter() - started) * 1000, 3), "message": "上游执行失败，未执行此节点", "inputs": n["depends"]})
    run["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
    save(run)
    return run
