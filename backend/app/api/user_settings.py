from fastapi import APIRouter, Depends, HTTPException, status
import logging
from sqlalchemy.orm import Session
from typing import Dict, Any

from ..database import get_db
from ..models.user import User
from ..services.user_settings_service import user_settings_service
from ..schemas.user_settings import UserSettingsOut, UserSettingsUpdate
from ..utils.auth import get_current_active_user

router = APIRouter()

@router.get("/settings", response_model=UserSettingsOut)
async def get_user_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的设置"""
    try:
        # 获取用户设置
        settings_dict = user_settings_service.get_settings_dict(db, current_user.id)
        
        # 返回设置字典
        return settings_dict
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"获取用户设置失败: {str(e)}")
        
        # 返回默认设置
        try:
            return user_settings_service.get_default_settings()
        except Exception as ex:
            logger.error(f"获取默认设置失败: {str(ex)}")
            # 如果什么都失败了，返回硬编码的默认值
            return {
                "language": "zh_CN",
                "theme": "system",
                "notificationEnabled": True,
                "autoDownload": False,
                "autoDownloadMaxSize": 10,
                "thumbnailsEnabled": True,
                "timezone": "Asia/Shanghai",
                "dateFormat": "YYYY-MM-DD HH:mm",
                "defaultDownloadPath": "downloads",
                "displayDensity": "default",
                "previewFilesInline": True,
                "defaultPageSize": 20,
                "developerMode": False
            }

@router.post("/settings", response_model=UserSettingsOut)
async def create_or_update_settings(
    settings: UserSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建或更新当前用户的设置"""
    logger = logging.getLogger(__name__)
    try:
        # 更新用户设置
        updated_settings_dict = user_settings_service.update_settings_dict(
            db, current_user.id, settings.settings_data
        )
        
        return updated_settings_dict
    except ValueError as e:
        logger.error(f"更新用户设置参数错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"更新用户设置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户设置失败: {str(e)}"
        )

@router.delete("/settings")
async def reset_user_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """重置当前用户的设置为默认值"""
    try:
        # 删除用户设置
        success = user_settings_service.delete_settings(db, current_user.id)
        
        if success:
            return {"message": "用户设置已重置为默认值"}
        return {"message": "用户未设置自定义配置，无需重置"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重置用户设置失败: {str(e)}"
        )