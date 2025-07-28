#!/usr/bin/env python3
"""
规则筛选逻辑测试工具
模拟任务执行服务中的消息筛选过程
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

def test_multi_rule_filtering(task_id: int):
    """测试多规则筛选逻辑，模拟任务执行服务的筛选过程"""
    db_path = "/app/data/tggod.db"
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取任务信息
        cursor.execute("SELECT * FROM download_tasks WHERE id = ?", (task_id,))
        task_row = cursor.fetchone()
        if not task_row:
            logger.error(f"任务 {task_id} 不存在")
            return False
        
        cursor.execute("PRAGMA table_info(download_tasks)")
        task_columns = [col[1] for col in cursor.fetchall()]
        task_dict = dict(zip(task_columns, task_row))
        
        logger.info(f"🧪 测试任务 {task_id} 的规则筛选逻辑")
        logger.info("=" * 60)
        logger.info(f"任务名称: {task_dict['name']}")
        logger.info(f"目标群组 ID: {task_dict['group_id']}")
        
        # 获取任务关联的所有规则
        cursor.execute("""
            SELECT tra.rule_id, tra.is_active, tra.priority, fr.name
            FROM task_rule_associations tra
            JOIN filter_rules fr ON tra.rule_id = fr.id
            WHERE tra.task_id = ?
            ORDER BY tra.priority DESC
        """, (task_id,))
        rule_associations = cursor.fetchall()
        
        if not rule_associations:
            logger.error("任务没有关联的规则")
            return False
            
        logger.info(f"关联规则数量: {len(rule_associations)}")
        
        # 获取群组基础消息统计
        cursor.execute("SELECT COUNT(*) FROM telegram_messages WHERE group_id = ?", (task_dict['group_id'],))
        total_messages = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM telegram_messages 
            WHERE group_id = ? AND media_type IS NOT NULL AND media_type != 'text'
        """, (task_dict['group_id'],))
        media_messages = cursor.fetchone()[0]
        
        logger.info(f"群组总消息数: {total_messages}")
        logger.info(f"群组有媒体消息数: {media_messages}")
        
        # 模拟任务执行服务的多规则OR筛选逻辑
        logger.info(f"\n🔍 模拟多规则OR筛选逻辑:")
        
        # 收集所有活跃规则的详细配置
        active_rules_data = []
        for rule_id, is_active, priority, rule_name in rule_associations:
            if not is_active:
                logger.info(f"跳过非活跃规则: {rule_name}")
                continue
                
            cursor.execute("SELECT * FROM filter_rules WHERE id = ?", (rule_id,))
            rule_row = cursor.fetchone()
            if rule_row:
                cursor.execute("PRAGMA table_info(filter_rules)")
                rule_columns = [col[1] for col in cursor.fetchall()]
                rule_dict = dict(zip(rule_columns, rule_row))
                active_rules_data.append({
                    'id': rule_id,
                    'name': rule_name,
                    'priority': priority,
                    'config': rule_dict
                })
        
        logger.info(f"活跃规则数量: {len(active_rules_data)}")
        
        # 为每个规则创建子查询
        rule_conditions = []
        rule_results = []
        
        for rule_data in active_rules_data:
            rule_config = rule_data['config']
            logger.info(f"\n📋 处理规则: {rule_data['name']} (ID: {rule_data['id']})")
            
            # 构建基础查询
            query = """
                SELECT id, message_id, text, media_type, media_size, media_filename, 
                       sender_username, view_count, is_forwarded, date
                FROM telegram_messages 
                WHERE group_id = ? AND media_type IS NOT NULL AND media_type != 'text'
            """
            params = [task_dict['group_id']]
            
            # 应用关键词筛选
            if rule_config.get('keywords'):
                try:
                    keywords = json.loads(rule_config['keywords']) if isinstance(rule_config['keywords'], str) else rule_config['keywords']
                    if keywords:
                        keyword_conditions = []
                        for keyword in keywords:
                            keyword_conditions.append("text LIKE ?")
                            params.append(f"%{keyword}%")
                        query += f" AND ({' OR '.join(keyword_conditions)})"
                        logger.info(f"   应用关键词筛选: {keywords}")
                except:
                    pass
            
            # 应用排除关键词筛选
            if rule_config.get('exclude_keywords'):
                try:
                    exclude_keywords = json.loads(rule_config['exclude_keywords']) if isinstance(rule_config['exclude_keywords'], str) else rule_config['exclude_keywords']
                    if exclude_keywords:
                        for exclude_keyword in exclude_keywords:
                            query += " AND (text NOT LIKE ? OR text IS NULL)"
                            params.append(f"%{exclude_keyword}%")
                        logger.info(f"   应用排除关键词筛选: {exclude_keywords}")
                except:
                    pass
            
            # 应用媒体类型筛选
            if rule_config.get('media_types'):
                try:
                    media_types = json.loads(rule_config['media_types']) if isinstance(rule_config['media_types'], str) else rule_config['media_types']
                    if media_types:
                        type_conditions = []
                        for media_type in media_types:
                            type_conditions.append("media_type = ?")
                            params.append(media_type)
                        query += f" AND ({' OR '.join(type_conditions)})"
                        logger.info(f"   应用媒体类型筛选: {media_types}")
                except:
                    pass
            
            # 应用文件大小筛选
            if rule_config.get('min_file_size'):
                query += " AND media_size >= ?"
                params.append(rule_config['min_file_size'])
                logger.info(f"   应用最小文件大小筛选: {rule_config['min_file_size']} 字节")
            
            if rule_config.get('max_file_size'):
                query += " AND media_size <= ?"
                params.append(rule_config['max_file_size'])
                logger.info(f"   应用最大文件大小筛选: {rule_config['max_file_size']} 字节")
            
            # 应用浏览量筛选
            if rule_config.get('min_views'):
                query += " AND (view_count >= ? OR view_count IS NULL)"
                params.append(rule_config['min_views'])
                logger.info(f"   应用最小浏览量筛选: {rule_config['min_views']}")
            
            if rule_config.get('max_views'):
                query += " AND view_count <= ?"
                params.append(rule_config['max_views'])
                logger.info(f"   应用最大浏览量筛选: {rule_config['max_views']}")
            
            # 应用转发筛选
            if not rule_config.get('include_forwarded', True):
                query += " AND is_forwarded = 0"
                logger.info("   应用转发筛选: 排除转发消息")
            
            # 执行单个规则查询
            cursor.execute(query, params)
            rule_results_data = cursor.fetchall()
            rule_results.append({
                'rule_name': rule_data['name'],
                'rule_id': rule_data['id'],
                'count': len(rule_results_data),
                'messages': rule_results_data[:5]  # 只保留前5条消息用于展示
            })
            
            logger.info(f"   ✅ 规则筛选结果: {len(rule_results_data)} 条消息")
        
        # 合并所有规则的结果（模拟OR逻辑）
        logger.info(f"\n🔗 合并所有规则结果 (OR逻辑):")
        all_message_ids = set()
        for result in rule_results:
            for message in result['messages']:
                all_message_ids.add(message[0])  # message[0] is id
        
        # 获取最终筛选结果
        if all_message_ids:
            cursor.execute(f"""
                SELECT COUNT(*) FROM telegram_messages 
                WHERE id IN ({','.join('?' * len(all_message_ids))})
            """, list(all_message_ids))
            final_count = cursor.fetchone()[0]
        else:
            final_count = 0
        
        logger.info(f"最终筛选结果: {final_count} 条消息 (去重后)")
        
        # 显示每个规则的详细结果
        logger.info(f"\n📊 各规则筛选详情:")
        for result in rule_results:
            logger.info(f"规则 '{result['rule_name']}': {result['count']} 条消息")
            if result['messages']:
                logger.info("   示例消息:")
                for msg in result['messages'][:3]:
                    msg_text = (msg[2] or '')[:100] + '...' if msg[2] and len(msg[2]) > 100 else msg[2] or '无文本'
                    logger.info(f"     - ID {msg[1]}: {msg_text} ({msg[3]}, {msg[4]} bytes)")
        
        # 与任务执行结果对比
        logger.info(f"\n📈 与任务执行结果对比:")
        logger.info(f"任务记录的总消息数: {task_dict.get('total_messages', 0)}")
        logger.info(f"任务记录的已下载数: {task_dict.get('downloaded_messages', 0)}")
        logger.info(f"筛选测试结果: {final_count}")
        
        if final_count != task_dict.get('total_messages', 0):
            logger.warning("⚠️ 筛选结果与任务记录不匹配，可能存在问题!")
        else:
            logger.info("✅ 筛选结果与任务记录匹配")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="规则筛选逻辑测试工具")
    parser.add_argument("task_id", type=int, help="要测试的任务ID")
    
    args = parser.parse_args()
    
    logger.info("🚀 启动规则筛选逻辑测试")
    
    success = test_multi_rule_filtering(args.task_id)
    
    if success:
        logger.info("✅ 测试完成")
        sys.exit(0)
    else:
        logger.error("❌ 测试失败")
        sys.exit(1)