"""
zero_carbon_park_agent Pydantic 数据模型（Schemas）
用于 FastAPI 请求/响应验证
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── 水质数据 ──────────────────────────────────────────────────────────────

class WaterQualityQuery(BaseModel):
    device_id: str = Field(default="WQ-001", description="设备编号")
    hours: int = Field(default=24, ge=1, le=720, description="查询最近N小时数据")


class WaterPredictRequest(BaseModel):
    device_id: str = Field(default="WQ-001", description="设备编号")
    horizon_hours: int = Field(default=24, ge=1, le=72, description="预测时长")


class WaterQualityRecordOut(BaseModel):
    id: int
    device_id: str
    timestamp: datetime
    cod: Optional[float]
    ammonia_nitrogen: Optional[float]
    nitrate_nitrogen: Optional[float]
    ph: Optional[float]
    temperature: Optional[float]
    dissolved_oxygen: Optional[float]
    inflow_rate: Optional[float]
    sludge_conc: Optional[float]

    class Config:
        from_attributes = True


class PredictionItem(BaseModel):
    target_timestamp: str
    cod: float
    ammonia_nitrogen: float
    nitrate_nitrogen: float


class AnomalyFlag(BaseModel):
    target_timestamp: str
    metric: str
    predicted_value: float
    threshold: float
    severity: str


class PredictionResponse(BaseModel):
    device_id: str
    predicted_at: str
    horizon_hours: int
    predictions: List[PredictionItem]
    anomaly_flags: List[AnomalyFlag]
    model_version: str


# ── 知识图谱 ──────────────────────────────────────────────────────────────

class GraphQueryRequest(BaseModel):
    action: str = Field(default="overview", description="操作类型")
    entity_id: Optional[str] = None
    trace_direction: Optional[str] = "upstream"


class GraphOverviewResponse(BaseModel):
    total_nodes: int
    total_edges: int
    node_counts: Dict[str, int]
    total_renewable_capacity_kw: float


# ── 碳足迹 ────────────────────────────────────────────────────────────────

class CarbonFootprintResponse(BaseModel):
    total_power_kw: float
    grid_power_kw: float
    renewable_power_kw: float
    renewable_ratio: float
    direct_emission_tco2_per_h: float
    indirect_emission_tco2_per_h: float
    carbon_offset_tco2_per_h: float
    net_emission_tco2_per_h: float
    grid_emission_factor: float


# ── Agent 工作流 ──────────────────────────────────────────────────────────

class WorkflowTriggerRequest(BaseModel):
    workflow_type: str = Field(default="water_anomaly", description="工作流类型")
    params: Dict[str, Any] = Field(default_factory=dict, description="工作流参数")


class WorkflowTriggerResponse(BaseModel):
    workflow_id: str
    workflow_type: str
    status: str
    started_at: str
    agents_involved: List[str]


class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    status: str
    current_step: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    has_report: bool
    error_message: Optional[str]


# ── 异常事件 ──────────────────────────────────────────────────────────────

class AnomalyEventResponse(BaseModel):
    id: int
    event_type: str
    severity: str
    source: Optional[str]
    description: Optional[str]
    predicted_value: Optional[float]
    threshold_value: Optional[float]
    detected_at: datetime
    resolved_at: Optional[datetime]
    workflow_id: Optional[str]
    status: str

    class Config:
        from_attributes = True


# ── 通用响应 ──────────────────────────────────────────────────────────────

class APIResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Any = None