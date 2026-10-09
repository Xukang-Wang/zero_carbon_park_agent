"""
服务层
"""
# Keep lightweight analytical services independent from legacy model imports.
def __getattr__(name):
    if name in {"MonitoringService", "get_monitoring_service", "NodeAlert", "AlertLevel"}:
        from . import monitoring_service
        return getattr(monitoring_service, name)
    if name in {"ParkDataService", "get_park_service"}:
        from . import park_service
        return getattr(park_service, name)
    raise AttributeError(name)
