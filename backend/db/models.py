"""
zero_carbon_park_agent 数据库 ORM 模型（SQLAlchemy）
"""
from sqlalchemy import Column, Integer, BigInteger, String, Float, Text, DateTime, JSON
from sqlalchemy.sql import func
from db.postgres_client import Base


class WaterQualityRecord(Base):
    """水质监测数据表"""
    __tablename__ = "water_quality_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(32), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    cod = Column(Float)
    ammonia_nitrogen = Column(Float)
    nitrate_nitrogen = Column(Float)
    ph = Column(Float)
    temperature = Column(Float)
    dissolved_oxygen = Column(Float)
    inflow_rate = Column(Float)
    sludge_conc = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class WaterPredictionResult(Base):
    """水质预测结果表"""
    __tablename__ = "water_prediction_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(32), nullable=False, index=True)
    predicted_at = Column(DateTime, nullable=False)
    target_timestamp = Column(DateTime, nullable=False, index=True)
    cod_pred = Column(Float)
    ammonia_nitrogen_pred = Column(Float)
    nitrate_nitrogen_pred = Column(Float)
    model_version = Column(String(32), default="lstm_transformer_v1")
    created_at = Column(DateTime, server_default=func.now())


class AnomalyEvent(Base):
    """异常事件表"""
    __tablename__ = "anomaly_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(32), nullable=False, default="water_quality")
    severity = Column(String(16), nullable=False)
    source = Column(String(64))
    description = Column(Text)
    predicted_value = Column(Float)
    threshold_value = Column(Float)
    detected_at = Column(DateTime, nullable=False, index=True)
    resolved_at = Column(DateTime)
    workflow_id = Column(String(64))
    root_cause = Column(Text)
    resolution = Column(Text)
    status = Column(String(16), default="open")


class WorkflowExecution(Base):
    """工作流执行记录表"""
    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(64), nullable=False, unique=True, index=True)
    workflow_type = Column(String(32), nullable=False)
    status = Column(String(16), default="running")
    state_snapshot = Column(JSON)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    report_content = Column(Text)
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class CarbonAssetRecord(Base):
    """碳资产记录表"""
    __tablename__ = "carbon_asset_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_type = Column(String(32), nullable=False)  # quota/ccer/green_certificate
    quantity = Column(Float, nullable=False)
    unit = Column(String(16), default="tCO2e")
    unit_price = Column(Float)
    total_value = Column(Float)
    transaction_date = Column(DateTime, nullable=False)
    counterparty = Column(String(64))
    status = Column(String(16), default="active")
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class EnergyDispatchRecord(Base):
    """能源调度记录表"""
    __tablename__ = "energy_dispatch_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dispatch_type = Column(String(32), nullable=False)  # multi_energy/storage/vpp
    pv_power_kw = Column(Float, default=0)
    wind_power_kw = Column(Float, default=0)
    grid_power_kw = Column(Float, default=0)
    storage_power_kw = Column(Float, default=0)
    load_power_kw = Column(Float, default=0)
    storage_soc = Column(Float, default=0)
    dispatch_time = Column(DateTime, nullable=False)
    cost_saving = Column(Float, default=0)
    created_at = Column(DateTime, server_default=func.now())


class EvaluationRecord(Base):
    """零碳园区评价记录表"""
    __tablename__ = "evaluation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    eval_date = Column(DateTime, nullable=False)
    indicator_name = Column(String(64), nullable=False)
    current_value = Column(Float)
    target_value = Column(Float)
    unit = Column(String(16))
    pass_status = Column(String(16))
    category = Column(String(16))
    created_at = Column(DateTime, server_default=func.now())