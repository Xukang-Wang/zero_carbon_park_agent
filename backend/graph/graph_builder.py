"""
zero_carbon_park_agent 知识图谱构建与管理（基于 NetworkX）
轻量级替代 Neo4j，支持 JSON 持久化，实现能源血缘追溯与碳足迹计算
"""
import json
import networkx as nx
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Optional, Any
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import GRAPH_DATA_PATH, GRID_EMISSION_FACTOR, ZERO_CARBON_INDICATORS


class EnergyKnowledgeGraph:
    """能源知识图谱

    构建"源—网—荷—储—碳"五层节点本体与 6 类关系，
    支持能源血缘追溯与碳足迹实时计算。
    """

    NODE_TYPES = ["EnergySource", "GridNode", "EnergyLoad", "EnergyStorage", "CarbonRecord",
                  "GreenPowerSupply", "IncrementalDistGrid", "CCUSNode", "BiomassNode",
                  "MicroGrid", "VPPNode", "CarbonAsset", "DispatchPlan", "MonitoringPoint"]
    RELATION_TYPES = ["GENERATES", "TRANSMITS", "CONSUMES", "STORES", "EMITS", "OFFSETS",
                      "FEEDS", "AGGREGATES", "DISPATCHES", "MONITORS", "TRADES"]

    def __init__(self):
        self.graph = nx.MultiDiGraph()

    # ── 图谱构建 ──────────────────────────────────────────────────────────

    def build_default_graph(self):
        """构建默认的园区能源知识图谱"""
        self.graph.clear()

        # 能源源节点
        self.graph.add_node("PV-001", type="EnergySource", name="1号光伏电站",
                            source_type="solar", capacity_kw=5000, location="园区A区屋顶")
        self.graph.add_node("GRID-001", type="EnergySource", name="市电馈线",
                            source_type="grid", capacity_kw=10000,
                            emission_factor=GRID_EMISSION_FACTOR)

        # 电网节点
        self.graph.add_node("TRANS-001", type="GridNode", name="1号主变压器",
                            node_type="transformer", voltage_level_kv=10, capacity_kva=8000)

        # 负荷节点
        self.graph.add_node("WWTP-001", type="EnergyLoad", name="集中式污水处理厂",
                            load_type="wastewater_treatment", rated_power_kw=1500,
                            department="环保部", daily_capacity_m3=20000)
        self.graph.add_node("LOAD-001", type="EnergyLoad", name="1号生产线",
                            load_type="manufacturing", rated_power_kw=2000,
                            department="制造一部", wastewater_discharge_m3h=50)
        self.graph.add_node("LOAD-002", type="EnergyLoad", name="2号生产线",
                            load_type="manufacturing", rated_power_kw=1800,
                            department="制造二部", wastewater_discharge_m3h=40)
        self.graph.add_node("LOAD-003", type="EnergyLoad", name="空调系统",
                            load_type="hvac", rated_power_kw=800, department="设施部")
        self.graph.add_node("LOAD-004", type="EnergyLoad", name="充电桩集群",
                            load_type="ev_charging", rated_power_kw=600, department="后勤部")

        # 储能节点
        self.graph.add_node("BAT-001", type="EnergyStorage", name="1号锂电池储能系统",
                            storage_type="li_ion", capacity_kwh=5000, rated_power_kw=2500,
                            soc_min=20, soc_max=90)

        # 碳排放记录节点
        today = date.today().isoformat()
        self.graph.add_node(f"CARBON-{today}", type="CarbonRecord",
                            date=today, direct_emission_tco2=12.5,
                            indirect_emission_tco2=45.3, offset_tco2=23.1,
                            net_emission_tco2=34.7)

        # 关系：光伏电站 → 变压器
        self.graph.add_edge("PV-001", "TRANS-001", relation="GENERATES",
                            power_kw=3500, renewable=True)
        # 关系：市电 → 变压器
        self.graph.add_edge("GRID-001", "TRANS-001", relation="GENERATES",
                            power_kw=5000, renewable=False)

        # 关系：变压器 → 各负荷
        self.graph.add_edge("TRANS-001", "WWTP-001", relation="TRANSMITS", power_kw=1200)
        self.graph.add_edge("TRANS-001", "LOAD-001", relation="TRANSMITS", power_kw=1800)
        self.graph.add_edge("TRANS-001", "LOAD-002", relation="TRANSMITS", power_kw=1600)
        self.graph.add_edge("TRANS-001", "LOAD-003", relation="TRANSMITS", power_kw=700)
        self.graph.add_edge("TRANS-001", "LOAD-004", relation="TRANSMITS", power_kw=500)

        # 关系：变压器 → 储能（充电）
        self.graph.add_edge("TRANS-001", "BAT-001", relation="STORES",
                            power_kw=2000, direction="charge")
        # 关系：储能 → 变压器（放电）
        self.graph.add_edge("BAT-001", "TRANS-001", relation="STORES",
                            power_kw=1500, direction="discharge")

        # 关系：各负荷 → 碳排放
        carbon_node = f"CARBON-{today}"
        self.graph.add_edge("LOAD-001", carbon_node, relation="EMITS", amount_tco2=2.5)
        self.graph.add_edge("WWTP-001", carbon_node, relation="EMITS", amount_tco2=1.8)
        self.graph.add_edge("LOAD-002", carbon_node, relation="EMITS", amount_tco2=2.0)

        # 绿电直供与增量配电网
        self.add_green_power_nodes()
        # CCUS 碳捕集利用与封存
        self.add_ccus_nodes()
        # 生物质CHP
        self.add_biomass_chp_nodes()
        # 微电网与VPP节点
        self.add_microgrid_vpp_nodes()
        # 碳资产节点
        self.add_carbon_asset_nodes()
        # 调度计划节点
        self.add_dispatch_nodes()
        # 监测点
        self.add_monitoring_nodes()

        print(f"知识图谱构建完成: {self.graph.number_of_nodes()} 个节点, "
              f"{self.graph.number_of_edges()} 条边")

    # ── 绿电直供与增量配电网 ──────────────────────────────────────────────

    def add_green_power_nodes(self):
        """添加绿电直供和增量配电网节点"""
        # 绿电直供节点
        self.graph.add_node("GREEN-PV-001", type="GreenPowerSupply", name="光伏直供系统",
                            supply_type="solar_direct", capacity_kw=5000, location="园区A区")
        self.graph.add_node("GREEN-WIND-001", type="GreenPowerSupply", name="风电直供系统",
                            supply_type="wind_direct", capacity_kw=3000, location="园区B区")
        self.graph.add_node("GREEN-HYDRO-001", type="GreenPowerSupply", name="氢能站",
                            supply_type="hydrogen", capacity_kw=1000, location="园区C区")

        # 增量配电网节点
        self.graph.add_node("IDG-001", type="IncrementalDistGrid", name="增量配电网",
                            voltage_level_kv=10, capacity_kva=10000)

        # 关系：绿电 → 增量配电网
        self.graph.add_edge("GREEN-PV-001", "IDG-001", relation="GENERATES",
                            power_kw=3500, renewable=True)
        self.graph.add_edge("GREEN-WIND-001", "IDG-001", relation="GENERATES",
                            power_kw=2000, renewable=True)
        self.graph.add_edge("GREEN-HYDRO-001", "IDG-001", relation="GENERATES",
                            power_kw=800, renewable=True)

        # 关系：增量配电网 → 主变压器
        self.graph.add_edge("IDG-001", "TRANS-001", relation="TRANSMITS",
                            power_kw=6000)

    # ── CCUS 碳捕集利用与封存 ──────────────────────────────────────────────

    def add_ccus_nodes(self):
        """添加CCUS碳捕集、利用与封存节点"""
        self.graph.add_node("CCUS-001", type="CCUSNode", name="碳捕集装置",
                            capture_rate=0.90, capture_cost=200,
                            technology="chemical_absorption")
        self.graph.add_node("CCUS-UTIL-001", type="CCUSNode", name="碳利用装置",
                            utilization_ratio=0.60, product="化工原料")
        self.graph.add_node("CCUS-STORAGE-001", type="CCUSNode", name="碳封存装置",
                            storage_type="地质封存", capacity_tco2=100000)

        # 关系：捕集 → 利用，捕集 → 封存
        self.graph.add_edge("CCUS-001", "CCUS-UTIL-001", relation="TRANSMITS",
                            co2_flow_tph=5.0)
        self.graph.add_edge("CCUS-001", "CCUS-STORAGE-001", relation="TRANSMITS",
                            co2_flow_tph=3.0)

    # ── 生物质CHP ─────────────────────────────────────────────────────────

    def add_biomass_chp_nodes(self):
        """添加生物质热电联产节点"""
        self.graph.add_node("BIOCHP-001", type="BiomassNode", name="生物质CHP电厂",
                            capacity_kw=2000, feedstock="秸秆/林业废弃物",
                            heat_output_kw=3000)
        self.graph.add_node("BIOGAS-001", type="BiomassNode", name="沼气发酵罐",
                            biogas_yield_m3_per_t=120, methane_ratio=0.60,
                            feedstock_t_per_day=50)

        # 关系：沼气 → CHP（供料），CHP → 变压器（发电）
        self.graph.add_edge("BIOGAS-001", "BIOCHP-001", relation="FEEDS",
                            feedstock_t_per_day=50)
        self.graph.add_edge("BIOCHP-001", "TRANS-001", relation="GENERATES",
                            power_kw=1500, renewable=True)

    # ── 微电网与VPP ────────────────────────────────────────────────────────

    def add_microgrid_vpp_nodes(self):
        """添加微电网与虚拟电厂节点"""
        # 微电网
        self.graph.add_node("MG-001", type="MicroGrid", name="园区微电网",
                            voltage_level_kv=10, frequency_hz=50.0,
                            total_generation_kw=8500, total_load_kw=8000)
        # VPP
        self.graph.add_node("VPP-001", type="VPPNode", name="园区虚拟电厂",
                            aggregated_capacity_mw=10.5, response_time_ms=200,
                            market_participation="spot+ancillary")
        # 关系
        self.graph.add_edge("MG-001", "VPP-001", relation="AGGREGATES",
                            capacity_mw=10.5)
        self.graph.add_edge("PV-001", "VPP-001", relation="AGGREGATES",
                            capacity_mw=5.0)
        self.graph.add_edge("BAT-001", "VPP-001", relation="AGGREGATES",
                            capacity_mw=2.5)

    # ── 碳资产 ─────────────────────────────────────────────────────────────

    def add_carbon_asset_nodes(self):
        """添加碳资产节点"""
        self.graph.add_node("CEA-001", type="CarbonAsset", name="碳配额(CEA)",
                            asset_type="cea", amount_tco2=5000, unit_price=60.0)
        self.graph.add_node("CCER-001", type="CarbonAsset", name="CCER-光伏项目",
                            asset_type="ccer", amount_tco2=2000, unit_price=50.0)
        self.graph.add_node("GEC-001", type="CarbonAsset", name="绿证(GEC)",
                            asset_type="green_certificate", amount_mwh=10000, unit_price=25.0)
        # 关系：碳资产 → 碳记录（抵消）
        today = date.today().isoformat()
        self.graph.add_edge("CCER-001", f"CARBON-{today}", relation="OFFSETS",
                            amount_tco2=2000)

    # ── 调度计划 ───────────────────────────────────────────────────────────

    def add_dispatch_nodes(self):
        """添加调度计划节点"""
        self.graph.add_node("DISPATCH-001", type="DispatchPlan", name="日前调度计划",
                            strategy="balanced", horizon_hours=24,
                            expected_renewable_ratio=0.45)
        self.graph.add_node("DISPATCH-002", type="DispatchPlan", name="实时调度计划",
                            strategy="real_time", horizon_hours=1)
        # 关系
        self.graph.add_edge("DISPATCH-001", "BAT-001", relation="DISPATCHES",
                            charge_schedule="valley", discharge_schedule="peak")
        self.graph.add_edge("DISPATCH-001", "MG-001", relation="DISPATCHES",
                            target_power_balance=0)

    # ── 监测点 ─────────────────────────────────────────────────────────────

    def add_monitoring_nodes(self):
        """添加监测点节点"""
        monitoring_points = [
            ("MON-PV-001", "光伏出力监测点", "PV-001", "power/temperature/irradiance"),
            ("MON-WIND-001", "风电出力监测点", "WIND-001", "power/wind_speed"),
            ("MON-BAT-001", "储能状态监测点", "BAT-001", "soc/soh/temperature"),
            ("MON-GRID-001", "电网交互监测点", "GRID-001", "power/voltage/frequency"),
            ("MON-LOAD-001", "负荷监测点", "LOAD-001", "power/flexibility"),
        ]
        for mp_id, mp_name, target, metrics in monitoring_points:
            self.graph.add_node(mp_id, type="MonitoringPoint", name=mp_name,
                                metrics=metrics)
            self.graph.add_edge(mp_id, target, relation="MONITORS", metrics=metrics)

    # ── 持久化 ────────────────────────────────────────────────────────────

    def get_overview(self) -> Dict:
        """获取图谱概览统计"""
        node_counts = {}
        for ntype in self.NODE_TYPES:
            nodes = [n for n, d in self.graph.nodes(data=True) if d.get("type") == ntype]
            node_counts[ntype] = len(nodes)

        total_renewable = sum(
            d.get("capacity_kw", 0) for n, d in self.graph.nodes(data=True)
            if d.get("type") == "EnergySource" and d.get("source_type") == "solar"
        )

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_counts": node_counts,
            "total_renewable_capacity_kw": total_renewable,
        }

    def trace_energy(self, entity_id: str, direction: str = "upstream",
                     max_depth: int = 5) -> List[Dict]:
        """能源血缘追溯

        Args:
            entity_id: 实体 ID
            direction: upstream（向上追溯能源来源）或 downstream（向下追溯用能去向）
            max_depth: 最大追溯深度
        """
        if entity_id not in self.graph:
            return []

        trace_path = []
        visited = set()

        if direction == "upstream":
            # BFS 向上追溯
            current_layer = [entity_id]
            depth = 0
            while current_layer and depth < max_depth:
                next_layer = []
                for node in current_layer:
                    if node in visited:
                        continue
                    visited.add(node)
                    for pred in self.graph.predecessors(node):
                        if pred not in visited:
                            edge_data = self.graph.get_edge_data(pred, node)
                            if edge_data:
                                for key, data in edge_data.items():
                                    trace_path.append({
                                        "depth": depth + 1,
                                        "from": pred,
                                        "to": node,
                                        "relation": data.get("relation", "UNKNOWN"),
                                        "power_kw": data.get("power_kw", 0),
                                    })
                            next_layer.append(pred)
                current_layer = next_layer
                depth += 1
        else:
            # BFS 向下追溯
            current_layer = [entity_id]
            depth = 0
            while current_layer and depth < max_depth:
                next_layer = []
                for node in current_layer:
                    if node in visited:
                        continue
                    visited.add(node)
                    for succ in self.graph.successors(node):
                        if succ not in visited:
                            edge_data = self.graph.get_edge_data(node, succ)
                            if edge_data:
                                for key, data in edge_data.items():
                                    trace_path.append({
                                        "depth": depth + 1,
                                        "from": node,
                                        "to": succ,
                                        "relation": data.get("relation", "UNKNOWN"),
                                        "power_kw": data.get("power_kw", 0),
                                    })
                            next_layer.append(succ)
                current_layer = next_layer
                depth += 1

        return trace_path

    def get_entity_info(self, entity_id: str) -> Optional[Dict]:
        """获取实体详细信息"""
        if entity_id in self.graph:
            return {"id": entity_id, **self.graph.nodes[entity_id]}
        return None

    def get_all_entities_by_type(self, node_type: str) -> List[Dict]:
        """获取指定类型的所有实体"""
        return [
            {"id": n, **d}
            for n, d in self.graph.nodes(data=True)
            if d.get("type") == node_type
        ]

    def get_loads_upstream_of_wwtp(self) -> List[Dict]:
        """获取污水处理厂上游的产线负荷（用于根因分析）"""
        results = []
        # 找到所有制造业负荷
        for n, d in self.graph.nodes(data=True):
            if d.get("type") == "EnergyLoad" and d.get("load_type") == "manufacturing":
                # 追溯该负荷的能源路径
                trace = self.trace_energy(n, direction="downstream")
                results.append({
                    "load_id": n,
                    "load_name": d.get("name", n),
                    "department": d.get("department", ""),
                    "rated_power_kw": d.get("rated_power_kw", 0),
                    "wastewater_discharge_m3h": d.get("wastewater_discharge_m3h", 0),
                    "energy_trace": trace,
                })
        return results

    # ── 碳足迹计算 ────────────────────────────────────────────────────────

    def calculate_carbon_footprint(self) -> Dict:
        """计算园区碳足迹汇总"""
        total_grid_power = 0.0
        total_renewable_power = 0.0

        for u, v, data in self.graph.edges(data=True):
            if data.get("relation") == "GENERATES":
                power = data.get("power_kw", 0)
                if data.get("renewable", False):
                    total_renewable_power += power
                else:
                    total_grid_power += power

        total_power = total_grid_power + total_renewable_power
        renewable_ratio = total_renewable_power / total_power if total_power > 0 else 0

        # 间接排放 = 外购电力 × 电网排放因子
        indirect_emission = (total_grid_power / 1000) * GRID_EMISSION_FACTOR  # tCO₂/h

        # 碳抵消 = 可再生能源发电 × 电网排放因子
        carbon_offset = (total_renewable_power / 1000) * GRID_EMISSION_FACTOR

        # 直接排放（从碳排放节点获取）
        direct_emission = 0
        for n, d in self.graph.nodes(data=True):
            if d.get("type") == "CarbonRecord":
                direct_emission += d.get("direct_emission_tco2", 0)

        net_emission = direct_emission + indirect_emission - carbon_offset

        return {
            "total_power_kw": total_power,
            "grid_power_kw": total_grid_power,
            "renewable_power_kw": total_renewable_power,
            "renewable_ratio": round(renewable_ratio, 4),
            "direct_emission_tco2_per_h": round(direct_emission, 2),
            "indirect_emission_tco2_per_h": round(indirect_emission, 2),
            "carbon_offset_tco2_per_h": round(carbon_offset, 2),
            "net_emission_tco2_per_h": round(net_emission, 2),
            "grid_emission_factor": GRID_EMISSION_FACTOR,
        }

    # ── 碳排放核算 ────────────────────────────────────────────────────────

    def get_scope_emissions(self) -> Dict:
        """获取 Scope 1/2/3 碳排放核算

        Scope 1: 直接排放（燃料燃烧、工艺排放）
        Scope 2: 间接排放（外购电力、蒸汽）
        Scope 3: 其他间接排放（供应链、运输等）
        """
        # 从当前图谱获取碳足迹基础数据
        carbon_data = self.calculate_carbon_footprint()

        # Scope 1: 直接排放（园区内化石燃料燃烧、工业过程排放）
        scope1 = carbon_data.get("direct_emission_tco2_per_h", 12.5) * 24 * 365

        # Scope 2: 间接排放（外购电力、热力）
        scope2 = carbon_data.get("indirect_emission_tco2_per_h", 45.3) * 24 * 365

        # Scope 3: 其他间接排放（供应链运输、废弃物处理、员工通勤等）
        scope3 = scope2 * 0.35  # 估算为 Scope 2 的 35%

        total_emissions = scope1 + scope2 + scope3
        carbon_offset = carbon_data.get("carbon_offset_tco2_per_h", 23.1) * 24 * 365

        return {
            "scope1_direct_emissions_tco2": round(scope1, 2),
            "scope1_breakdown": {
                "natural_gas_combustion": round(scope1 * 0.45, 2),
                "industrial_process": round(scope1 * 0.35, 2),
                "fugitive_emissions": round(scope1 * 0.20, 2),
            },
            "scope2_indirect_emissions_tco2": round(scope2, 2),
            "scope2_breakdown": {
                "purchased_electricity": round(scope2 * 0.85, 2),
                "purchased_steam_heat": round(scope2 * 0.15, 2),
            },
            "scope3_other_emissions_tco2": round(scope3, 2),
            "scope3_breakdown": {
                "supply_chain_transport": round(scope3 * 0.40, 2),
                "waste_disposal": round(scope3 * 0.25, 2),
                "employee_commuting": round(scope3 * 0.20, 2),
                "business_travel": round(scope3 * 0.15, 2),
            },
            "total_emissions_tco2": round(total_emissions, 2),
            "carbon_offset_tco2": round(carbon_offset, 2),
            "net_emissions_tco2": round(total_emissions - carbon_offset, 2),
            "grid_emission_factor": carbon_data.get("grid_emission_factor", 0.581),
            "renewable_ratio": carbon_data.get("renewable_ratio", 0),
        }

    def evaluate_zero_carbon_indicators(self) -> Dict:
        """评估零碳园区达标指标（参考国家级零碳园区评价标准）"""
        carbon_data = self.calculate_carbon_footprint()
        renewable_ratio = carbon_data.get("renewable_ratio", 0)

        # 指标定义
        indicators = [
            {
                "name": "可再生能源占比",
                "current_value": round(renewable_ratio * 100, 1),
                "target": 50.0,
                "unit": "%",
                "pass_status": renewable_ratio >= 0.50,
                "score": min(25, round(renewable_ratio * 50, 1)),
            },
            {
                "name": "碳排放强度",
                "current_value": round(carbon_data.get("net_emission_tco2_per_h", 0) * 8760
                                     / (carbon_data.get("total_power_kw", 1000) / 1000), 2),
                "target": 0.3,
                "unit": "tCO₂/MWh",
                "pass_status": True,  # 模拟数据
                "score": 20,
            },
            {
                "name": "能源利用效率",
                "current_value": round(65.0 + renewable_ratio * 15, 1),
                "target": 70.0,
                "unit": "%",
                "pass_status": True,
                "score": 15,
            },
            {
                "name": "碳抵消比例",
                "current_value": round(min(100, renewable_ratio * 120), 1),
                "target": 30.0,
                "unit": "%",
                "pass_status": True,
                "score": 15,
            },
            {
                "name": "绿色建筑覆盖率",
                "current_value": 85.0,
                "target": 80.0,
                "unit": "%",
                "pass_status": True,
                "score": 15,
            },
            {
                "name": "水资源循环利用率",
                "current_value": 78.5,
                "target": 75.0,
                "unit": "%",
                "pass_status": True,
                "score": 10,
            },
        ]

        total_score = sum(ind["score"] for ind in indicators)
        all_passed = all(ind["pass_status"] for ind in indicators)

        return {
            "overall_score": round(total_score, 1),
            "max_score": 100,
            "indicators": indicators,
            "all_indicators_passed": all_passed,
            "recommendation": "园区已达到零碳标准，建议持续优化可再生能源占比"
            if all_passed and total_score >= 80
            else "园区尚未完全达标，需重点提升可再生能源占比和碳排放强度",
            "certification_stage": "已通过初审" if total_score >= 80 else "整改中",
            "evaluation_date": datetime.now().isoformat(),
        }

    # ── 持久化 ────────────────────────────────────────────────────────────

    def save(self, path: Path = GRAPH_DATA_PATH):
        """保存图谱到 JSON 文件"""
        data = {
            "nodes": [
                {"id": n, **d}
                for n, d in self.graph.nodes(data=True)
            ],
            "edges": [
                {"from": u, "to": v, **d}
                for u, v, d in self.graph.edges(data=True)
            ]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"知识图谱已保存: {path}")

    def load(self, path: Path = GRAPH_DATA_PATH):
        """从 JSON 文件加载图谱"""
        if not path.exists():
            print(f"图谱文件不存在: {path}，将构建默认图谱")
            self.build_default_graph()
            self.save(path)
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.graph.clear()
        for node in data["nodes"]:
            node_id = node.pop("id")
            self.graph.add_node(node_id, **node)

        for edge in data["edges"]:
            u = edge.pop("from")
            v = edge.pop("to")
            self.graph.add_edge(u, v, **edge)

        print(f"知识图谱已加载: {self.graph.number_of_nodes()} 个节点, "
              f"{self.graph.number_of_edges()} 条边")


# 全局单例
_kg_instance: Optional[EnergyKnowledgeGraph] = None


def get_knowledge_graph() -> EnergyKnowledgeGraph:
    """获取知识图谱单例"""
    global _kg_instance
    if _kg_instance is None:
        _kg_instance = EnergyKnowledgeGraph()
        _kg_instance.load()
    return _kg_instance


def init_knowledge_graph():
    """初始化知识图谱（首次运行调用）"""
    global _kg_instance
    _kg_instance = EnergyKnowledgeGraph()
    _kg_instance.build_default_graph()
    _kg_instance.save()
    return _kg_instance


if __name__ == "__main__":
    kg = init_knowledge_graph()
    print("\n图谱概览:", kg.get_overview())
    print("\n能源追溯 (WWTP-001 upstream):")
    for item in kg.trace_energy("WWTP-001", "upstream"):
        print(f"  {item}")
    print("\n碳足迹:", kg.calculate_carbon_footprint())