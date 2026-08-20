"""
园区智能监控服务 - 实时监测所有能源节点状态
提供节点状态采集、异常检测、告警生成
"""
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class NodeAlert:
    """节点告警"""
    node_id: str
    node_type: str
    level: AlertLevel
    message: str
    value: float
    threshold: float
    timestamp: datetime
    acknowledged: bool = False


@dataclass
class MonitoringService:
    """园区智能监控服务
    
    负责监测所有能源节点的运行状态，包括：
    - 光伏/风电出力监测
    - 储能SOC/SOH监测
    - 负荷功率监测
    - 电网交互监测
    - 功率平衡校验
    - 异常告警生成
    """
    alerts: List[NodeAlert] = field(default_factory=list)
    _anomaly_history: List[Dict] = field(default_factory=list)
    
    # 告警阈值
    SOC_LOW_THRESHOLD: float = 25.0
    SOC_CRITICAL_THRESHOLD: float = 15.0
    VOLTAGE_HIGH_THRESHOLD: float = 1.05  # pu
    VOLTAGE_LOW_THRESHOLD: float = 0.95   # pu
    POWER_IMBALANCE_THRESHOLD: float = 500.0  # kW
    RENEWABLE_LOW_THRESHOLD: float = 20.0  # %
    
    def monitor_pv(self, pv_id: str, current_power: float, capacity: float,
                   irradiance: float, temp_c: float) -> List[NodeAlert]:
        """监测光伏运行状态"""
        new_alerts = []
        capacity_factor = current_power / capacity if capacity > 0 else 0
        
        # 低出力告警（光伏应该发电时）
        current_hour = datetime.now().hour
        if 10 <= current_hour <= 14 and capacity_factor < 0.3 and irradiance > 500:
            new_alerts.append(NodeAlert(
                node_id=pv_id, node_type="PV",
                level=AlertLevel.WARNING,
                message=f"光伏出力异常偏低: {capacity_factor*100:.1f}%（辐照{irradiance:.0f}W/m²）",
                value=capacity_factor * 100, threshold=30.0,
                timestamp=datetime.now(),
            ))
        
        # 高温告警
        if temp_c > 70:
            new_alerts.append(NodeAlert(
                node_id=pv_id, node_type="PV",
                level=AlertLevel.WARNING,
                message=f"光伏组件温度过高: {temp_c:.0f}°C",
                value=temp_c, threshold=70.0,
                timestamp=datetime.now(),
            ))
        
        self.alerts.extend(new_alerts)
        return new_alerts
    
    def monitor_storage(self, storage_id: str, soc: float, soh: float,
                        temp_c: float, cycle_count: int) -> List[NodeAlert]:
        """监测储能运行状态"""
        new_alerts = []
        
        # SOC低告警
        if soc <= self.SOC_CRITICAL_THRESHOLD:
            new_alerts.append(NodeAlert(
                node_id=storage_id, node_type="Storage",
                level=AlertLevel.CRITICAL,
                message=f"储能SOC极低: {soc:.1f}%",
                value=soc, threshold=self.SOC_CRITICAL_THRESHOLD,
                timestamp=datetime.now(),
            ))
        elif soc <= self.SOC_LOW_THRESHOLD:
            new_alerts.append(NodeAlert(
                node_id=storage_id, node_type="Storage",
                level=AlertLevel.WARNING,
                message=f"储能SOC偏低: {soc:.1f}%",
                value=soc, threshold=self.SOC_LOW_THRESHOLD,
                timestamp=datetime.now(),
            ))
        
        # SOH衰减告警
        if soh < 80:
            new_alerts.append(NodeAlert(
                node_id=storage_id, node_type="Storage",
                level=AlertLevel.WARNING,
                message=f"储能健康度下降: {soh:.1f}%（已循环{cycle_count}次）",
                value=soh, threshold=80.0,
                timestamp=datetime.now(),
            ))
        
        # 温度告警
        if temp_c > 45:
            new_alerts.append(NodeAlert(
                node_id=storage_id, node_type="Storage",
                level=AlertLevel.CRITICAL,
                message=f"储能温度过高: {temp_c:.0f}°C",
                value=temp_c, threshold=45.0,
                timestamp=datetime.now(),
            ))
        elif temp_c > 35:
            new_alerts.append(NodeAlert(
                node_id=storage_id, node_type="Storage",
                level=AlertLevel.WARNING,
                message=f"储能温度偏高: {temp_c:.0f}°C",
                value=temp_c, threshold=35.0,
                timestamp=datetime.now(),
            ))
        
        self.alerts.extend(new_alerts)
        return new_alerts
    
    def monitor_grid(self, grid_id: str, current_power: float, max_power: float,
                     voltage_pu: float, frequency_hz: float) -> List[NodeAlert]:
        """监测电网交互状态"""
        new_alerts = []
        
        # 电压越限
        if voltage_pu > self.VOLTAGE_HIGH_THRESHOLD:
            new_alerts.append(NodeAlert(
                node_id=grid_id, node_type="Grid",
                level=AlertLevel.WARNING,
                message=f"电网电压偏高: {voltage_pu:.3f} pu",
                value=voltage_pu, threshold=self.VOLTAGE_HIGH_THRESHOLD,
                timestamp=datetime.now(),
            ))
        elif voltage_pu < self.VOLTAGE_LOW_THRESHOLD:
            new_alerts.append(NodeAlert(
                node_id=grid_id, node_type="Grid",
                level=AlertLevel.WARNING,
                message=f"电网电压偏低: {voltage_pu:.3f} pu",
                value=voltage_pu, threshold=self.VOLTAGE_LOW_THRESHOLD,
                timestamp=datetime.now(),
            ))
        
        # 接近功率限额
        if abs(current_power) > max_power * 0.9:
            new_alerts.append(NodeAlert(
                node_id=grid_id, node_type="Grid",
                level=AlertLevel.WARNING,
                message=f"电网交互功率接近限额: {abs(current_power):.0f}/{max_power:.0f} kW",
                value=abs(current_power), threshold=max_power * 0.9,
                timestamp=datetime.now(),
            ))
        
        # 频率偏差
        if abs(frequency_hz - 50.0) > 0.5:
            new_alerts.append(NodeAlert(
                node_id=grid_id, node_type="Grid",
                level=AlertLevel.CRITICAL,
                message=f"电网频率异常: {frequency_hz:.2f} Hz",
                value=frequency_hz, threshold=50.0,
                timestamp=datetime.now(),
            ))
        
        self.alerts.extend(new_alerts)
        return new_alerts
    
    def monitor_power_balance(self, generation: float, load: float,
                              storage: float, grid: float) -> List[NodeAlert]:
        """监测功率平衡"""
        new_alerts = []
        imbalance = generation + grid - load - storage
        
        if abs(imbalance) > self.POWER_IMBALANCE_THRESHOLD:
            new_alerts.append(NodeAlert(
                node_id="system", node_type="System",
                level=AlertLevel.CRITICAL,
                message=f"功率不平衡: {imbalance:.0f} kW（发电{generation:.0f}+电网{grid:.0f}-负荷{load:.0f}-储能{storage:.0f}）",
                value=abs(imbalance), threshold=self.POWER_IMBALANCE_THRESHOLD,
                timestamp=datetime.now(),
            ))
        
        self.alerts.extend(new_alerts)
        return new_alerts
    
    def monitor_renewable_ratio(self, ratio: float) -> List[NodeAlert]:
        """监测可再生能源占比"""
        new_alerts = []
        if ratio < self.RENEWABLE_LOW_THRESHOLD:
            new_alerts.append(NodeAlert(
                node_id="system", node_type="System",
                level=AlertLevel.WARNING,
                message=f"可再生能源占比偏低: {ratio:.1f}%",
                value=ratio, threshold=self.RENEWABLE_LOW_THRESHOLD,
                timestamp=datetime.now(),
            ))
        
        self.alerts.extend(new_alerts)
        return new_alerts
    
    def get_node_status_summary(self) -> Dict:
        """获取园区节点状态摘要"""
        total_alerts = len(self.alerts)
        critical = sum(1 for a in self.alerts if a.level == AlertLevel.CRITICAL)
        warning = sum(1 for a in self.alerts if a.level == AlertLevel.WARNING)
        info = sum(1 for a in self.alerts if a.level == AlertLevel.INFO)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_nodes": 0,  # 外部填充
            "online_nodes": 0,
            "total_alerts": total_alerts,
            "critical_alerts": critical,
            "warning_alerts": warning,
            "info_alerts": info,
            "system_status": "critical" if critical > 0 else "warning" if warning > 3 else "normal",
            "active_alerts": [
                {
                    "node_id": a.node_id,
                    "node_type": a.node_type,
                    "level": a.level.value,
                    "message": a.message,
                    "value": a.value,
                    "threshold": a.threshold,
                    "timestamp": a.timestamp.isoformat(),
                    "acknowledged": a.acknowledged,
                }
                for a in self.alerts[:20]
            ],
        }
    
    def acknowledge_alert(self, node_id: str, timestamp: str) -> bool:
        """确认告警"""
        for alert in self.alerts:
            if alert.node_id == node_id and alert.timestamp.isoformat() == timestamp:
                alert.acknowledged = True
                return True
        return False
    
    def clear_resolved_alerts(self):
        """清除已确认的告警"""
        self.alerts = [a for a in self.alerts if not a.acknowledged]


# 全局单例
_monitor_instance: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = MonitoringService()
    return _monitor_instance