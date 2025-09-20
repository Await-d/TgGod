"""TgGod 任务管理API模块

该模块提供任务管理的RESTful API端点，负责处理:

- 下载任务的创建、修改、删除和查询
- 任务状态管理(开始、暂停、停止、重启)
- 任务-规则关联关系管理
- 任务执行进度监控和统计
- 任务调度配置和历史记录
- 媒体文件组织和Jellyfin集成配置

API端点分类:
    CRUD操作: POST/GET/PUT/DELETE /tasks/* - 基本任务管理
    执行控制: POST /tasks/{id}/(start|pause|stop|restart) - 任务执行控制
    监控查询: GET /tasks/{id}/(status|progress|logs) - 监控和统计
    规则管理: POST/DELETE /tasks/{id}/rules - 任务规则关联
    调度管理: POST/PUT /tasks/{id}/schedule - 任务调度配置

Features:
    - 支持一次性和定时任务两种类型
    - 灵活的规则关联和优先级管理
    - 完整的任务生命周期管理
    - 实时进度监控和状态推送
    - Jellyfin媒体库集成配置
    - 详细的错误处理和日志记录
    - 批量操作和并发控制

Author: TgGod Team
Version: 1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, Query
import asyncio
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.rule import DownloadTask
from ..models.telegram import TelegramGroup
from ..models.rule import FilterRule
from ..models.task_rule_association import TaskRuleAssociation
from ..services.task_execution_service import task_execution_service
from ..core.error_handler import global_error_handler, operation_context
from ..services.service_monitor import ServiceMonitor
from ..websocket.manager import websocket_manager
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ProductionTaskExecutionManager:
    """生产级任务执行管理器

    提供完全可靠的任务执行服务，集成统一错误处理、服务监控和自动恢复机制。
    绝对不使用Mock服务，确保所有任务在生产环境中正确执行。

    Features:
        - 统一错误处理和日志记录
        - 服务健康监控和自动恢复
        - WebSocket实时状态推送
        - 完整的故障预防和处理
        - 零Mock依赖的生产架构
    """

    def __init__(self):
        self.service_monitor = ServiceMonitor()
        self._initialization_lock = asyncio.Lock()
        self._initialized = False

    async def _ensure_service_ready(self) -> bool:
        """确保任务执行服务已准备就绪"""
        async with self._initialization_lock:
            if not self._initialized:
                with operation_context("ProductionTaskExecutionManager", "initialize_service") as ctx:
                    try:
                        # 启动服务监控
                        monitor_result = await self.service_monitor.start_monitoring()
                        if not monitor_result.success:
                            raise Exception(f"服务监控启动失败: {monitor_result.error}")

                        # 初始化任务执行服务
                        await task_execution_service.initialize()

                        # 验证服务状态
                        if not hasattr(task_execution_service, '_initialized') or not task_execution_service._initialized:
                            raise Exception("任务执行服务初始化验证失败")

                        self._initialized = True
                        logger.info("生产任务执行管理器初始化完成")

                        # 发送状态更新
                        await websocket_manager.broadcast_message({
                            "type": "status",
                            "message": "任务执行服务已就绪",
                            "status": "ready",
                            "timestamp": datetime.now().isoformat()
                        })

                        return True

                    except Exception as e:
                        logger.error(f"任务执行服务初始化失败: {e}")

                        # 发送错误状态
                        await websocket_manager.broadcast_message({
                            "type": "status",
                            "message": f"任务执行服务初始化失败: {str(e)}",
                            "status": "error",
                            "timestamp": datetime.now().isoformat()
                        })

                        raise HTTPException(
                            status_code=503,
                            detail=f"任务执行服务不可用: {str(e)}。请检查系统状态或联系管理员。"
                        )

            return self._initialized

    async def execute_task_operation(self, operation_name: str, task_id: int, **kwargs):
        """执行任务操作（start/pause/stop等）"""
        with operation_context("ProductionTaskExecutionManager", operation_name, task_id=task_id) as ctx:
            # 确保服务就绪
            await self._ensure_service_ready()

            # 获取操作方法
            operation_method = getattr(task_execution_service, operation_name, None)
            if not operation_method:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的任务操作: {operation_name}"
                )

            # 执行操作
            try:
                result = await operation_method(task_id, **kwargs)

                # 发送成功状态
                await websocket_manager.broadcast_message({
                    "type": "progress",
                    "task_id": task_id,
                    "operation": operation_name,
                    "status": "success",
                    "timestamp": datetime.now().isoformat()
                })

                return result

            except Exception as e:
                # 发送错误状态
                await websocket_manager.broadcast_message({
                    "type": "progress",
                    "task_id": task_id,
                    "operation": operation_name,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })

                raise HTTPException(
                    status_code=500,
                    detail=f"任务操作失败: {str(e)}"
                )

# 全局生产任务执行管理器实例
production_task_manager = ProductionTaskExecutionManager()

# Pydantic数据模型
class TaskRuleAssociation(BaseModel):
    """任务-规则关联配置模型

    定义任务与过滤规则之间的关联关系配置。

    Attributes:
        rule_id (int): 过滤规则ID，关联到FilterRule表
        is_active (bool): 规则是否激活，默认True
        priority (int): 规则优先级，数值越小优先级越高，默认0
    """
    rule_id: int
    is_active: bool = True
    priority: int = 0

class TaskCreate(BaseModel):
    """创建下载任务的请求模型

    包含创建新下载任务所需的所有配置参数。

    Attributes:
        name (str): 任务名称，用于标识和管理
        group_id (int): 目标Telegram群组ID
        rule_ids (List[int]): 应用的过滤规则ID列表
        download_path (str): 文件下载保存路径
        date_from (Optional[datetime]): 消息过滤开始时间，为空表示不限制
        date_to (Optional[datetime]): 消息过滤结束时间，为空表示不限制

        # Jellyfin媒体库集成配置
        use_jellyfin_structure (bool): 是否使用Jellyfin目录结构，默认False
        include_metadata (bool): 是否生成NFO元数据文件，默认True
        download_thumbnails (bool): 是否下载缩略图，默认True
        use_series_structure (bool): 是否使用剧集目录结构，默认False
        organize_by_date (bool): 是否按日期组织文件，默认True
        max_filename_length (int): 文件名最大长度限制，默认150
        thumbnail_size (str): 缩略图尺寸格式，默认"400x300"
        poster_size (str): 海报图尺寸格式，默认"600x900"
        fanart_size (str): 艺术图尺寸格式，默认"1920x1080"

        # 任务调度配置
        task_type (Optional[str]): 任务类型(once/recurring)，默认"once"
        schedule_type (Optional[str]): 调度类型(interval/cron)，为空表示一次性任务
        schedule_config (Optional[dict]): 调度配置参数
        max_runs (Optional[int]): 最大执行次数限制，为空表示不限制
    """
    name: str
    group_id: int
    rule_ids: List[int]  # 改为规则ID列表
    download_path: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    # Jellyfin 配置
    use_jellyfin_structure: bool = False
    include_metadata: bool = True
    download_thumbnails: bool = True
    use_series_structure: bool = False
    organize_by_date: bool = True
    max_filename_length: int = 150
    thumbnail_size: str = "400x300"
    poster_size: str = "600x900"
    fanart_size: str = "1920x1080"

    # 调度配置
    task_type: Optional[str] = "once"
    schedule_type: Optional[str] = None
    schedule_config: Optional[dict] = None
    max_runs: Optional[int] = None

class TaskUpdate(BaseModel):
    """更新下载任务的请求模型

    用于修改现有下载任务配置的部分更新模型。
    所有字段均为可选，只更新提供的字段。

    Attributes:
        name (Optional[str]): 新的任务名称
        group_id (Optional[int]): 新的目标群组ID
        rule_ids (Optional[List[int]]): 新的过滤规则ID列表
        download_path (Optional[str]): 新的下载路径
        date_from (Optional[datetime]): 新的开始时间过滤
        date_to (Optional[datetime]): 新的结束时间过滤

        # Jellyfin媒体库配置更新
        use_jellyfin_structure (Optional[bool]): 是否使用Jellyfin结构
        include_metadata (Optional[bool]): 是否包含元数据
        download_thumbnails (Optional[bool]): 是否下载缩略图
        use_series_structure (Optional[bool]): 是否使用剧集结构
        organize_by_date (Optional[bool]): 是否按日期组织
        max_filename_length (Optional[int]): 文件名长度限制
        thumbnail_size (Optional[str]): 缩略图尺寸
        poster_size (Optional[str]): 海报尺寸
        fanart_size (Optional[str]): 艺术图尺寸

        # 调度配置更新
        task_type (Optional[str]): 任务类型
        schedule_type (Optional[str]): 调度类型
        schedule_config (Optional[dict]): 调度配置
        max_runs (Optional[int]): 最大运行次数
    """
    name: Optional[str] = None
    group_id: Optional[int] = None
    rule_ids: Optional[List[int]] = None
    download_path: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    # Jellyfin 配置
    use_jellyfin_structure: Optional[bool] = None
    include_metadata: Optional[bool] = None
    download_thumbnails: Optional[bool] = None
    use_series_structure: Optional[bool] = None
    organize_by_date: Optional[bool] = None
    max_filename_length: Optional[int] = None
    thumbnail_size: Optional[str] = None
    poster_size: Optional[str] = None
    fanart_size: Optional[str] = None

    # 调度配置
    task_type: Optional[str] = None
    schedule_type: Optional[str] = None
    schedule_config: Optional[dict] = None
    max_runs: Optional[int] = None

class TaskRuleAssociationResponse(BaseModel):
    """任务-规则关联关系响应模型

    表示任务与过滤规则关联关系的详细信息。

    Attributes:
        rule_id (int): 规则ID
        rule_name (str): 规则显示名称
        is_active (bool): 规则是否激活
        priority (int): 规则优先级
    """
    rule_id: int
    rule_name: str
    is_active: bool
    priority: int

class TaskResponse(BaseModel):
    """下载任务详细信息响应模型

    返回完整的任务信息，包括关联的规则和执行状态。

    Attributes:
        id (int): 任务唯一标识ID
        name (str): 任务名称
        group_id (int): 关联的Telegram群组ID
        rules (List[TaskRuleAssociationResponse]): 关联的过滤规则列表
        status (str): 任务执行状态(pending/running/completed/failed/paused)
        progress (int): 任务执行进度百分比(0-100)
    """
    id: int
    name: str
    group_id: int
    rules: List[TaskRuleAssociationResponse]  # 改为规则列表
    status: str
    progress: int
    total_messages: int
    downloaded_messages: int
    download_path: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    # Jellyfin 配置
    use_jellyfin_structure: bool = False
    include_metadata: bool = True
    download_thumbnails: bool = True
    use_series_structure: bool = False
    organize_by_date: bool = True
    max_filename_length: int = 150
    thumbnail_size: str = "400x300"
    poster_size: str = "600x900"
    fanart_size: str = "1920x1080"
    
    # 调度配置
    task_type: Optional[str] = "once"
    schedule_type: Optional[str] = None
    schedule_config: Optional[dict] = None
    next_run_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None
    is_active: Optional[bool] = True
    max_runs: Optional[int] = None
    run_count: Optional[int] = 0
    
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True

@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    group_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取下载任务列表

    查询并返回下载任务列表，支持按群组、状态过滤和分页查询。
    每个任务包含完整的配置信息、执行状态和关联的过滤规则。

    Args:
        group_id (Optional[int]): 过滤指定群组的任务，为空返回所有群组任务
        status (Optional[str]): 过滤指定状态的任务(pending/running/completed/failed/paused)
        skip (int): 跳过的记录数，用于分页，默认0，最小0
        limit (int): 返回的最大记录数，默认100，范围1-1000
        db (Session): 数据库会话实例

    Returns:
        List[TaskResponse]: 任务列表，每个任务包含完整的配置和状态信息

    Raises:
        HTTPException: 500 - 数据库查询失败或其他内部错误

    Example:
        ```http
        GET /api/tasks?group_id=123&status=running&skip=0&limit=50
        ```

    Note:
        - 结果按创建时间倒序排列，最新创建的任务在前
        - 自动处理数据库结构兼容性问题
        - 包含完整的Jellyfin和调度配置信息
        - 规则信息按优先级降序排列
    """
    try:
        query = db.query(DownloadTask)
        
        if group_id:
            query = query.filter(DownloadTask.group_id == group_id)
        
        if status:
            query = query.filter(DownloadTask.status == status)
        
        tasks = query.order_by(DownloadTask.created_at.desc()).offset(skip).limit(limit).all()
        
        # 为每个任务构建完整的响应数据
        task_responses = []
        for task in tasks:
            # 获取规则关联信息
            from ..models.task_rule_association import TaskRuleAssociation
            from ..models.rule import FilterRule
            
            rule_associations = db.query(TaskRuleAssociation).filter(
                TaskRuleAssociation.task_id == task.id,
                TaskRuleAssociation.is_active == True
            ).order_by(TaskRuleAssociation.priority.desc()).all()
            
            rules_info = []
            for assoc in rule_associations:
                rule = db.query(FilterRule).filter(FilterRule.id == assoc.rule_id).first()
                if rule:
                    rules_info.append(TaskRuleAssociationResponse(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        is_active=assoc.is_active,
                        priority=assoc.priority
                    ))
            
            # 构建任务响应数据
            response_data = {
                "id": task.id,
                "name": task.name,
                "group_id": task.group_id,
                "rules": rules_info,
                "status": task.status,
                "progress": task.progress,
                "total_messages": task.total_messages,
                "downloaded_messages": task.downloaded_messages,
                "download_path": task.download_path,
                "date_from": task.date_from,
                "date_to": task.date_to,
                
                # Jellyfin 配置
                "use_jellyfin_structure": getattr(task, 'use_jellyfin_structure', False),
                "include_metadata": getattr(task, 'include_metadata', True),
                "download_thumbnails": getattr(task, 'download_thumbnails', True),
                "use_series_structure": getattr(task, 'use_series_structure', False),
                "organize_by_date": getattr(task, 'organize_by_date', True),
                "max_filename_length": getattr(task, 'max_filename_length', 150),
                "thumbnail_size": getattr(task, 'thumbnail_size', '400x300'),
                "poster_size": getattr(task, 'poster_size', '600x900'),
                "fanart_size": getattr(task, 'fanart_size', '1920x1080'),
                
                # 调度配置
                "task_type": getattr(task, 'task_type', 'once'),
                "schedule_type": getattr(task, 'schedule_type', None),
                "schedule_config": getattr(task, 'schedule_config', None),
                "next_run_time": getattr(task, 'next_run_time', None),
                "last_run_time": getattr(task, 'last_run_time', None),
                "is_active": getattr(task, 'is_active', True),
                "max_runs": getattr(task, 'max_runs', None),
                "run_count": getattr(task, 'run_count', 0),
                
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "completed_at": task.completed_at,
                "error_message": task.error_message
            }
            
            task_responses.append(TaskResponse(**response_data))
        
        return task_responses
    except Exception as e:
        logger.error(f"查询任务列表失败: {str(e)}")
        # 如果是数据库结构问题，返回空列表
        if "no such column" in str(e).lower() or "unknown column" in str(e).lower():
            logger.warning("检测到数据库结构问题，建议重启应用以触发自动修复")
            return []
        raise HTTPException(status_code=500, detail=f"查询任务失败: {str(e)}")

@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db)
):
    """创建新的下载任务

    根据提供的配置信息创建新的下载任务，包括目标群组、过滤规则、
    下载路径和各种配置选项。创建成功后自动建立任务与规则的关联关系。

    Args:
        task (TaskCreate): 任务创建配置，包含所有必要的任务参数
        db (Session): 数据库会话实例

    Returns:
        TaskResponse: 创建成功的任务详细信息，包含分配的任务ID

    Raises:
        HTTPException:
            - 404 - 指定的群组不存在
            - 404 - 指定的过滤规则不存在
            - 500 - 数据库操作失败或其他内部错误

    Example:
        ```json
        POST /api/tasks
        {
            "name": "动漫下载任务",
            "group_id": 123,
            "rule_ids": [1, 2, 3],
            "download_path": "/downloads/anime",
            "use_jellyfin_structure": true,
            "task_type": "once"
        }
        ```

    Note:
        - 任务创建后初始状态为"pending"
        - 系统会验证所有关联的群组和规则是否存在
        - 自动处理数据库字段兼容性问题
        - 支持完整的Jellyfin媒体库集成配置
    """
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == task.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 检查所有规则是否存在
    rules = db.query(FilterRule).filter(FilterRule.id.in_(task.rule_ids)).all()
    if len(rules) != len(task.rule_ids):
        found_rule_ids = [r.id for r in rules]
        missing_rule_ids = [rid for rid in task.rule_ids if rid not in found_rule_ids]
        raise HTTPException(status_code=404, detail=f"规则不存在: {missing_rule_ids}")
    
    # 检查任务名称是否已存在
    existing_task = db.query(DownloadTask).filter(
        DownloadTask.name == task.name,
        DownloadTask.group_id == task.group_id
    ).first()
    if existing_task:
        raise HTTPException(status_code=400, detail="任务名称已存在")
    
    # 创建任务（排除rule_ids字段）
    task_data = task.dict()
    rule_ids = task_data.pop('rule_ids')
    new_task = DownloadTask(**task_data)
    db.add(new_task)
    db.flush()  # 获取任务ID，但不提交事务
    
    # 创建任务-规则关联
    for i, rule_id in enumerate(rule_ids):
        association = TaskRuleAssociation(
            task_id=new_task.id,
            rule_id=rule_id,
            is_active=True,
            priority=i  # 按照传入顺序设置优先级
        )
        db.add(association)
    
    db.commit()
    db.refresh(new_task)
    
    # 构建响应数据
    task_rules = []
    for assoc in new_task.rule_associations:
        task_rules.append(TaskRuleAssociationResponse(
            rule_id=assoc.rule_id,
            rule_name=assoc.rule.name,
            is_active=assoc.is_active,
            priority=assoc.priority
        ))
    
    # 构建完整响应
    response_data = {
        "id": new_task.id,
        "name": new_task.name,
        "group_id": new_task.group_id,
        "rules": task_rules,
        "status": new_task.status,
        "progress": new_task.progress,
        "total_messages": new_task.total_messages,
        "downloaded_messages": new_task.downloaded_messages,
        "download_path": new_task.download_path,
        "date_from": new_task.date_from,
        "date_to": new_task.date_to,
        "use_jellyfin_structure": new_task.use_jellyfin_structure,
        "include_metadata": new_task.include_metadata,
        "download_thumbnails": new_task.download_thumbnails,
        "use_series_structure": new_task.use_series_structure,
        "organize_by_date": new_task.organize_by_date,
        "max_filename_length": new_task.max_filename_length,
        "thumbnail_size": new_task.thumbnail_size,
        "poster_size": new_task.poster_size,
        "fanart_size": new_task.fanart_size,
        "task_type": new_task.task_type,
        "schedule_type": new_task.schedule_type,
        "schedule_config": new_task.schedule_config,
        "next_run_time": new_task.next_run_time,
        "last_run_time": new_task.last_run_time,
        "is_active": new_task.is_active,
        "max_runs": new_task.max_runs,
        "run_count": new_task.run_count,
        "created_at": new_task.created_at,
        "updated_at": new_task.updated_at,
        "completed_at": new_task.completed_at,
        "error_message": new_task.error_message
    }
    
    return TaskResponse(**response_data)

@router.get("/tasks/stats")
async def get_task_stats(
    db: Session = Depends(get_db)
):
    """获取任务统计信息"""
    try:
        total_tasks = db.query(DownloadTask).count()
        running_tasks = db.query(DownloadTask).filter(DownloadTask.status == "running").count()
        completed_tasks = db.query(DownloadTask).filter(DownloadTask.status == "completed").count()
        failed_tasks = db.query(DownloadTask).filter(DownloadTask.status == "failed").count()
        
        return {
            "total": total_tasks,
            "running": running_tasks,
            "completed": completed_tasks,
            "failed": failed_tasks,
            "pending": total_tasks - running_tasks - completed_tasks - failed_tasks
        }
    except Exception as e:
        logger.error(f"获取任务统计失败: {str(e)}")
        # 如果是数据库结构问题，返回默认统计
        if "no such column" in str(e).lower() or "unknown column" in str(e).lower():
            logger.warning("检测到数据库结构问题，返回默认统计信息")
            return {
                "total": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "pending": 0
            }
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """获取单个任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

@router.post("/tasks/{task_id}/start")
async def start_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """启动任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status == "running":
        raise HTTPException(status_code=400, detail="任务已在运行中")
    
    # 更新任务状态
    task.status = "running"
    task.progress = 0
    task.error_message = None
    db.commit()
    
    # 启动实际的下载任务
    try:
        success = await production_task_manager.execute_task_operation("start_task", task_id)
        if not success:
            task.status = "failed"
            task.error_message = "启动任务执行服务失败"
            db.commit()
            raise HTTPException(status_code=500, detail="启动任务执行服务失败")
    except HTTPException:
        # 重新抛出HTTP异常
        task.status = "failed"
        task.error_message = "启动任务执行服务失败"
        db.commit()
        raise
    except Exception as e:
        task.status = "failed"
        task.error_message = f"启动任务失败: {str(e)}"
        db.commit()
        raise HTTPException(status_code=500, detail=f"启动任务失败: {str(e)}")
    
    return {"message": "任务启动成功"}

@router.post("/tasks/{task_id}/pause")
async def pause_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """暂停任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status != "running":
        raise HTTPException(status_code=400, detail="任务未运行，无法暂停")
    
    # 暂停实际的下载任务
    try:
        success = await production_task_manager.execute_task_operation("pause_task", task_id)
        if not success:
            raise HTTPException(status_code=400, detail="暂停任务失败，任务可能未在运行")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"暂停任务失败: {str(e)}")
    
    return {"message": "任务暂停成功"}

@router.post("/tasks/{task_id}/stop")
async def stop_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """停止任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="任务已完成或失败，无法停止")
    
    # 停止实际的下载任务
    try:
        success = await production_task_manager.execute_task_operation("stop_task", task_id)
        if not success:
            raise HTTPException(status_code=400, detail="停止任务失败，任务可能未在运行")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止任务失败: {str(e)}")
    
    return {"message": "任务停止成功"}

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db)
):
    """更新任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status == "running":
        raise HTTPException(status_code=400, detail="任务正在运行，无法更新")
    
    # 处理规则关联更新
    rule_ids = None
    update_data = task_update.dict(exclude_unset=True)
    if 'rule_ids' in update_data:
        rule_ids = update_data.pop('rule_ids')  # 从update_data中移除，单独处理
        
        # 验证规则存在
        if rule_ids:
            from ..models.rule import FilterRule
            existing_rules = db.query(FilterRule).filter(FilterRule.id.in_(rule_ids)).all()
            if len(existing_rules) != len(rule_ids):
                raise HTTPException(status_code=400, detail="部分规则不存在")
    
    # 验证群组存在（如果提供了group_id）
    if 'group_id' in update_data:
        from ..models.telegram import TelegramGroup
        group = db.query(TelegramGroup).filter(TelegramGroup.id == update_data['group_id']).first()
        if not group:
            raise HTTPException(status_code=400, detail="指定的群组不存在")
    
    # 更新任务基本字段
    for field, value in update_data.items():
        setattr(task, field, value)
    
    # 更新规则关联
    if rule_ids is not None:
        from ..models.task_rule_association import TaskRuleAssociation
        
        # 删除旧的规则关联
        db.query(TaskRuleAssociation).filter(TaskRuleAssociation.task_id == task_id).delete()
        
        # 创建新的规则关联
        for i, rule_id in enumerate(rule_ids):
            association = TaskRuleAssociation(
                task_id=task_id,
                rule_id=rule_id,
                is_active=True,
                priority=len(rule_ids) - i  # 根据顺序设置优先级
            )
            db.add(association)
    
    task.updated_at = datetime.now()
    db.commit()
    db.refresh(task)
    
    # 构建响应数据（包含规则关联信息）
    from ..models.task_rule_association import TaskRuleAssociation
    from ..models.rule import FilterRule
    
    # 获取规则关联信息
    rule_associations = db.query(TaskRuleAssociation).filter(
        TaskRuleAssociation.task_id == task_id,
        TaskRuleAssociation.is_active == True
    ).order_by(TaskRuleAssociation.priority.desc()).all()
    
    rules_info = []
    for assoc in rule_associations:
        rule = db.query(FilterRule).filter(FilterRule.id == assoc.rule_id).first()
        if rule:
            rules_info.append(TaskRuleAssociationResponse(
                rule_id=rule.id,
                rule_name=rule.name,
                is_active=assoc.is_active,
                priority=assoc.priority
            ))
    
    # 构建任务响应数据
    response_data = {
        "id": task.id,
        "name": task.name,
        "group_id": task.group_id,
        "rules": rules_info,
        "status": task.status,
        "progress": task.progress,
        "total_messages": task.total_messages,
        "downloaded_messages": task.downloaded_messages,
        "download_path": task.download_path,
        "date_from": task.date_from,
        "date_to": task.date_to,
        "task_type": getattr(task, 'task_type', 'once'),
        "schedule_type": getattr(task, 'schedule_type', None),
        "schedule_config": getattr(task, 'schedule_config', None),
        "next_run_time": getattr(task, 'next_run_time', None),
        "last_run_time": getattr(task, 'last_run_time', None),
        "is_active": getattr(task, 'is_active', True),
        "max_runs": getattr(task, 'max_runs', None),
        "run_count": getattr(task, 'run_count', 0),
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "completed_at": task.completed_at,
        "error_message": task.error_message
    }
    
    return TaskResponse(**response_data)

@router.post("/tasks/{task_id}/restart")
async def restart_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """重启任务 - 停止当前任务并重新开始"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 如果任务正在运行，先停止它
    if task.status == "running":
        try:
            await production_task_manager.execute_task_operation("stop_task", task_id)
            logger.info(f"任务 {task_id} 已停止，准备重启")
        except Exception as e:
            logger.error(f"停止任务 {task_id} 失败: {e}")
    
    # 重置任务状态
    task.status = "pending"
    task.progress = 0
    task.downloaded_messages = 0
    task.error_message = None
    task.updated_at = datetime.now()
    db.commit()
    
    # 启动任务
    try:
        success = await production_task_manager.execute_task_operation("start_task", task_id)
        if not success:
            task.status = "failed"
            task.error_message = "重启任务失败"
            db.commit()
            raise HTTPException(status_code=500, detail="重启任务失败")

        task.status = "running"
        db.commit()
        logger.info(f"任务 {task_id} 重启成功")

    except HTTPException:
        task.status = "failed"
        task.error_message = "重启任务失败"
        db.commit()
        raise
    except Exception as e:
        task.status = "failed"
        task.error_message = f"重启任务失败: {str(e)}"
        db.commit()
        logger.error(f"重启任务 {task_id} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"重启任务失败: {str(e)}")
    
    return {"message": "任务重启成功"}

@router.post("/tasks/{task_id}/retry")
async def retry_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """重试失败的任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 只有失败的任务才能重试
    if task.status not in ["failed", "completed", "stopped"]:
        raise HTTPException(status_code=400, detail="只有失败、完成或停止的任务才能重试")
    
    # 重置任务状态但保留进度信息
    original_downloaded = task.downloaded_messages or 0
    task.status = "pending"
    task.error_message = None
    task.updated_at = datetime.now()
    db.commit()
    
    # 启动任务
    try:
        success = await production_task_manager.execute_task_operation("start_task", task_id)
        if not success:
            task.status = "failed"
            task.error_message = "重试任务失败"
            db.commit()
            raise HTTPException(status_code=500, detail="重试任务失败")

        task.status = "running"
        db.commit()
        logger.info(f"任务 {task_id} 重试成功，从 {original_downloaded} 个文件开始继续")

    except HTTPException:
        task.status = "failed"
        task.error_message = "重试任务失败"
        db.commit()
        raise
    except Exception as e:
        task.status = "failed"
        task.error_message = f"重试任务失败: {str(e)}"
        db.commit()
        logger.error(f"重试任务 {task_id} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"重试任务失败: {str(e)}")
    
    return {"message": f"任务重试成功，从第 {original_downloaded + 1} 个文件开始继续"}

@router.post("/tasks/{task_id}/resume")
async def resume_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """恢复暂停的任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 只有暂停的任务才能恢复
    if task.status != "paused":
        raise HTTPException(status_code=400, detail="只有暂停的任务才能恢复")
    
    # 恢复任务
    try:
        success = await production_task_manager.execute_task_operation("start_task", task_id)
        if not success:
            task.error_message = "恢复任务失败"
            db.commit()
            raise HTTPException(status_code=500, detail="恢复任务失败")

        task.status = "running"
        task.updated_at = datetime.now()
        db.commit()
        logger.info(f"任务 {task_id} 恢复成功")

    except HTTPException:
        task.error_message = "恢复任务失败"
        db.commit()
        raise
    except Exception as e:
        task.error_message = f"恢复任务失败: {str(e)}"
        db.commit()
        logger.error(f"恢复任务 {task_id} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"恢复任务失败: {str(e)}")
    
    return {"message": "任务恢复成功"}

@router.post("/tasks/{task_id}/reset")
async def reset_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """重置任务 - 清空进度，重置到初始状态"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 如果任务正在运行，不允许重置
    if task.status == "running":
        raise HTTPException(status_code=400, detail="任务正在运行，请先停止任务")
    
    # 重置任务状态
    task.status = "pending"
    task.progress = 0
    task.downloaded_messages = 0
    task.total_messages = None
    task.error_message = None
    task.completed_at = None
    task.updated_at = datetime.now()
    db.commit()
    
    logger.info(f"任务 {task_id} 已重置")
    return {"message": "任务重置成功"}

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    force: bool = Query(False, description="强制删除，忽略任务状态"),
    db: Session = Depends(get_db)
):
    """删除任务"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status == "running" and not force:
        raise HTTPException(status_code=400, detail="任务正在运行，无法删除。使用force=true参数强制删除")
    
    # 如果是强制删除，先尝试停止任务
    if task.status == "running" and force:
        try:
            await production_task_manager.execute_task_operation("stop_task", task_id)
            logger.info(f"强制删除时已停止运行中的任务 {task_id}")
        except Exception as e:
            logger.warning(f"强制删除时停止任务失败，继续删除: {e}")
    
    db.delete(task)
    db.commit()
    
    if force:
        return {"message": "任务强制删除成功"}
    else:
        return {"message": "任务删除成功"}

@router.post("/tasks/batch")
async def batch_task_operation(
    operation: str,
    task_ids: List[int],
    force: bool = Query(False, description="强制操作，忽略任务状态"),
    db: Session = Depends(get_db)
):
    """批量任务操作"""
    if not task_ids:
        raise HTTPException(status_code=400, detail="任务ID列表不能为空")
    
    valid_operations = ["start", "stop", "pause", "restart", "retry", "reset", "delete"]
    if operation not in valid_operations:
        raise HTTPException(status_code=400, detail=f"无效操作，支持的操作: {', '.join(valid_operations)}")
    
    results = []
    successful = 0
    failed = 0
    
    for task_id in task_ids:
        try:
            task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
            if not task:
                results.append({"task_id": task_id, "status": "failed", "message": "任务不存在"})
                failed += 1
                continue
            
            # 根据操作类型执行相应操作
            if operation == "start":
                if task.status == "running":
                    results.append({"task_id": task_id, "status": "skipped", "message": "任务已在运行"})
                else:
                    task.status = "running"
                    success = await production_task_manager.execute_task_operation("start_task", task_id)
                    if success:
                        results.append({"task_id": task_id, "status": "success", "message": "任务启动成功"})
                        successful += 1
                    else:
                        task.status = "failed"
                        results.append({"task_id": task_id, "status": "failed", "message": "任务启动失败"})
                        failed += 1
                        
            elif operation == "stop":
                if task.status != "running":
                    results.append({"task_id": task_id, "status": "skipped", "message": "任务未运行"})
                else:
                    success = await production_task_manager.execute_task_operation("stop_task", task_id)
                    if success:
                        results.append({"task_id": task_id, "status": "success", "message": "任务停止成功"})
                        successful += 1
                    else:
                        results.append({"task_id": task_id, "status": "failed", "message": "任务停止失败"})
                        failed += 1
                        
            elif operation == "pause":
                if task.status != "running":
                    results.append({"task_id": task_id, "status": "skipped", "message": "任务未运行"})
                else:
                    success = await production_task_manager.execute_task_operation("pause_task", task_id)
                    if success:
                        results.append({"task_id": task_id, "status": "success", "message": "任务暂停成功"})
                        successful += 1
                    else:
                        results.append({"task_id": task_id, "status": "failed", "message": "任务暂停失败"})
                        failed += 1
                        
            elif operation == "restart":
                if task.status == "running":
                    await production_task_manager.execute_task_operation("stop_task", task_id)
                task.status = "pending"
                task.progress = 0
                task.downloaded_messages = 0
                task.error_message = None
                success = await production_task_manager.execute_task_operation("start_task", task_id)
                if success:
                    task.status = "running"
                    results.append({"task_id": task_id, "status": "success", "message": "任务重启成功"})
                    successful += 1
                else:
                    task.status = "failed"
                    results.append({"task_id": task_id, "status": "failed", "message": "任务重启失败"})
                    failed += 1
                    
            elif operation == "retry":
                if task.status not in ["failed", "completed", "stopped"]:
                    results.append({"task_id": task_id, "status": "skipped", "message": "任务状态不支持重试"})
                else:
                    task.status = "pending"
                    task.error_message = None
                    success = await production_task_manager.execute_task_operation("start_task", task_id)
                    if success:
                        task.status = "running"
                        results.append({"task_id": task_id, "status": "success", "message": "任务重试成功"})
                        successful += 1
                    else:
                        task.status = "failed"
                        results.append({"task_id": task_id, "status": "failed", "message": "任务重试失败"})
                        failed += 1
                        
            elif operation == "reset":
                if task.status == "running":
                    results.append({"task_id": task_id, "status": "skipped", "message": "任务正在运行，无法重置"})
                else:
                    task.status = "pending"
                    task.progress = 0
                    task.downloaded_messages = 0
                    task.total_messages = None
                    task.error_message = None
                    task.completed_at = None
                    results.append({"task_id": task_id, "status": "success", "message": "任务重置成功"})
                    successful += 1
                    
            elif operation == "delete":
                if task.status == "running" and not force:
                    results.append({"task_id": task_id, "status": "skipped", 
                                  "message": "任务正在运行，无法删除。使用force=true强制删除"})
                else:
                    # 如果是强制删除运行中的任务，先尝试停止
                    if task.status == "running" and force:
                        try:
                            await production_task_manager.execute_task_operation("stop_task", task_id)
                            logger.info(f"批量强制删除时已停止运行中的任务 {task_id}")
                        except Exception as e:
                            logger.warning(f"批量强制删除时停止任务失败，继续删除: {e}")
                    
                    db.delete(task)
                    message = "任务强制删除成功" if (task.status == "running" and force) else "任务删除成功"
                    results.append({"task_id": task_id, "status": "success", "message": message})
                    successful += 1
            
            db.commit()
            
        except Exception as e:
            logger.error(f"批量操作任务 {task_id} 失败: {e}")
            results.append({"task_id": task_id, "status": "failed", "message": f"操作失败: {str(e)}"})
            failed += 1
    
    return {
        "operation": operation,
        "total": len(task_ids),
        "successful": successful,
        "failed": failed,
        "results": results
    }

@router.post("/tasks/reset-orphaned")
async def reset_orphaned_tasks(db: Session = Depends(get_db)):
    """重置孤儿任务状态（处于running/paused状态但实际进程已停止的任务）"""
    try:
        # 查找所有可能的孤儿任务
        orphaned_tasks = db.query(DownloadTask).filter(
            DownloadTask.status.in_(["running", "paused"])
        ).all()
        
        reset_count = 0
        task_details = []
        
        for task in orphaned_tasks:
            original_status = task.status
            task.status = "failed"
            task.error_message = f"手动重置：原状态为{original_status}，疑似孤儿进程"
            reset_count += 1
            
            task_details.append({
                "task_id": task.id,
                "task_name": task.name,
                "original_status": original_status,
                "new_status": "failed"
            })
            
            logger.info(f"手动重置孤儿任务 {task.id}({task.name}) 状态: {original_status} -> failed")
        
        if reset_count > 0:
            db.commit()
            logger.info(f"手动重置了 {reset_count} 个孤儿任务状态")
        
        return {
            "message": f"成功重置 {reset_count} 个孤儿任务状态",
            "reset_count": reset_count,
            "tasks": task_details
        }
        
    except Exception as e:
        logger.error(f"重置孤儿任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")

@router.post("/tasks/create-and-start", response_model=TaskResponse)
async def create_and_start_task(
    task: TaskCreate,
    start_immediately: bool = True,
    db: Session = Depends(get_db)
):
    """创建任务并立即开始执行"""
    # 检查群组是否存在
    group = db.query(TelegramGroup).filter(TelegramGroup.id == task.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 检查规则是否存在（如果指定了规则ID列表）
    if task.rule_ids:
        rules = db.query(FilterRule).filter(FilterRule.id.in_(task.rule_ids)).all()
        if len(rules) != len(task.rule_ids):
            found_rule_ids = [r.id for r in rules]
            missing_rule_ids = [rid for rid in task.rule_ids if rid not in found_rule_ids]
            raise HTTPException(status_code=404, detail=f"规则不存在: {missing_rule_ids}")
    
    # 创建任务
    new_task = DownloadTask(**task.dict())
    new_task.status = "pending"
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    if start_immediately:
        # 立即启动任务
        try:
            new_task.status = "running"
            db.commit()
            
            success = await production_task_manager.execute_task_operation("start_task", new_task.id)
            if not success:
                new_task.status = "failed"
                new_task.error_message = "任务启动失败"
                db.commit()
                raise HTTPException(status_code=500, detail="任务创建成功但启动失败")
            
            logger.info(f"任务 {new_task.id} 创建并启动成功")
            
        except Exception as e:
            new_task.status = "failed"
            new_task.error_message = f"启动任务失败: {str(e)}"
            db.commit()
            logger.error(f"任务 {new_task.id} 启动失败: {e}")
            raise HTTPException(status_code=500, detail=f"任务创建成功但启动失败: {str(e)}")
    
    return new_task

@router.get("/tasks/{task_id}/status")
async def get_task_status(
    task_id: int,
    include_logs: bool = False,
    db: Session = Depends(get_db)
):
    """获取任务详细状态信息"""
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 获取关联的规则和群组信息
    from ..models.task_rule_association import TaskRuleAssociation
    rule_associations = db.query(TaskRuleAssociation).filter(
        TaskRuleAssociation.task_id == task_id,
        TaskRuleAssociation.is_active == True
    ).order_by(TaskRuleAssociation.priority.desc()).first()

    rule = None
    if rule_associations:
        rule = db.query(FilterRule).filter(FilterRule.id == rule_associations.rule_id).first()
    group = db.query(TelegramGroup).filter(TelegramGroup.id == task.group_id).first()
    
    # 计算执行时间
    execution_time = None
    if task.created_at:
        if task.completed_at:
            execution_time = (task.completed_at - task.created_at).total_seconds()
        elif task.status == "running":
            execution_time = (datetime.now() - task.created_at).total_seconds()
    
    # 计算下载速度
    download_speed = None
    if task.downloaded_messages and execution_time and execution_time > 0:
        download_speed = task.downloaded_messages / execution_time  # 文件/秒
    
    # 估算剩余时间
    estimated_remaining = None
    if (task.total_messages and task.downloaded_messages and 
        task.total_messages > task.downloaded_messages and download_speed and download_speed > 0):
        remaining_files = task.total_messages - task.downloaded_messages
        estimated_remaining = remaining_files / download_speed  # 秒
    
    status_info = {
        "task_id": task.id,
        "name": task.name,
        "status": task.status,
        "progress": task.progress,
        "total_messages": task.total_messages,
        "downloaded_messages": task.downloaded_messages,
        "error_message": task.error_message,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "completed_at": task.completed_at,
        "execution_time_seconds": execution_time,
        "download_speed_files_per_second": download_speed,
        "estimated_remaining_seconds": estimated_remaining,
        "rule_info": {
            "id": rule.id,
            "name": rule.name,
            "is_active": rule.is_active
        } if rule else None,
        "group_info": {
            "id": group.id,
            "title": group.title,
            "username": group.username
        } if group else None,
        "jellyfin_config": {
            "use_jellyfin_structure": task.use_jellyfin_structure,
            "include_metadata": task.include_metadata,
            "download_thumbnails": task.download_thumbnails,
            "use_series_structure": task.use_series_structure
        }
    }
    
    # 如果请求包含日志，添加最近的任务日志
    if include_logs:
        try:
            from ..models.log import TaskLog
            recent_logs = db.query(TaskLog).filter(
                TaskLog.task_id == task_id
            ).order_by(TaskLog.created_at.desc()).limit(10).all()
            
            status_info["recent_logs"] = [
                {
                    "level": log.level,
                    "message": log.message,
                    "created_at": log.created_at
                } for log in recent_logs
            ]
        except Exception as e:
            logger.warning(f"获取任务日志失败: {e}")
            status_info["recent_logs"] = []
    
    return status_info

@router.get("/tasks/running")
async def get_running_tasks(
    db: Session = Depends(get_db)
):
    """获取所有正在运行的任务"""
    try:
        running_tasks = db.query(DownloadTask).filter(DownloadTask.status == "running").all()
        
        # 获取任务执行服务中的实际运行状态
        await production_task_manager._ensure_service_ready()
        actual_running_task_ids = task_execution_service.get_running_tasks()
        
        task_info = []
        for task in running_tasks:
            is_actually_running = task.id in actual_running_task_ids
            
            # 如果数据库显示运行但服务中没有，可能是异常状态
            if not is_actually_running:
                logger.warning(f"任务 {task.id} 在数据库中显示运行但服务中不存在")
            
            task_info.append({
                "id": task.id,
                "name": task.name,
                "progress": task.progress,
                "total_messages": task.total_messages,
                "downloaded_messages": task.downloaded_messages,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "is_actually_running": is_actually_running
            })
        
        return {
            "total_running": len(running_tasks),
            "actual_running": len(actual_running_task_ids),
            "tasks": task_info
        }
        
    except Exception as e:
        logger.error(f"获取运行中任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取运行中任务失败: {str(e)}")