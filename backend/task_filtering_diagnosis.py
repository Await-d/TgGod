#!/usr/bin/env python3
"""
任务执行筛选问题诊断工具

此工具分析任务执行筛选不到数据的原因，并提供解决方案。
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 设置环境变量和路径
if 'DATABASE_URL' not in os.environ:
    os.environ['DATABASE_URL'] = 'sqlite:////app/data/tggod.db'

backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

def main():
    """主诊断函数"""
    print("=" * 70)
    print("🔍 TgGod 任务筛选问题诊断工具")
    print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    try:
        from app.utils.db_optimization import optimized_db_session
        from app.models.rule import DownloadTask, FilterRule
        from app.models.telegram import TelegramGroup, TelegramMessage
        from app.config import settings
        
        with optimized_db_session() as db:
            print("📊 数据库状态检查:")
            
            # 1. 检查任务和规则数据
            tasks = db.query(DownloadTask).all()
            rules = db.query(FilterRule).all()
            groups = db.query(TelegramGroup).all()
            messages = db.query(TelegramMessage).all()
            
            print(f"  ✓ 下载任务数量: {len(tasks)}")
            print(f"  ✓ 过滤规则数量: {len(rules)}")
            print(f"  ✓ Telegram群组数量: {len(groups)}")
            print(f"  ✓ Telegram消息数量: {len(messages)}")
            
            if len(messages) == 0:
                print("\n❌ 根本问题：数据库中没有Telegram消息数据！")
                print("   这就是为什么任务执行筛选不到数据的原因。")
                
                print("\n🛠️  解决方案分析:")
                
                # 2. 检查Telegram API配置
                api_id = settings.telegram_api_id
                api_hash = settings.telegram_api_hash
                
                print(f"\n📡 Telegram API配置检查:")
                print(f"  - API ID: {api_id}")
                print(f"  - API Hash: {'已配置' if api_hash else '未配置'}")
                
                # 检查API ID是否为测试值
                if api_id == 12345678 or api_id == 0:
                    print("  ❌ API ID是测试值或未配置")
                    print("     解决方案: 需要配置真实的Telegram API凭据")
                    print("     1. 访问 https://my.telegram.org/apps")
                    print("     2. 创建应用并获取真实的API ID和API Hash")
                    print("     3. 在系统配置中更新这些值")
                    
                if not api_hash or api_hash in ['your_api_hash_here', 'test_hash']:
                    print("  ❌ API Hash未正确配置")
                    print("     解决方案: 配置从 https://my.telegram.org/apps 获取的真实API Hash")
                
                # 3. 检查群组配置
                print(f"\n👥 群组配置检查:")
                for group in groups:
                    print(f"  - 群组 {group.id}: {group.title}")
                    print(f"    - 用户名: @{group.username}")
                    print(f"    - Telegram ID: {group.telegram_id}")
                    print(f"    - 成员数: {group.member_count}")
                    print(f"    - 状态: {'活跃' if group.is_active else '非活跃'}")
                    
                    # 检查是否为测试群组
                    if group.title == "Test Group" or group.username == "test_group":
                        print("    ❌ 这是一个测试群组，需要配置真实的Telegram群组")
                        print("       解决方案:")
                        print("       1. 加入真实的Telegram群组或频道")
                        print("       2. 在TgGod系统中添加真实群组")
                        print("       3. 删除或更新测试群组配置")
                
                # 4. 检查过滤规则
                print(f"\n🔍 过滤规则检查:")
                for rule in rules:
                    print(f"  - 规则 {rule.id}: {rule.name}")
                    print(f"    - 群组ID: {rule.group_id}")
                    print(f"    - 状态: {'活跃' if rule.is_active else '非活跃'}")
                    print(f"    - 关键词: {rule.keywords}")
                    print(f"    - 媒体类型: {rule.media_types}")
                    
                    # 检查同步状态
                    sync_status = getattr(rule, 'sync_status', 'unknown')
                    last_sync = getattr(rule, 'last_sync_time', None)
                    print(f"    - 同步状态: {sync_status}")
                    print(f"    - 最后同步: {last_sync or '从未同步'}")
                    
                    if sync_status in ['pending', 'failed'] or not last_sync:
                        print(f"    ❌ 规则 {rule.name} 未成功同步消息数据")
                
                print("\n📋 完整解决方案步骤:")
                print("1. 配置真实的Telegram API凭据")
                print("   - 获取真实的API ID和API Hash")
                print("   - 更新系统配置或环境变量")
                
                print("\n2. 配置真实的Telegram群组")
                print("   - 加入要下载的Telegram群组或频道")
                print("   - 在TgGod中添加这些群组")
                print("   - 删除测试群组配置")
                
                print("\n3. 执行消息同步")
                print("   - 确保Telegram客户端能够连接")
                print("   - 运行消息同步功能")
                print("   - 验证消息数据已正确导入")
                
                print("\n4. 验证筛选功能")
                print("   - 创建包含适当过滤条件的规则")
                print("   - 运行任务执行测试")
                print("   - 确认能够筛选到消息")
                
            else:
                print(f"\n✅ 数据库中有 {len(messages)} 条消息")
                
                # 分析具体的筛选问题
                print("\n🔍 筛选逻辑分析:")
                
                # 检查每个任务的筛选结果
                for task in tasks:
                    print(f"\n  📝 任务 {task.id}: {task.name}")
                    rule = db.query(FilterRule).filter(FilterRule.id == task.rule_id).first()
                    group = db.query(TelegramGroup).filter(TelegramGroup.id == task.group_id).first()
                    
                    if not rule:
                        print(f"    ❌ 找不到规则 {task.rule_id}")
                        continue
                        
                    if not group:
                        print(f"    ❌ 找不到群组 {task.group_id}")
                        continue
                    
                    # 模拟筛选过程
                    query = db.query(TelegramMessage).filter(TelegramMessage.group_id == group.id)
                    
                    total_in_group = query.count()
                    print(f"    - 群组 {group.title} 中总消息数: {total_in_group}")
                    
                    # 应用媒体类型筛选
                    media_query = query.filter(TelegramMessage.media_type != 'text')
                    media_query = media_query.filter(TelegramMessage.media_type.isnot(None))
                    media_count = media_query.count()
                    print(f"    - 非文本媒体消息数: {media_count}")
                    
                    # 应用其他筛选条件
                    if rule.keywords:
                        print(f"    - 关键词筛选: {rule.keywords}")
                    if rule.media_types:
                        print(f"    - 媒体类型筛选: {rule.media_types}")
                    if rule.date_from:
                        print(f"    - 开始日期筛选: {rule.date_from}")
                    if rule.date_to:
                        print(f"    - 结束日期筛选: {rule.date_to}")
                    
                    if media_count == 0:
                        print("    ❌ 没有符合媒体类型条件的消息")
                        print("       可能原因:")
                        print("       - 消息都是纯文本消息")
                        print("       - 媒体信息未正确解析")
                        print("       - 需要调整筛选条件")
                
                # 分析消息类型分布
                print(f"\n📊 消息类型分布:")
                media_types = db.query(TelegramMessage.media_type).distinct().all()
                for media_type_row in media_types:
                    media_type = media_type_row[0]
                    count = db.query(TelegramMessage).filter(
                        TelegramMessage.media_type == media_type
                    ).count()
                    print(f"  - {media_type or 'None'}: {count} 条")
                
    except Exception as e:
        print(f"❌ 诊断过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("🎯 诊断完成！请根据上述分析结果采取相应的解决措施。")
    print("=" * 70)

if __name__ == "__main__":
    main()