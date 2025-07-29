"""
规则同步服务

负责智能管理规则相关的消息同步，包括：
1. 规则初始化时的自动消息同步
2. 后续任务执行的增量同步
3. 规则修改后的重新查找机制

注意：规则现在通过任务-规则关联表与群组关联，不再直接包含group_id字段
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, or_

from ..models.rule import FilterRule, DownloadTask
from ..models.task_rule_association import TaskRuleAssociation
from ..models.telegram import TelegramGroup, TelegramMessage
from ..services.telegram_service import telegram_service
from ..database import get_db

logger = logging.getLogger(__name__)

class RuleSyncService:
    
    def __init__(self):
        self.logger = logger
    
    async def ensure_rule_data_availability(self, rule_id: int, db: Session) -> Dict[str, Any]:
        """
        确保规则有足够的数据可供查询
        
        Args:
            rule_id: 规则ID
            db: 数据库会话
            
        Returns:
            字典包含同步状态和结果信息
        """
        rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
        if not rule:
            raise ValueError(f"规则 {rule_id} 不存在")
        
        # 获取使用此规则的所有任务的群组
        associated_groups = self._get_rule_associated_groups(rule_id, db)
        if not associated_groups:
            self.logger.warning(f"规则 {rule_id} 没有关联的任务或群组，跳过同步")
            return {
                "rule_id": rule_id,
                "sync_performed": False,
                "sync_type": "no_association",
                "message_count": 0,
                "sync_status": "no_association"
            }
        
        # 对每个相关群组检查同步需求
        total_synced = 0
        sync_performed = False
        
        for group in associated_groups:
            sync_result = await self._check_sync_requirements_for_group(rule, group, db)
            
            if sync_result["needs_sync"]:
                # 执行同步
                await self._perform_sync_for_group(rule, group, db, sync_result["sync_type"])
                sync_performed = True
                total_synced += sync_result.get("synced_count", 0)
        
        return {
            "rule_id": rule_id,
            "sync_performed": sync_performed,
            "associated_groups_count": len(associated_groups),
            "total_synced_messages": total_synced,
            "message_count": self._get_available_message_count(rule_id, db),
            "sync_status": getattr(rule, 'sync_status', 'pending')
        }
    
    def _get_rule_associated_groups(self, rule_id: int, db: Session) -> List[TelegramGroup]:
        """
        获取规则关联的所有群组
        通过任务-规则关联表和任务表来查找
        """
        # 查询使用此规则的所有活跃任务
        task_associations = db.query(TaskRuleAssociation).filter(
            TaskRuleAssociation.rule_id == rule_id,
            TaskRuleAssociation.is_active == True
        ).all()
        
        if not task_associations:
            return []
        
        # 获取所有相关任务的群组ID
        task_ids = [assoc.task_id for assoc in task_associations]
        tasks = db.query(DownloadTask).filter(
            DownloadTask.id.in_(task_ids)
        ).all()
        
        # 获取唯一的群组ID
        group_ids = list(set([task.group_id for task in tasks]))
        
        # 查询群组信息
        groups = db.query(TelegramGroup).filter(
            TelegramGroup.id.in_(group_ids)
        ).all()
        
        return groups
    
    async def _check_sync_requirements_for_group(self, rule: FilterRule, group: TelegramGroup, db: Session) -> Dict[str, Any]:
        """
        检查规则在特定群组中的同步需求
        
        Args:
            rule: 规则对象
            group: 群组对象
            db: 数据库会话
            
        Returns:
            包含是否需要同步和同步类型的字典
        """
        # 情况1: 规则从未同步过
        if not hasattr(rule, 'last_sync_time') or rule.last_sync_time is None:
            return {
                "needs_sync": True,
                "sync_type": "initial",
                "reason": f"规则初次使用，需要为群组 {group.title} 进行初始同步"
            }
        
        # 情况2: 规则被修改，需要完全重新同步
        if hasattr(rule, 'needs_full_resync') and rule.needs_full_resync:
            return {
                "needs_sync": True,
                "sync_type": "full_resync",
                "reason": f"规则已修改，需要为群组 {group.title} 完全重新同步"
            }
        
        # 情况3: 检查是否需要增量同步
        # 获取群组中规则时间范围内的最新消息时间
        latest_message_query = db.query(TelegramMessage).filter(
            TelegramMessage.group_id == group.id
        )
        
        # 如果规则有时间限制，应用它
        if hasattr(rule, 'date_from') and rule.date_from:
            latest_message_query = latest_message_query.filter(
                TelegramMessage.date >= rule.date_from
            )
        if hasattr(rule, 'date_to') and rule.date_to:
            latest_message_query = latest_message_query.filter(
                TelegramMessage.date <= rule.date_to
            )
        
        latest_message = latest_message_query.order_by(desc(TelegramMessage.date)).first()
        
        if not latest_message:
            return {
                "needs_sync": True,
                "sync_type": "initial",
                "reason": f"群组 {group.title} 在规则时间范围内没有消息数据"
            }
        
        # 检查群组是否有更新的消息（在规则最后同步时间之后）
        newer_messages_count = db.query(TelegramMessage).filter(
            TelegramMessage.group_id == group.id,
            TelegramMessage.date > getattr(rule, 'last_sync_time', datetime.now() - timedelta(days=90))
        ).count()
        
        if newer_messages_count > 0:
            return {
                "needs_sync": True,
                "sync_type": "incremental",
                "reason": f"群组 {group.title} 中检测到 {newer_messages_count} 条新消息需要同步"
            }
        
        return {
            "needs_sync": False,
            "reason": f"群组 {group.title} 数据已是最新"
        }
    
    async def _perform_sync_for_group(self, rule: FilterRule, group: TelegramGroup, db: Session, sync_type: str):
        """
        为特定群组执行同步操作
        
        Args:
            rule: 规则对象
            group: 群组对象
            db: 数据库会话
            sync_type: 同步类型 ('initial', 'full_resync', 'incremental')
        """
        try:
            # 更新同步状态
            if hasattr(rule, 'sync_status'):
                rule.sync_status = 'syncing'
            db.commit()
            
            # 根据同步类型确定同步参数
            sync_params = self._determine_sync_params(rule, sync_type)
            
            self.logger.info(
                f"开始为规则 {rule.id} 在群组 {group.title} 中执行 {sync_type} 同步，"
                f"参数: {sync_params}"
            )
            
            # 执行消息同步
            sync_result = await self._sync_messages(group, sync_params)
            
            # 更新规则同步状态
            if hasattr(rule, 'last_sync_time'):
                rule.last_sync_time = datetime.now()
            if hasattr(rule, 'last_sync_message_count'):
                # 累加同步计数而不是覆盖
                current_count = getattr(rule, 'last_sync_message_count', 0)
                rule.last_sync_message_count = current_count + sync_result.get('synced_count', 0)
            if hasattr(rule, 'sync_status'):
                rule.sync_status = 'completed'
            if hasattr(rule, 'needs_full_resync'):
                rule.needs_full_resync = False
            
            db.commit()
            
            self.logger.info(
                f"规则 {rule.id} 在群组 {group.title} 中同步完成，"
                f"同步了 {sync_result.get('synced_count', 0)} 条消息"
            )
            
        except Exception as e:
            # 同步失败，更新状态
            if hasattr(rule, 'sync_status'):
                rule.sync_status = 'failed'
            db.commit()
            
            self.logger.error(f"规则 {rule.id} 在群组 {group.title} 中同步失败: {str(e)}")
            raise
    
    def _determine_sync_params(self, rule: FilterRule, sync_type: str) -> Dict[str, Any]:
        """
        根据同步类型确定同步参数
        """
        params = {}
        
        if sync_type == 'initial' or sync_type == 'full_resync':
            # 初始同步或完全重新同步：根据规则的时间范围同步
            if rule.date_from:
                params['start_date'] = rule.date_from
            else:
                # 默认同步最近3个月的数据
                params['start_date'] = datetime.now() - timedelta(days=90)
            
            if rule.date_to:
                params['end_date'] = rule.date_to
            else:
                params['end_date'] = datetime.now()
                
        elif sync_type == 'incremental':
            # 增量同步：从最后同步时间开始
            params['start_date'] = getattr(rule, 'last_sync_time', datetime.now() - timedelta(days=1))
            params['end_date'] = datetime.now()
        
        return params
    
    async def _sync_messages(self, group: TelegramGroup, sync_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行实际的消息同步
        """
        try:
            # 使用Telegram服务进行消息同步
            result = await telegram_service.sync_group_messages(
                group_id=group.id,
                start_date=sync_params.get('start_date'),
                end_date=sync_params.get('end_date'),
                limit=10000  # 设置合理的限制
            )
            
            return {
                'synced_count': result.get('synced_count', 0),
                'total_messages': result.get('total_messages', 0),
                'success': True
            }
            
        except Exception as e:
            self.logger.error(f"消息同步失败: {str(e)}")
            return {
                'synced_count': 0,
                'total_messages': 0,
                'success': False,
                'error': str(e)
            }
    
    def _get_available_message_count(self, rule_id: int, db: Session) -> int:
        """
        获取规则范围内的可用消息数量
        现在通过任务-规则关联来计算所有相关群组的消息总数
        """
        rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
        if not rule:
            return 0
        
        # 获取规则关联的所有群组
        associated_groups = self._get_rule_associated_groups(rule_id, db)
        if not associated_groups:
            return 0
        
        total_count = 0
        for group in associated_groups:
            query = db.query(TelegramMessage).filter(
                TelegramMessage.group_id == group.id
            )
            
            # 应用时间过滤
            if hasattr(rule, 'date_from') and rule.date_from:
                query = query.filter(TelegramMessage.date >= rule.date_from)
            if hasattr(rule, 'date_to') and rule.date_to:
                query = query.filter(TelegramMessage.date <= rule.date_to)
            
            total_count += query.count()
        
        return total_count
    
    async def mark_rule_for_resync(self, rule_id: int, db: Session):
        """
        标记规则需要重新同步（在规则修改后调用）
        """
        rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
        if rule:
            if hasattr(rule, 'needs_full_resync'):
                rule.needs_full_resync = True
            if hasattr(rule, 'sync_status'):
                rule.sync_status = 'pending'
            db.commit()
            
            self.logger.info(f"规则 {rule_id} 已标记为需要重新同步")
    
    async def get_sync_status(self, rule_id: int, db: Session) -> Dict[str, Any]:
        """
        获取规则的同步状态信息
        """
        rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
        if not rule:
            raise ValueError(f"规则 {rule_id} 不存在")
        
        # 获取关联的群组信息
        associated_groups = self._get_rule_associated_groups(rule_id, db)
        
        return {
            "rule_id": rule_id,
            "sync_status": getattr(rule, 'sync_status', 'pending'),
            "last_sync_time": getattr(rule, 'last_sync_time', None),
            "last_sync_message_count": getattr(rule, 'last_sync_message_count', 0),
            "needs_full_resync": getattr(rule, 'needs_full_resync', True),
            "available_message_count": self._get_available_message_count(rule_id, db),
            "associated_groups_count": len(associated_groups),
            "associated_groups": [{"id": g.id, "title": g.title} for g in associated_groups]
        }

# 创建全局服务实例
rule_sync_service = RuleSyncService()