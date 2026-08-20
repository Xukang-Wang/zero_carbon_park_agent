"""
zero_carbon_park_agent Agent 工作流 API 路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from db.postgres_client import get_db
from db.models import WorkflowExecution, AnomalyEvent
from schemas.water import APIResponse, WorkflowTriggerRequest

router = APIRouter(prefix="/api/v1/agent", tags=["Agent 工作流"])


AGENTS_INVOLVED = [
    "anomaly_detection_agent",
    "root_cause_agent",
    "dispatch_decision_agent",
    "task_assignment_agent",
    "report_generation_agent",
]


@router.post("/workflow/trigger")
async def trigger_workflow(
    request: WorkflowTriggerRequest,
    db: Session = Depends(get_db),
):
    """触发 Agent 工作流"""
    workflow_id = f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    # 保存工作流记录
    wf_record = WorkflowExecution(
        workflow_id=workflow_id,
        workflow_type=request.workflow_type,
        status="running",
        started_at=datetime.now(),
    )
    db.add(wf_record)
    db.commit()

    # 异步执行工作流（简化：同步执行）
    if request.workflow_type == "water_anomaly":
        from workflows.water_anomaly_workflow import run_water_anomaly_workflow
        try:
            result = run_water_anomaly_workflow(request.params)
            # 更新工作流状态
            wf_record.status = "completed"
            wf_record.completed_at = datetime.now()
            wf_record.report_content = result.get("report_content", "")
            wf_record.state_snapshot = {
                "current_step": result.get("current_step", ""),
                "anomaly_severity": result.get("anomaly_severity", ""),
                "task_id": result.get("task_id", ""),
            }
            db.commit()
        except Exception as e:
            wf_record.status = "failed"
            wf_record.error_message = str(e)
            db.commit()
            return APIResponse(code=500, message=f"工作流执行失败: {str(e)}")

    elif request.workflow_type == "daily_report":
        from workflows.water_anomaly_workflow import run_daily_report_workflow
        result = run_daily_report_workflow()
        wf_record.status = "completed"
        wf_record.completed_at = datetime.now()
        wf_record.report_content = result.get("report_content", "")
        db.commit()

    return APIResponse(data={
        "workflow_id": workflow_id,
        "workflow_type": request.workflow_type,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "agents_involved": AGENTS_INVOLVED,
    })


@router.get("/workflow/{workflow_id}/status")
async def get_workflow_status(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """查询工作流状态"""
    wf = db.query(WorkflowExecution).filter_by(workflow_id=workflow_id).first()

    if not wf:
        return APIResponse(code=404, message=f"工作流 {workflow_id} 不存在")

    return APIResponse(data={
        "workflow_id": wf.workflow_id,
        "status": wf.status,
        "current_step": wf.state_snapshot.get("current_step") if wf.state_snapshot else None,
        "started_at": wf.started_at.isoformat() if wf.started_at else None,
        "completed_at": wf.completed_at.isoformat() if wf.completed_at else None,
        "has_report": bool(wf.report_content),
        "error_message": wf.error_message,
    })


@router.get("/workflow/{workflow_id}/report")
async def get_workflow_report(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """获取工作流报告"""
    wf = db.query(WorkflowExecution).filter_by(workflow_id=workflow_id).first()

    if not wf:
        return APIResponse(code=404, message=f"工作流 {workflow_id} 不存在")

    if not wf.report_content:
        return APIResponse(code=404, message="报告尚未生成")

    return APIResponse(data={
        "workflow_id": wf.workflow_id,
        "report": wf.report_content,
        "generated_at": wf.completed_at.isoformat() if wf.completed_at else None,
    })


@router.get("/anomaly/events")
async def get_anomaly_events(
    status: str = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """查询异常事件列表"""
    query = db.query(AnomalyEvent)
    if status:
        query = query.filter(AnomalyEvent.status == status)
    events = query.order_by(AnomalyEvent.detected_at.desc()).limit(limit).all()

    data = []
    for e in events:
        data.append({
            "id": e.id,
            "event_type": e.event_type,
            "severity": e.severity,
            "source": e.source,
            "description": e.description,
            "predicted_value": e.predicted_value,
            "threshold_value": e.threshold_value,
            "detected_at": e.detected_at.isoformat() if e.detected_at else None,
            "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
            "workflow_id": e.workflow_id,
            "status": e.status,
        })

    return APIResponse(data={"events": data, "total": len(data)})


@router.get("/anomaly/events/{event_id}")
async def get_anomaly_event_detail(
    event_id: int,
    db: Session = Depends(get_db),
):
    """查询异常事件详情"""
    e = db.query(AnomalyEvent).filter_by(id=event_id).first()

    if not e:
        return APIResponse(code=404, message=f"事件 {event_id} 不存在")

    return APIResponse(data={
        "id": e.id,
        "event_type": e.event_type,
        "severity": e.severity,
        "source": e.source,
        "description": e.description,
        "predicted_value": e.predicted_value,
        "threshold_value": e.threshold_value,
        "detected_at": e.detected_at.isoformat() if e.detected_at else None,
        "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
        "workflow_id": e.workflow_id,
        "root_cause": e.root_cause,
        "resolution": e.resolution,
        "status": e.status,
    })