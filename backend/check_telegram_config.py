#!/usr/bin/env python3
"""
检查和修复Telegram API配置
"""

import sqlite3
import os
import sys

def check_telegram_config():
    """检查Telegram API配置"""
    
    db_path = '/app/data/tggod.db'
    if not os.path.exists(db_path):
        db_path = './data/tggod.db'
        if not os.path.exists(db_path):
            print('❌ 数据库文件不存在')
            return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 查询Telegram API配置
        cursor.execute("SELECT key, value FROM system_config WHERE key IN ('telegram_api_id', 'telegram_api_hash')")
        configs = cursor.fetchall()
        
        api_id = None
        api_hash = None
        
        for key, value in configs:
            if key == 'telegram_api_id':
                api_id = value
            elif key == 'telegram_api_hash':
                api_hash = value
        
        print("当前Telegram API配置:")
        print(f"  API ID: {api_id if api_id else '未设置'}")
        print(f"  API Hash: {'已设置' if api_hash else '未设置'}")
        
        if not api_id or not api_hash:
            print("\n❌ Telegram API配置不完整")
            print("\n请按以下步骤配置:")
            print("1. 访问 https://my.telegram.org")
            print("2. 登录并创建一个新的应用")
            print("3. 获取 API ID 和 API Hash")
            print("4. 运行以下命令更新配置:")
            print(f"   sqlite3 {db_path}")
            print("   UPDATE system_config SET value='YOUR_API_ID' WHERE key='telegram_api_id';")
            print("   UPDATE system_config SET value='YOUR_API_HASH' WHERE key='telegram_api_hash';")
            print("   .exit")
            return False
        
        print("\n✅ Telegram API配置完整")
        return True
        
    except Exception as e:
        print(f"❌ 检查配置失败: {e}")
        return False
    finally:
        conn.close()

def check_session_file():
    """检查session文件"""
    session_path = "./telegram_sessions/tggod_session.session"
    
    if os.path.exists(session_path):
        size = os.path.getsize(session_path)
        print(f"\n✅ Session文件存在: {session_path} (大小: {size} bytes)")
        
        if size > 0:
            print("✅ Session文件有内容，应该包含认证信息")
            return True
        else:
            print("⚠️  Session文件为空，可能需要重新认证")
            return False
    else:
        print(f"\n❌ Session文件不存在: {session_path}")
        print("请先运行主程序进行Telegram认证")
        return False

def main():
    print("=" * 60)
    print("TgGod Telegram配置检查")
    print("=" * 60)
    
    # 检查API配置
    print("1. 检查Telegram API配置...")
    api_ok = check_telegram_config()
    
    # 检查Session文件
    print("\n2. 检查Session文件...")
    session_ok = check_session_file()
    
    print("\n" + "=" * 60)
    if api_ok and session_ok:
        print("✅ 配置检查通过，媒体下载功能应该可以正常工作")
    else:
        print("❌ 配置检查失败，请按照上述说明修复配置")
        print("\n📖 更多帮助:")
        print("- Telegram API申请: https://my.telegram.org")
        print("- 如果已有API配置，请检查数据库中的system_config表")
        print("- 如果需要重新认证，删除session文件并重启程序")
    print("=" * 60)

if __name__ == "__main__":
    main()