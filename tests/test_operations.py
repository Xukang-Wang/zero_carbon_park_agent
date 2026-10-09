"""Domain invariants, failure handling, and API contracts for the new workbench."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.api.operations import router
from backend.services import operations as op
from backend.services import operations_workflow as wf


class OperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = op.read_source()
        cls.rows, _ = op.select_rows(cls.data)
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)

    def test_source_complete_and_reproducible(self):
        self.assertTrue(op.quality(self.data)["valid"])
        self.assertEqual(len(self.data["records"]), 720)
        self.assertEqual(self.data["fingerprint"], op.read_source()["fingerprint"])

    def test_physics_for_extreme_scenarios(self):
        a = self.data["assumptions"]
        for strategy in ("balanced", "economic", "carbon"):
            for capacity in (0, 500, 5000, 20000):
                for pv, load in ((.5, 1.5), (2, .5), (1, 1)):
                    with self.subTest(strategy=strategy, capacity=capacity, pv=pv, load=load):
                        plan = op.dispatch(self.rows, a, strategy, pv, load, capacity)
                        energy = capacity * a["soc_initial"]
                        for r in plan:
                            self.assertAlmostEqual(r["balance_error_kw"], 0, places=8)
                            self.assertLessEqual(max(r["charge_kw"], r["discharge_kw"]), a["battery_power_kw"] + 1e-7)
                            self.assertEqual(r["charge_kw"] * r["discharge_kw"], 0)
                            energy += r["charge_kw"] * a["charge_efficiency"] - r["discharge_kw"] / a["discharge_efficiency"]
                            self.assertAlmostEqual(energy, r["soc"] / 100 * capacity)
                            if capacity:
                                self.assertGreaterEqual(r["soc"], 20 - 1e-7)
                                self.assertLessEqual(r["soc"], 90 + 1e-7)
                        self.assertAlmostEqual(energy, capacity * a["soc_initial"])

    def test_zero_battery_matches_baseline(self):
        result = op.scenario(None, "balanced", 1, 1, 0)
        self.assertAlmostEqual(result["savings_cny"], 0)
        self.assertAlmostEqual(result["carbon_saving_t"], 0)

    def test_accounting_reconciles(self):
        plan = op.dispatch(self.rows, self.data["assumptions"])
        summary = op.summarize(plan)
        expected = sum(r["grid_import_kw"] * .58 + r["gas_m3"] * 2.16 for r in plan) / 1000
        self.assertAlmostEqual(summary["carbon_t"], expected)
        self.assertAlmostEqual(summary["scope1_t"] + summary["scope2_t"], summary["carbon_t"])
        self.assertAlmostEqual(summary["cost_cny"], sum(r["grid_import_kw"] * r["price_cny_kwh"] - r["grid_export_kw"] * .25 + (r["charge_kw"] + r["discharge_kw"]) * .05 for r in plan))

    def test_bad_data_blocks_analysis(self):
        for key, value in (("load_kw", None), ("pv_kw", -1), ("wind_kw", float('nan')), ("timestamp", "bad-time")):
            bad = copy.deepcopy(self.data)
            bad["records"][2][key] = value
            self.assertFalse(op.quality(bad)["valid"])
            with self.assertRaises(ValueError):
                op.select_rows(bad)
        bad = copy.deepcopy(self.data)
        bad["records"][1]["timestamp"] = bad["records"][0]["timestamp"]
        self.assertFalse(op.quality(bad)["valid"])

    def test_window_and_invalid_date(self):
        result = op.overview(days=7)
        self.assertEqual(result["period"]["hours"], 168)
        self.assertEqual(len(result["daily"]), 7)
        with self.assertRaises(ValueError):
            op.overview("2020-01-01")

    def test_workflow_dependencies_forecast_and_persistence(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(wf, "DB", Path(directory) / "runs.db"):
            result = wf.execute()
            self.assertEqual(result["status"], "completed")
            self.assertEqual(len(result["outputs"]), 7)
            self.assertEqual(wf.get_run(result["id"])["source_fingerprint"], self.data["fingerprint"])
            self.assertEqual(wf.history()[0]["id"], result["id"])
            completed = set()
            for e in result["events"]:
                if e["status"] == "running":
                    self.assertTrue(set(e["inputs"]) <= completed)
                else:
                    completed.add(e["agent"])
            self.assertTrue(all(result["outputs"]["risk"]["checks"].values()))
            self.assertEqual(result["outputs"]["forecast"]["history_hours"], 168)
            # Holdout values must not leak into the historical mean.
            first = result["outputs"]["forecast"]["records"][0]
            peers = [r for r in self.data["records"] if r["timestamp"][:10] < result["day"]][-168::24]
            self.assertAlmostEqual(first["load_kw"], sum(r["load_kw"] for r in peers) / 7)

    def test_insufficient_history_is_persisted_failure(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(wf, "DB", Path(directory) / "runs.db"):
            result = wf.execute("2026-09-09")
            self.assertEqual(result["status"], "failed")
            self.assertNotIn("report", result["outputs"])
            self.assertEqual(wf.get_run(result["id"])["status"], "failed")
            self.assertTrue(any(e["agent"] == "report" and e["status"] == "skipped" for e in result["events"]))

    def test_risk_failure_does_not_accept_strategy(self):
        constrained = copy.deepcopy(self.data)
        constrained["assumptions"]["grid_limit_kw"] = 100
        with tempfile.TemporaryDirectory() as directory, patch.object(wf, "DB", Path(directory) / "runs.db"), patch.object(wf, "read_source", return_value=constrained):
            result = wf.execute()
            self.assertEqual(result["status"], "needs_review")
            self.assertFalse(result["outputs"]["report"]["accepted"])

    def test_invalid_model_assumptions_block_execution(self):
        for key, value in (("charge_efficiency", 0), ("soc_initial", 1.2), ("grid_kgco2_kwh", -1)):
            bad = copy.deepcopy(self.data)
            bad["assumptions"][key] = value
            with self.assertRaises(ValueError):
                op.select_rows(bad)

    def test_api_contracts(self):
        self.assertEqual(self.client.get('/api/v1/operations/overview').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/operations/overview?days=0').status_code, 422)
        self.assertEqual(self.client.get('/api/v1/operations/overview?day=missing').status_code, 422)
        for body in ({"capacity_kwh": -1}, {"load_scale": 2}, {"strategy": "unknown"}):
            self.assertEqual(self.client.post('/api/v1/operations/scenario', json=body).status_code, 422)
        response = self.client.post('/api/v1/operations/scenario', json={"capacity_kwh": 0})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["savings_cny"], 0)
        self.assertEqual(len(self.client.get('/api/v1/operations/agents').json()["nodes"]), 7)
        with tempfile.TemporaryDirectory() as directory, patch.object(wf, "DB", Path(directory) / "runs.db"):
            self.assertEqual(self.client.get('/api/v1/operations/runs/missing').status_code, 404)
            result = self.client.post('/api/v1/operations/runs', json={}).json()
            self.assertEqual(result["status"], "completed")


if __name__ == "__main__":
    unittest.main()
