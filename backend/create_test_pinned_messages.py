#!/usr/bin/env python3
"""
创建测试置顶消息数据
用于测试置顶消息排序和切换功能
"""

import sqlite3
import os
from datetime import datetime, timedelta

def create_test_pinned_messages():
    """创建测试置顶消息数据"""
    
    db_path = '/app/data/tggod.db'
    if not os.path.exists(db_path):
        db_path = './data/tggod.db'
        if not os.path.exists(db_path):
            print('❌ 数据库文件不存在')
            return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 首先检查是否有群组
        cursor.execute("SELECT id FROM telegram_groups LIMIT 1")
        group = cursor.fetchone()
        
        if not group:
            print('❌ 没有找到群组，请先添加群组')
            return False
        
        group_id = group[0]
        print(f'✅ 找到群组 ID: {group_id}')
        
        # 删除现有的测试置顶消息
        cursor.execute("DELETE FROM telegram_messages WHERE text LIKE '测试置顶消息%'")
        
        # 创建多条测试置顶消息，时间从旧到新
        base_time = datetime.now() - timedelta(days=7)
        test_messages = [
            {
                'text': '测试置顶消息1 - 最早的置顶消息',
                'date': base_time,
            },
            {
                'text': '测试置顶消息2 - 中间的置顶消息',
                'date': base_time + timedelta(days=2),
            },
            {
                'text': '测试置顶消息3 - 最新的置顶消息',
                'date': base_time + timedelta(days=4),
            }
        ]
        
        for i, msg in enumerate(test_messages, 1):
            message_id = 9000 + i  # 使用特殊的消息ID避免冲突
            
            cursor.execute("""
                INSERT INTO telegram_messages (
                    group_id, message_id, text, sender_id, sender_username, 
                    sender_name, date, view_count, is_forwarded, 
                    is_own_message, is_pinned, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                group_id,
                message_id,
                msg['text'],
                12345,  # 测试发送者ID
                'test_user',
                '测试用户',
                msg['date'].isoformat(),
                0,  # view_count
                False,  # is_forwarded
                False,  # is_own_message
                True,   # is_pinned - 设置为置顶
                datetime.now().isoformat()
            ))
            
            print(f'✅ 创建测试置顶消息 {i}: {msg["text"]} (日期: {msg["date"]})')
        
        conn.commit()
        
        # 验证创建的消息
        cursor.execute("""
            SELECT id, message_id, text, date 
            FROM telegram_messages 
            WHERE is_pinned = 1 AND text LIKE '测试置顶消息%'
            ORDER BY date DESC
        """)
        
        messages = cursor.fetchall()
        print(f'\n📋 创建的置顶消息 (按日期降序):')
        for msg in messages:
            print(f'  ID: {msg[0]}, MessageID: {msg[1]}, 日期: {msg[3][:19]}, 内容: {msg[2]}')
        
        print(f'\n✅ 成功创建 {len(messages)} 条测试置顶消息')
        print('\n🔄 请刷新前端页面查看置顶消息切换功能')
        print('💡 应该看到最新的消息("测试置顶消息3")显示在第一位')
        
        return True
        
    except Exception as e:
        print(f'❌ 创建测试数据失败: {e}')
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    print("=" * 60)
    print("创建测试置顶消息数据")
    print("=" * 60)
    
    success = create_test_pinned_messages()
    
    if success:
        print("\n🎉 测试数据创建成功!")
        print("\n📝 测试步骤:")
        print("1. 刷新前端页面")
        print("2. 选择有置顶消息的群组")
        print("3. 检查置顶消息是否按最新到最旧排序")
        print("4. 测试左右切换按钮")
        print("5. 测试页面指示器点击")
        print("6. 测试键盘快捷键 (Ctrl+←/→)")
    else:
        print("\n❌ 测试数据创建失败")

if __name__ == "__main__":
    main()