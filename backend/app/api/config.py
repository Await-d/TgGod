from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel
from ..database import get_db
from ..services.config_service import config_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ConfigUpdateRequest(BaseModel):
    configs: Dict[str, str]

class ConfigResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any] = None

@router.get("/configs", response_model=ConfigResponse)
async def get_configs(db: Session = Depends(get_db)):
    """获取所有配置"""
    try:
        configs = config_service.get_all_configs(db)
        
        # 隐藏敏感信息
        for key, config in configs.items():
            if config.get("is_encrypted") and config.get("value"):
                config["value"] = "***"
        
        return ConfigResponse(
            success=True,
            message="获取配置成功",
            data=configs
        )
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail="获取配置失败")

@router.post("/configs", response_model=ConfigResponse)
async def update_configs(request: ConfigUpdateRequest, db: Session = Depends(get_db)):
    """更新配置"""
    try:
        updated_count = 0
        
        for key, value in request.configs.items():
            # 跳过空值或占位符
            if not value or value == "***":
                continue
                
            if config_service.set_config(key, value, db):
                updated_count += 1
        
        # 清除settings缓存以确保新配置生效
        from ..config import settings
        settings.clear_cache()
        config_service.clear_cache()
        
        return ConfigResponse(
            success=True,
            message=f"成功更新 {updated_count} 个配置项"
        )
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail="更新配置失败")

@router.get("/configs/{key}", response_model=ConfigResponse)
async def get_config(key: str, db: Session = Depends(get_db)):
    """获取单个配置"""
    try:
        value = config_service.get_config(key, db)
        if value is None:
            raise HTTPException(status_code=404, detail="配置项不存在")
        
        return ConfigResponse(
            success=True,
            message="获取配置成功",
            data={"key": key, "value": value}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail="获取配置失败")

@router.put("/configs/{key}", response_model=ConfigResponse)
async def set_config(key: str, value: str, db: Session = Depends(get_db)):
    """设置单个配置"""
    try:
        if config_service.set_config(key, value, db):
            # 清除settings缓存以确保新配置生效
            from ..config import settings
            settings.clear_cache()
            config_service.clear_cache()
            
            return ConfigResponse(
                success=True,
                message="设置配置成功"
            )
        else:
            raise HTTPException(status_code=500, detail="设置配置失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置配置失败: {e}")
        raise HTTPException(status_code=500, detail="设置配置失败")

@router.post("/configs/init", response_model=ConfigResponse)
async def init_configs(db: Session = Depends(get_db)):
    """初始化默认配置"""
    try:
        config_service.init_default_configs(db)
        return ConfigResponse(
            success=True,
            message="初始化配置成功"
        )
    except Exception as e:
        logger.error(f"初始化配置失败: {e}")
        raise HTTPException(status_code=500, detail="初始化配置失败")

@router.post("/configs/clear-cache", response_model=ConfigResponse)
async def clear_cache():
    """清除配置缓存"""
    try:
        from ..config import settings
        settings.clear_cache()
        config_service.clear_cache()
        
        return ConfigResponse(
            success=True,
            message="清除缓存成功"
        )
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        raise HTTPException(status_code=500, detail="清除缓存失败")

@router.get("/telegram-status", response_model=ConfigResponse)
async def get_telegram_status(db: Session = Depends(get_db)):
    """获取 Telegram API 配置状态"""
    try:
        api_id = config_service.get_config("telegram_api_id", db)
        api_hash = config_service.get_config("telegram_api_hash", db)
        
        # 检查环境变量
        env_api_id = os.environ.get("TELEGRAM_API_ID")
        env_api_hash = os.environ.get("TELEGRAM_API_HASH")
        
        # 判断配置状态
        db_configured = bool(api_id and api_id != "0" and api_hash)
        env_configured = bool(
            env_api_id and env_api_id != "your_api_id_here" and
            env_api_hash and env_api_hash != "your_api_hash_here"
        )
        
        status = {
            "db_configured": db_configured,
            "env_configured": env_configured,
            "is_configured": db_configured or env_configured,
            "db_api_id": api_id if api_id else "未设置",
            "db_api_hash": api_hash[:10] + "..." if api_hash else "未设置",
            "env_api_id": env_api_id if env_api_id and env_api_id != "your_api_id_here" else "未设置",
            "env_api_hash": env_api_hash[:10] + "..." if env_api_hash and env_api_hash != "your_api_hash_here" else "未设置"
        }
        
        return ConfigResponse(
            success=True,
            message="获取 Telegram 配置状态成功",
            data=status
        )
    except Exception as e:
        logger.error(f"获取 Telegram 配置状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取配置状态失败")

@router.post("/telegram-config", response_model=ConfigResponse)
async def set_telegram_config(api_id: int, api_hash: str, db: Session = Depends(get_db)):
    """设置 Telegram API 配置"""
    try:
        # 验证输入
        if not api_id or api_id <= 0:
            raise HTTPException(status_code=400, detail="API ID 必须是正整数")
        
        if not api_hash or len(api_hash) < 20:
            raise HTTPException(status_code=400, detail="API Hash 格式不正确")
        
        # 保存配置
        config_service.set_config("telegram_api_id", str(api_id), db)
        config_service.set_config("telegram_api_hash", api_hash, db)
        
        # 清除缓存
        from ..config import settings
        settings.clear_cache()
        config_service.clear_cache()
        
        return ConfigResponse(
            success=True,
            message="Telegram API 配置设置成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置 Telegram API 配置失败: {e}")
        raise HTTPException(status_code=500, detail="设置配置失败")
