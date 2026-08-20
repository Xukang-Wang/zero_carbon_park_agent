"""
zero_carbon_park_agent 水质数据 API 路由
所有数据从静态 JSON 文件加载，替换为真实数据时只需替换 JSON 文件
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta
from typing import Optional
import json

from db.postgres_client import get_db
from db.models import WaterQualityRecord, WaterPredictionResult
from schemas.water import (
    WaterQualityQuery, WaterPredictRequest, PredictionResponse,
    PredictionItem, AnomalyFlag, APIResponse,
)

router = APIRouter(prefix="/api/v1/water", tags=["水质监测"])


@router.get("/realtime")
async def get_realtime_water_quality(
    device_id: str = Query(default="WQ-001", description="设备编号"),
    db: Session = Depends(get_db),
):
    """获取实时水质数据（最新一条，从静态JSON加载）"""
    record = (
        db.query(WaterQualityRecord)
        .filter(WaterQualityRecord.device_id == device_id)
        .order_by(desc(WaterQualityRecord.timestamp))
        .first()
    )

    if record is None:
        from data.mock_data import get_mock_data
        return APIResponse(data=get_mock_data().get_water_realtime(device_id))

    return APIResponse(data={
        "device_id": record.device_id,
        "timestamp": record.timestamp.isoformat(),
        "cod": record.cod,
        "ammonia_nitrogen": record.ammonia_nitrogen,
        "nitrate_nitrogen": record.nitrate_nitrogen,
        "ph": record.ph,
        "temperature": record.temperature,
        "dissolved_oxygen": record.dissolved_oxygen,
        "inflow_rate": record.inflow_rate,
        "sludge_conc": record.sludge_conc,
        "source": "database",
    })


@router.get("/history")
async def get_water_quality_history(
    device_id: str = Query(default="WQ-001"),
    hours: int = Query(default=24, ge=1, le=720),
    db: Session = Depends(get_db),
):
    """查询历史水质数据（从静态JSON加载）"""
    since = datetime.now() - timedelta(hours=hours)
    records = (
        db.query(WaterQualityRecord)
        .filter(
            WaterQualityRecord.device_id == device_id,
            WaterQualityRecord.timestamp >= since,
        )
        .order_by(WaterQualityRecord.timestamp)
        .limit(1000)
        .all()
    )

    if not records:
        from data.mock_data import get_mock_data
        data = get_mock_data().get_water_history(device_id, hours)
        return APIResponse(data={"device_id": device_id, "records": data, "source": "simulated"})

    data = []
    for r in records:
        data.append({
            "timestamp": r.timestamp.isoformat(),
            "cod": r.cod,
            "ammonia_nitrogen": r.ammonia_nitrogen,
            "nitrate_nitrogen": r.nitrate_nitrogen,
            "ph": r.ph,
            "temperature": r.temperature,
            "dissolved_oxygen": r.dissolved_oxygen,
            "inflow_rate": r.inflow_rate,
            "sludge_conc": r.sludge_conc,
        })

    return APIResponse(data={"device_id": device_id, "records": data, "source": "database"})


@router.post("/predict")
async def predict_water_quality(
    request: WaterPredictRequest,
    db: Session = Depends(get_db),
):
    """触发水质指标 24h 预测"""
    from tools.prediction_tool import PredictionTool
    from models.anomaly_detector import get_anomaly_detector
    from datetime import datetime as dt

    tool = PredictionTool()
    result_str = tool.run(device_id=request.device_id, horizon_hours=request.horizon_hours)
    result = json.loads(result_str)

    if "error" in result:
        return APIResponse(code=500, message=result["error"])

    # 保存预测结果到数据库
    try:
        predicted_at = dt.now()
        for pred in result["predictions"]:
            db.add(WaterPredictionResult(
                device_id=request.device_id,
                predicted_at=predicted_at,
                target_timestamp=dt.fromisoformat(pred["target_timestamp"]),
                cod_pred=pred["cod"],
                ammonia_nitrogen_pred=pred["ammonia_nitrogen"],
                nitrate_nitrogen_pred=pred["nitrate_nitrogen"],
                model_version=result.get("model_version", "v1"),
            ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"保存预测结果失败: {e}")

    return APIResponse(data=result)


@router.get("/predictions")
async def get_latest_predictions(
    device_id: str = Query(default="WQ-001"),
    db: Session = Depends(get_db),
):
    """查询最新预测结果"""
    records = (
        db.query(WaterPredictionResult)
        .filter(WaterPredictionResult.device_id == device_id)
        .order_by(desc(WaterPredictionResult.predicted_at))
        .limit(24)
        .all()
    )

    if not records:
        return APIResponse(data={"device_id": device_id, "predictions": [], "message": "暂无预测数据，请先调用 POST /predict"})

    data = []
    for r in records:
        data.append({
            "target_timestamp": r.target_timestamp.isoformat() if r.target_timestamp else None,
            "cod": r.cod_pred,
            "ammonia_nitrogen": r.ammonia_nitrogen_pred,
            "nitrate_nitrogen": r.nitrate_nitrogen_pred,
        })

    return APIResponse(data={"device_id": device_id, "predictions": data})