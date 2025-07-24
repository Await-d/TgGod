"""
数据库结构检查和自动修复工具
用于项目启动时检查数据库表结构是否完整，并自动修复缺失的字段
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..database import SessionLocal, engine
from ..models.telegram import TelegramGroup, TelegramMessage
from ..models.rule import FilterRule, DownloadTask
from ..models.log import TaskLog, SystemLog
from ..models.user import User, UserSettings

logger = logging.getLogger(__name__)

class DatabaseChecker:
    """数据库结构检查器"""
    
    def __init__(self):
        self.inspector = inspect(engine)
        self.db = SessionLocal()
        
        # 定义期望的表结构
        self.expected_tables = {
            'telegram_groups': [
                'id', 'chat_id', 'title', 'username', 'type', 'member_count',
                'description', 'invite_link', 'is_active', 'last_sync_date',
                'created_at', 'updated_at'
            ],
            'telegram_messages': [
                'id', 'message_id', 'group_id', 'sender_id', 'sender_name',
                'sender_username', 'text', 'media_type', 'file_size', 'file_path',
                'is_forwarded', 'forward_from', 'date', 'views', 'reply_to_message_id',
                'created_at', 'updated_at'
            ],
            'filter_rules': [
                'id', 'name', 'group_id', 'keywords', 'exclude_keywords',
                'sender_filter', 'media_types', 'date_from', 'date_to',
                'min_views', 'max_views', 'min_file_size', 'max_file_size',
                'include_forwarded', 'is_active', 'created_at', 'updated_at'
            ],
            'download_tasks': [
                'id', 'name', 'group_id', 'rule_id', 'status', 'progress',
                'total_messages', 'downloaded_messages', 'download_path',
                'created_at', 'updated_at', 'completed_at', 'error_message'
            ],
            'task_logs': [
                'id', 'task_id', 'level', 'message', 'details', 'created_at'
            ],
            'system_logs': [
                'id', 'level', 'message', 'module', 'function', 'details', 'created_at'
            ],
            'users': [
                'id', 'username', 'email', 'hashed_password', 'full_name',
                'avatar_url', 'bio', 'is_active', 'is_superuser', 'is_verified',
                'created_at', 'updated_at', 'last_login'
            ],
            'user_settings': [
                'id', 'user_id', 'setting_key', 'setting_value', 'created_at', 'updated_at'
            ]
        }
        
        # 字段类型映射（用于添加缺失字段）
        self.field_definitions = {
            'filter_rules': {
                'min_file_size': 'INTEGER',
                'max_file_size': 'INTEGER'
            }
        }
    
    def check_database_structure(self) -> Dict[str, Any]:
        """检查数据库结构完整性"""
        logger.info("开始检查数据库结构...")
        
        check_results = {
            'missing_tables': [],
            'missing_columns': {},
            'status': 'healthy',
            'issues_found': 0,
            'fixed_issues': 0,
            'errors': []
        }
        
        try:
            # 检查表是否存在
            existing_tables = self.inspector.get_table_names()
            
            for table_name, expected_columns in self.expected_tables.items():
                if table_name not in existing_tables:
                    check_results['missing_tables'].append(table_name)
                    check_results['issues_found'] += 1
                    logger.warning(f"缺失表: {table_name}")
                else:
                    # 检查表的列
                    missing_columns = self._check_table_columns(table_name, expected_columns)
                    if missing_columns:
                        check_results['missing_columns'][table_name] = missing_columns
                        check_results['issues_found'] += len(missing_columns)
                        logger.warning(f"表 {table_name} 缺失字段: {missing_columns}")
            
            # 设置总体状态
            if check_results['issues_found'] > 0:
                check_results['status'] = 'needs_repair'
                
        except Exception as e:
            logger.error(f"检查数据库结构时出错: {e}")
            check_results['errors'].append(str(e))
            check_results['status'] = 'error'
        
        logger.info(f"数据库结构检查完成，发现 {check_results['issues_found']} 个问题")
        return check_results
    
    def _check_table_columns(self, table_name: str, expected_columns: List[str]) -> List[str]:
        """检查表的列是否完整"""
        try:
            existing_columns = [col['name'] for col in self.inspector.get_columns(table_name)]
            missing_columns = []
            
            for column in expected_columns:
                if column not in existing_columns:
                    missing_columns.append(column)
            
            return missing_columns
            
        except Exception as e:
            logger.error(f"检查表 {table_name} 的列时出错: {e}")
            return []
    
    def repair_database_structure(self, check_results: Dict[str, Any]) -> Dict[str, Any]:
        """修复数据库结构问题"""
        logger.info("开始修复数据库结构...")
        
        repair_results = {
            'repaired_tables': [],
            'repaired_columns': {},
            'failed_repairs': [],
            'success': True
        }
        
        try:
            # 修复缺失的表（通过重新创建模型）
            if check_results['missing_tables']:
                logger.warning("发现缺失表，建议运行 alembic upgrade head 来创建")
                repair_results['success'] = False
                repair_results['failed_repairs'].extend(check_results['missing_tables'])
            
            # 修复缺失的列
            for table_name, missing_columns in check_results['missing_columns'].items():
                repaired_columns = self._repair_table_columns(table_name, missing_columns)
                if repaired_columns:
                    repair_results['repaired_columns'][table_name] = repaired_columns
                    check_results['fixed_issues'] += len(repaired_columns)
                else:
                    repair_results['failed_repairs'].append(f"{table_name}: {missing_columns}")
                    
        except Exception as e:
            logger.error(f"修复数据库结构时出错: {e}")
            repair_results['success'] = False
            repair_results['failed_repairs'].append(str(e))
        
        logger.info(f"数据库结构修复完成，成功修复 {check_results['fixed_issues']} 个问题")
        return repair_results
    
    def _repair_table_columns(self, table_name: str, missing_columns: List[str]) -> List[str]:
        """修复表的缺失列"""
        repaired_columns = []
        
        # 只修复我们定义了修复方法的字段
        if table_name not in self.field_definitions:
            logger.warning(f"表 {table_name} 没有定义字段修复规则，跳过修复")
            return repaired_columns
        
        try:
            for column in missing_columns:
                if column in self.field_definitions[table_name]:
                    column_type = self.field_definitions[table_name][column]
                    if self._add_column(table_name, column, column_type):
                        repaired_columns.append(column)
                        logger.info(f"成功添加字段 {table_name}.{column}")
                    else:
                        logger.error(f"添加字段 {table_name}.{column} 失败")
                else:
                    logger.warning(f"字段 {table_name}.{column} 没有定义修复规则，跳过")
                    
        except Exception as e:
            logger.error(f"修复表 {table_name} 的列时出错: {e}")
        
        return repaired_columns
    
    def _add_column(self, table_name: str, column_name: str, column_type: str) -> bool:
        """向表中添加列"""
        try:
            # 构建 ALTER TABLE 语句
            sql = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            
            with engine.connect() as conn:
                conn.execute(sql)
                conn.commit()
                
            logger.info(f"成功添加列: {table_name}.{column_name} ({column_type})")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"添加列 {table_name}.{column_name} 失败: {e}")
            return False
    
    def run_startup_check(self) -> bool:
        """项目启动时运行的完整检查和修复流程"""
        logger.info("="*50)
        logger.info("开始项目启动数据库检查...")
        
        try:
            # 1. 检查数据库结构
            check_results = self.check_database_structure()
            
            # 2. 如果发现问题，尝试自动修复
            if check_results['status'] == 'needs_repair':
                logger.info(f"发现 {check_results['issues_found']} 个数据库结构问题，开始自动修复...")
                repair_results = self.repair_database_structure(check_results)
                
                if repair_results['success'] and check_results['fixed_issues'] > 0:
                    logger.info(f"✅ 数据库结构修复完成！成功修复 {check_results['fixed_issues']} 个问题")
                elif repair_results['failed_repairs']:
                    logger.warning(f"⚠️  部分问题修复失败: {repair_results['failed_repairs']}")
                    logger.warning("建议手动运行 alembic upgrade head 来完成数据库迁移")
                    return False
            elif check_results['status'] == 'healthy':
                logger.info("✅ 数据库结构检查通过，所有表和字段完整")
            elif check_results['status'] == 'error':
                logger.error(f"❌ 数据库结构检查失败: {check_results['errors']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"项目启动数据库检查失败: {e}")
            return False
        
        finally:
            self.db.close()
            logger.info("数据库检查完成")
            logger.info("="*50)
    
    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库基本信息"""
        try:
            tables = self.inspector.get_table_names()
            table_info = {}
            
            for table in tables:
                columns = self.inspector.get_columns(table)
                indexes = self.inspector.get_indexes(table)
                
                table_info[table] = {
                    'columns': [col['name'] for col in columns],
                    'column_count': len(columns),
                    'indexes': [idx['name'] for idx in indexes],
                    'index_count': len(indexes)
                }
            
            return {
                'database_url': str(engine.url).replace(engine.url.password or '', '***'),
                'table_count': len(tables),
                'tables': table_info
            }
            
        except Exception as e:
            logger.error(f"获取数据库信息失败: {e}")
            return {'error': str(e)}

# 创建全局实例
database_checker = DatabaseChecker()