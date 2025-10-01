"""实时事件数据模型

统一定义后端 WebSocket 推送的实时事件结构，便于前后端共享类型。
"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ServicePriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


class MaintenanceWindow(BaseModel):
    start: str
    end: str
    message: str


class ServiceInfo(BaseModel):
    name: str
    status: ServiceStatus
    priority: ServicePriority
    health_score: float = Field(..., ge=0.0, le=1.0)
    last_check: str
    uptime: float
    response_time: float
    error_count: int
    recovery_attempts: int
    message: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    recovery_suggestion: Optional[str] = None
    maintenance_window: Optional[MaintenanceWindow] = None


class SystemMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, float] = Field(default_factory=dict)
    active_connections: int
    total_tasks: int
    failed_tasks: int
    uptime: float
    load_average: list[float] = Field(default_factory=list)


class ErrorSummary(BaseModel):
    total_errors: int
    critical_errors: int
    recent_errors: int


class MaintenanceInfo(BaseModel):
    message: str
    eta: Optional[str] = None


class ProductionStatusPayload(BaseModel):
    type: str = Field("production_status", const=True)
    timestamp: str
    maintenance_mode: bool
    services: Dict[str, ServiceInfo]
    system_metrics: Optional[SystemMetrics] = None
    error_summary: ErrorSummary
    maintenance: Optional[MaintenanceInfo] = None


class RealtimeEventType(str, Enum):
    STATUS = "status"
    NOTIFICATION = "notification"
    SYSTEM_EVENT = "system_event"


class RealtimeEvent(BaseModel):
    type: RealtimeEventType
    data: Dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "ServicePriority",
    "ServiceStatus",
    "ServiceInfo",
    "SystemMetrics",
    "ProductionStatusPayload",
    "RealtimeEventType",
    "RealtimeEvent",
]
