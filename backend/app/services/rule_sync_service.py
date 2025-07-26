"""
规则同步服务

负责智能管理规则相关的消息同步，包括：
1. 规则初始化时的自动消息同步
2. 后续任务执行的增量同步
3. 规则修改后的重新查找机制
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, or_

from ..models.rule import FilterRule
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
        
        # 检查是否需要同步
        sync_result = await self._check_sync_requirements(rule, db)
        
        if sync_result["needs_sync"]:
            # 执行同步
            await self._perform_sync(rule, db, sync_result["sync_type"])
            
        return {
            "rule_id": rule_id,
            "sync_performed": sync_result["needs_sync"],
            "sync_type": sync_result.get("sync_type"),
            "message_count": self._get_available_message_count(rule, db),
            "sync_status": rule.sync_status
        }
    
    async def _check_sync_requirements(self, rule: FilterRule, db: Session) -> Dict[str, Any]:
        """
        检查规则的同步需求
        
        Returns:
            包含是否需要同步和同步类型的字典
        """
        group = db.query(TelegramGroup).filter(TelegramGroup.id == rule.group_id).first()
        if not group:
            return {"needs_sync": False, "reason": "群组不存在"}
        
        # 情况1: 规则从未同步过
        if rule.last_sync_time is None:
            return {
                "needs_sync": True,
                "sync_type": "initial",
                "reason": "规则初次使用，需要初始同步"
            }
        
        # 情况2: 规则被修改，需要完全重新同步
        if rule.needs_full_resync:
            return {
                "needs_sync": True,
                "sync_type": "full_resync",
                "reason": "规则已修改，需要完全重新同步"
            }
        
        # 情况3: 检查是否需要增量同步
        # 获取规则时间范围内的最新消息时间
        latest_message_query = db.query(TelegramMessage).filter(
            TelegramMessage.group_id == rule.group_id
        )
        
        # 如果规则有时间限制，应用它
        if rule.date_from:
            latest_message_query = latest_message_query.filter(
                TelegramMessage.date >= rule.date_from
            )
        if rule.date_to:
            latest_message_query = latest_message_query.filter(
                TelegramMessage.date <= rule.date_to
            )
        
        latest_message = latest_message_query.order_by(desc(TelegramMessage.date)).first()
        
        if not latest_message:
            return {
                "needs_sync": True,
                "sync_type": "initial",
                "reason": "规则时间范围内没有消息数据"
            }
        
        # 检查群组是否有更新的消息（在规则最后同步时间之后）
        newer_messages_count = db.query(TelegramMessage).filter(
            TelegramMessage.group_id == rule.group_id,
            TelegramMessage.date > rule.last_sync_time
        ).count()
        
        if newer_messages_count > 0:
            return {
                "needs_sync": True,
                "sync_type": "incremental",
                "reason": f"检测到 {newer_messages_count} 条新消息需要同步"
            }
        
        return {
            "needs_sync": False,
            "reason": "数据已是最新"
        }
    
    async def _perform_sync(self, rule: FilterRule, db: Session, sync_type: str):
        """
        执行同步操作
        
        Args:
            rule: 规则对象
            db: 数据库会话
            sync_type: 同步类型 ('initial', 'full_resync', 'incremental')
        """
        try:
            # 更新同步状态
            rule.sync_status = 'syncing'
            db.commit()
            
            group = db.query(TelegramGroup).filter(TelegramGroup.id == rule.group_id).first()
            if not group:
                raise ValueError(f"群组 {rule.group_id} 不存在")
            
            # 根据同步类型确定同步参数
            sync_params = self._determine_sync_params(rule, sync_type)
            
            self.logger.info(
                f"开始为规则 {rule.id} 执行 {sync_type} 同步，"
                f"群组: {group.title}, 参数: {sync_params}"
            )
            
            # 执行消息同步
            sync_result = await self._sync_messages(group, sync_params)
            
            # 更新规则同步状态
            rule.last_sync_time = datetime.now()
            rule.last_sync_message_count = sync_result.get('synced_count', 0)
            rule.sync_status = 'completed'
            rule.needs_full_resync = False
            
            db.commit()
            
            self.logger.info(
                f"规则 {rule.id} 同步完成，同步了 {sync_result.get('synced_count', 0)} 条消息"
            )
            
        except Exception as e:
            # 同步失败，更新状态
            rule.sync_status = 'failed'
            db.commit()
            
            self.logger.error(f"规则 {rule.id} 同步失败: {str(e)}")
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
            params['start_date'] = rule.last_sync_time
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
    
    def _get_available_message_count(self, rule: FilterRule, db: Session) -> int:
        """
        获取规则范围内的可用消息数量
        """
        query = db.query(TelegramMessage).filter(
            TelegramMessage.group_id == rule.group_id
        )
        
        # 应用时间过滤
        if rule.date_from:
            query = query.filter(TelegramMessage.date >= rule.date_from)
        if rule.date_to:
            query = query.filter(TelegramMessage.date <= rule.date_to)
        
        return query.count()
    
    async def mark_rule_for_resync(self, rule_id: int, db: Session):
        """
        标记规则需要重新同步（在规则修改后调用）
        """
        rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
        if rule:
            rule.needs_full_resync = True
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
        
        return {
            "rule_id": rule_id,
            "sync_status": rule.sync_status,
            "last_sync_time": rule.last_sync_time,
            "last_sync_message_count": rule.last_sync_message_count,
            "needs_full_resync": rule.needs_full_resync,
            "available_message_count": self._get_available_message_count(rule, db)
        }

# 创建全局服务实例
rule_sync_service = RuleSyncService()