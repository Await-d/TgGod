#!/usr/bin/env python3
"""
任务执行配置诊断工具
检查任务执行过程中配置信息的正确使用
"""
import os
import sys
import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def diagnose_task_execution_config(task_id: int = None):
    """诊断任务执行配置使用情况"""
    db_path = "/app/data/tggod.db"
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取任务列表
        if task_id:
            cursor.execute("SELECT * FROM download_tasks WHERE id = ?", (task_id,))
            tasks = cursor.fetchall()
        else:
            cursor.execute("SELECT * FROM download_tasks ORDER BY created_at DESC LIMIT 5")
            tasks = cursor.fetchall()
        
        if not tasks:
            logger.warning("没有找到任务")
            return False
        
        # 获取字段名
        cursor.execute("PRAGMA table_info(download_tasks)")
        task_columns = [col[1] for col in cursor.fetchall()]
        
        logger.info("🔍 任务执行配置诊断报告")
        logger.info("=" * 60)
        
        for task_row in tasks:
            task_dict = dict(zip(task_columns, task_row))
            task_id = task_dict['id']
            
            logger.info(f"\n📋 任务 ID: {task_id} - {task_dict['name']}")
            logger.info(f"   状态: {task_dict['status']}")
            logger.info(f"   群组 ID: {task_dict['group_id']}")
            logger.info(f"   下载路径: {task_dict['download_path']}")
            
            # 获取群组信息
            cursor.execute("SELECT id, title, username FROM telegram_groups WHERE id = ?", (task_dict['group_id'],))
            group_info = cursor.fetchone()
            if group_info:
                logger.info(f"   📁 目标群组: {group_info[1]} (@{group_info[2] or 'N/A'})")
            else:
                logger.error(f"   ❌ 群组不存在: ID {task_dict['group_id']}")
            
            # 获取关联规则
            cursor.execute("""
                SELECT tra.rule_id, tra.is_active, tra.priority, fr.name
                FROM task_rule_associations tra
                JOIN filter_rules fr ON tra.rule_id = fr.id
                WHERE tra.task_id = ?
                ORDER BY tra.priority DESC
            """, (task_id,))
            rule_associations = cursor.fetchall()
            
            if rule_associations:
                logger.info(f"   🎯 关联规则 ({len(rule_associations)} 个):")
                for rule_id, is_active, priority, rule_name in rule_associations:
                    status = "✅ 活跃" if is_active else "❌ 非活跃"
                    logger.info(f"      - 规则 ID {rule_id}: {rule_name} (优先级: {priority}, {status})")
                    
                    # 获取规则详细配置
                    cursor.execute("SELECT * FROM filter_rules WHERE id = ?", (rule_id,))
                    rule_row = cursor.fetchone()
                    if rule_row:
                        cursor.execute("PRAGMA table_info(filter_rules)")
                        rule_columns = [col[1] for col in cursor.fetchall()]
                        rule_dict = dict(zip(rule_columns, rule_row))
                        
                        # 检查关键配置
                        config_items = []
                        if rule_dict.get('keywords'):
                            keywords = json.loads(rule_dict['keywords']) if isinstance(rule_dict['keywords'], str) else rule_dict['keywords']
                            config_items.append(f"关键词: {keywords}")
                        if rule_dict.get('exclude_keywords'):
                            exclude_keywords = json.loads(rule_dict['exclude_keywords']) if isinstance(rule_dict['exclude_keywords'], str) else rule_dict['exclude_keywords']
                            config_items.append(f"排除关键词: {exclude_keywords}")
                        if rule_dict.get('media_types'):
                            media_types = json.loads(rule_dict['media_types']) if isinstance(rule_dict['media_types'], str) else rule_dict['media_types']
                            config_items.append(f"媒体类型: {media_types}")
                        if rule_dict.get('min_file_size'):
                            config_items.append(f"最小文件大小: {rule_dict['min_file_size']} 字节")
                        if rule_dict.get('max_file_size'):
                            config_items.append(f"最大文件大小: {rule_dict['max_file_size']} 字节")
                        if rule_dict.get('min_views'):
                            config_items.append(f"最小浏览量: {rule_dict['min_views']}")
                        if rule_dict.get('max_views'):
                            config_items.append(f"最大浏览量: {rule_dict['max_views']}")
                        
                        for config in config_items:
                            logger.info(f"        {config}")
            else:
                logger.error(f"   ❌ 没有关联的规则")
            
            # 检查任务配置
            logger.info(f"   ⚙️ 任务配置:")
            config_items = [
                f"Jellyfin结构: {bool(task_dict.get('use_jellyfin_structure'))}",
                f"包含元数据: {bool(task_dict.get('include_metadata'))}",
                f"下载缩略图: {bool(task_dict.get('download_thumbnails'))}",
                f"按日期组织: {bool(task_dict.get('organize_by_date'))}",
                f"最大文件名长度: {task_dict.get('max_filename_length', 150)}"
            ]
            
            for config in config_items:
                logger.info(f"      {config}")
            
            # 检查任务执行历史
            if task_dict['status'] in ['completed', 'failed']:
                logger.info(f"   📊 执行统计:")
                logger.info(f"      总消息数: {task_dict.get('total_messages', 0)}")
                logger.info(f"      已下载: {task_dict.get('downloaded_messages', 0)}")
                logger.info(f"      进度: {task_dict.get('progress', 0)}%")
                if task_dict.get('error_message'):
                    logger.error(f"      错误信息: {task_dict['error_message']}")
                if task_dict.get('completed_at'):
                    logger.info(f"      完成时间: {task_dict['completed_at']}")
        
        # 检查消息筛选情况
        logger.info(f"\n🔬 消息筛选验证")
        logger.info("=" * 60)
        
        for task_row in tasks:
            task_dict = dict(zip(task_columns, task_row))
            task_id = task_dict['id']
            
            # 获取群组消息总数
            cursor.execute("SELECT COUNT(*) FROM telegram_messages WHERE group_id = ?", (task_dict['group_id'],))
            total_messages = cursor.fetchone()[0]
            
            # 获取有媒体的消息数
            cursor.execute("""
                SELECT COUNT(*) FROM telegram_messages 
                WHERE group_id = ? AND media_type IS NOT NULL AND media_type != 'text'
            """, (task_dict['group_id'],))
            media_messages = cursor.fetchone()[0]
            
            logger.info(f"\n📋 任务 {task_id} 消息筛选情况:")
            logger.info(f"   群组总消息数: {total_messages}")
            logger.info(f"   有媒体消息数: {media_messages}")
            
            # 模拟规则筛选
            cursor.execute("""
                SELECT tra.rule_id, fr.name
                FROM task_rule_associations tra
                JOIN filter_rules fr ON tra.rule_id = fr.id
                WHERE tra.task_id = ? AND tra.is_active = 1
                ORDER BY tra.priority DESC
            """, (task_id,))
            active_rules = cursor.fetchall()
            
            if active_rules:
                logger.info(f"   活跃规则筛选结果:")
                for rule_id, rule_name in active_rules:
                    # 简单的规则筛选测试
                    query = """
                        SELECT COUNT(*) FROM telegram_messages 
                        WHERE group_id = ? AND media_type IS NOT NULL AND media_type != 'text'
                    """
                    params = [task_dict['group_id']]
                    
                    # 获取规则配置进行筛选
                    cursor.execute("SELECT * FROM filter_rules WHERE id = ?", (rule_id,))
                    rule_row = cursor.fetchone()
                    if rule_row:
                        cursor.execute("PRAGMA table_info(filter_rules)")
                        rule_columns = [col[1] for col in cursor.fetchall()]
                        rule_dict = dict(zip(rule_columns, rule_row))
                        
                        # 添加文件大小筛选
                        if rule_dict.get('min_file_size'):
                            query += " AND media_size >= ?"
                            params.append(rule_dict['min_file_size'])
                        if rule_dict.get('max_file_size'):
                            query += " AND media_size <= ?"
                            params.append(rule_dict['max_file_size'])
                        
                        # 添加浏览量筛选
                        if rule_dict.get('min_views'):
                            query += " AND (view_count >= ? OR view_count IS NULL)"
                            params.append(rule_dict['min_views'])
                        if rule_dict.get('max_views'):
                            query += " AND view_count <= ?"
                            params.append(rule_dict['max_views'])
                    
                    cursor.execute(query, params)
                    filtered_count = cursor.fetchone()[0]
                    logger.info(f"      规则 '{rule_name}': {filtered_count} 条消息符合条件")
        
        conn.close()
        logger.info(f"\n✅ 诊断完成")
        return True
        
    except Exception as e:
        logger.error(f"诊断失败: {e}")
        return False

def test_rule_filtering_logic():
    """测试规则筛选逻辑"""
    logger.info("\n🧪 规则筛选逻辑测试")
    logger.info("=" * 60)
    
    # 这里可以添加更多的测试逻辑
    # 比如创建测试数据，验证筛选结果等
    
    logger.info("测试功能开发中...")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="任务执行配置诊断工具")
    parser.add_argument("--task-id", type=int, help="指定要诊断的任务ID")
    parser.add_argument("--test-filtering", action="store_true", help="测试规则筛选逻辑")
    
    args = parser.parse_args()
    
    logger.info("🚀 启动任务执行配置诊断工具")
    
    success = True
    
    if args.test_filtering:
        test_rule_filtering_logic()
    else:
        success = diagnose_task_execution_config(args.task_id)
    
    if success:
        logger.info("✅ 诊断工具执行成功")
        sys.exit(0)
    else:
        logger.error("❌ 诊断工具执行失败")
        sys.exit(1)