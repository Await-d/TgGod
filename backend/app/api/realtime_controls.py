from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import logging

from ..core.auto_recovery_engine import get_auto_recovery_engine
from ..websocket.production_status_manager import production_status_manager


logger = logging.getLogger(__name__)
router = APIRouter()


class MaintenanceModeRequest(BaseModel):
    enabled: bool
    message: str = ""
    eta: str | None = None


@router.post("/realtime/services/recover")
async def recover_service(service_name: str = Query(..., description="服务名称")):
    try:
        engine = get_auto_recovery_engine()
        engine.register_service(service_name)
        success = await production_status_manager.attempt_service_recovery(service_name)

        return {
            "success": success,
            "data": {
                "service_name": service_name,
                "recovery_started": success,
            },
            "message": f"服务 {service_name} 恢复{'已启动' if success else '未成功启动'}",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"手动恢复服务失败: {e}")
        raise HTTPException(status_code=500, detail=f"手动恢复服务失败: {str(e)}")


@router.post("/realtime/maintenance/mode")
async def set_maintenance_mode(payload: MaintenanceModeRequest):
    try:
        await production_status_manager.set_maintenance_mode(
            enabled=payload.enabled,
            message=payload.message,
            eta=payload.eta,
        )

        return {
            "success": True,
            "data": {
                "enabled": payload.enabled,
                "message": payload.message,
                "eta": payload.eta,
            },
            "message": f"维护模式已{'开启' if payload.enabled else '关闭'}",
        }
    except Exception as e:
        logger.error(f"设置维护模式失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置维护模式失败: {str(e)}")
