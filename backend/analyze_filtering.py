#!/usr/bin/env python3
"""
分析任务筛选逻辑和关键词匹配情况
"""

import sys
import os
from pathlib import Path

# 设置环境变量和路径
if 'DATABASE_URL' not in os.environ:
    os.environ['DATABASE_URL'] = 'sqlite:////app/data/tggod.db'

backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

def main():
    try:
        from app.utils.db_optimization import optimized_db_session
        from app.models.rule import DownloadTask, FilterRule
        from app.models.telegram import TelegramGroup, TelegramMessage
        from sqlalchemy import and_, or_

        print('📊 详细筛选分析:')
        with optimized_db_session() as db:
            # 获取任务和规则
            task = db.query(DownloadTask).first()
            rule = db.query(FilterRule).filter(FilterRule.id == task.rule_id).first()
            group = db.query(TelegramGroup).filter(TelegramGroup.id == task.group_id).first()
            
            print(f'任务: {task.name}')
            print(f'规则: {rule.name}')
            print(f'群组: {group.title}')
            print(f'关键词: {rule.keywords}')
            print(f'媒体类型: {rule.media_types}')
            print()
            
            # 模拟完整的筛选过程
            query = db.query(TelegramMessage).filter(TelegramMessage.group_id == group.id)
            print(f'步骤1 - 群组筛选: {query.count()} 条消息')
            
            # 应用关键词筛选
            if rule.keywords:
                keyword_conditions = []
                for keyword in rule.keywords:
                    text_condition = and_(
                        TelegramMessage.text.isnot(None),
                        TelegramMessage.text.contains(keyword)
                    )
                    sender_condition = and_(
                        TelegramMessage.sender_name.isnot(None),
                        TelegramMessage.sender_name.contains(keyword)
                    )
                    filename_condition = and_(
                        TelegramMessage.media_filename.isnot(None),
                        TelegramMessage.media_filename.contains(keyword)
                    )
                    keyword_conditions.append(or_(text_condition, sender_condition, filename_condition))
                if keyword_conditions:
                    query = query.filter(or_(*keyword_conditions))
            
            print(f'步骤2 - 关键词筛选 ({rule.keywords}): {query.count()} 条消息')
            
            # 应用媒体类型筛选  
            if rule.media_types:
                query = query.filter(TelegramMessage.media_type.in_(rule.media_types))
            
            print(f'步骤3 - 媒体类型筛选 ({rule.media_types}): {query.count()} 条消息')
            
            # 应用非文本媒体筛选 (任务执行服务中的筛选)
            query = query.filter(TelegramMessage.media_type != 'text')
            query = query.filter(TelegramMessage.media_type.isnot(None))
            
            print(f'步骤4 - 非文本媒体筛选: {query.count()} 条消息')
            
            print()
            print('🔍 关键词匹配分析:')
            
            # 检查包含关键词 '柚子猫' 的消息
            keyword = '柚子猫'
            
            # 在文本中查找
            text_matches = db.query(TelegramMessage).filter(
                TelegramMessage.group_id == group.id,
                TelegramMessage.text.isnot(None),
                TelegramMessage.text.contains(keyword)
            ).count()
            print(f'  - 文本中包含 "{keyword}": {text_matches} 条')
            
            # 在发送者名称中查找
            sender_matches = db.query(TelegramMessage).filter(
                TelegramMessage.group_id == group.id,
                TelegramMessage.sender_name.isnot(None),
                TelegramMessage.sender_name.contains(keyword)
            ).count()
            print(f'  - 发送者名称中包含 "{keyword}": {sender_matches} 条')
            
            # 在文件名中查找
            filename_matches = db.query(TelegramMessage).filter(
                TelegramMessage.group_id == group.id,
                TelegramMessage.media_filename.isnot(None),
                TelegramMessage.media_filename.contains(keyword)
            ).count()
            print(f'  - 文件名中包含 "{keyword}": {filename_matches} 条')
            
            print()
            print('📋 样本消息分析:')
            
            # 显示一些包含关键词的消息示例
            sample_messages = db.query(TelegramMessage).filter(
                TelegramMessage.group_id == group.id,
                or_(
                    and_(TelegramMessage.text.isnot(None), TelegramMessage.text.contains(keyword)),
                    and_(TelegramMessage.sender_name.isnot(None), TelegramMessage.sender_name.contains(keyword)),
                    and_(TelegramMessage.media_filename.isnot(None), TelegramMessage.media_filename.contains(keyword))
                )
            ).limit(5).all()
            
            for msg in sample_messages:
                print(f'  消息 {msg.message_id}:')
                print(f'    - 文本: {(msg.text or "")[:50]}...')
                print(f'    - 发送者: {msg.sender_name or "无"}')
                print(f'    - 文件名: {msg.media_filename or "无"}')
                print(f'    - 媒体类型: {msg.media_type or "无"}')
                print()
                
            # 检查是否有video类型的消息包含关键词
            print('🎥 视频消息中的关键词匹配:')
            video_with_keyword = db.query(TelegramMessage).filter(
                TelegramMessage.group_id == group.id,
                TelegramMessage.media_type == 'video',
                or_(
                    and_(TelegramMessage.text.isnot(None), TelegramMessage.text.contains(keyword)),
                    and_(TelegramMessage.sender_name.isnot(None), TelegramMessage.sender_name.contains(keyword)),
                    and_(TelegramMessage.media_filename.isnot(None), TelegramMessage.media_filename.contains(keyword))
                )
            ).count()
            print(f'  - 包含 "{keyword}" 的视频消息: {video_with_keyword} 条')
            
            # 如果没有匹配，尝试查找相似的关键词
            if video_with_keyword == 0:
                print('\n🔍 尝试查找相似关键词:')
                similar_keywords = ['柚子', '猫', 'yzm', 'yuzi']
                
                for sim_keyword in similar_keywords:
                    sim_count = db.query(TelegramMessage).filter(
                        TelegramMessage.group_id == group.id,
                        TelegramMessage.media_type == 'video',
                        or_(
                            and_(TelegramMessage.text.isnot(None), TelegramMessage.text.contains(sim_keyword)),
                            and_(TelegramMessage.sender_name.isnot(None), TelegramMessage.sender_name.contains(sim_keyword)),
                            and_(TelegramMessage.media_filename.isnot(None), TelegramMessage.media_filename.contains(sim_keyword))
                        )
                    ).count()
                    print(f'  - 包含 "{sim_keyword}" 的视频消息: {sim_count} 条')

    except Exception as e:
        print(f"❌ 分析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()