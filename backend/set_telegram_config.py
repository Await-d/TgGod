#!/usr/bin/env python3
"""
设置 Telegram API 配置的脚本
"""

import sys
import os
import json
from app.database import SessionLocal
from app.services.config_service import config_service

def main():
    print("=== TgGod Telegram API 配置设置 ===")
    print()
    
    # 获取用户输入
    print("请输入您的 Telegram API 配置信息：")
    print("可以从 https://my.telegram.org/apps 获取")
    print()
    
    api_id = input("API ID: ").strip()
    api_hash = input("API Hash: ").strip()
    
    # 验证输入
    if not api_id or not api_hash:
        print("错误：API ID 和 API Hash 不能为空")
        sys.exit(1)
    
    try:
        api_id = int(api_id)
    except ValueError:
        print("错误：API ID 必须是数字")
        sys.exit(1)
    
    if len(api_hash) < 20:
        print("错误：API Hash 格式不正确")
        sys.exit(1)
    
    # 保存配置到数据库
    print("\n正在保存配置...")
    
    try:
        db = SessionLocal()
        
        # 设置配置
        config_service.set_config("telegram_api_id", str(api_id), db)
        config_service.set_config("telegram_api_hash", api_hash, db)
        
        # 提交更改
        db.commit()
        
        print("✅ 配置保存成功！")
        print(f"   API ID: {api_id}")
        print(f"   API Hash: {api_hash[:10]}...")
        
        # 清除缓存
        try:
            from app.config import settings
            settings.clear_cache()
            config_service.clear_cache()
            print("✅ 缓存已清除")
        except Exception as e:
            print(f"⚠️  清除缓存失败: {e}")
        
        print("\n现在您可以尝试同步群组了！")
        
    except Exception as e:
        print(f"❌ 保存配置失败: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()