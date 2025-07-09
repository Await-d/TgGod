#!/usr/bin/env python3
"""
TgGod 系统初始化脚本
用于单独执行系统初始化任务
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from app.database import SessionLocal, Base, engine
from app.services.user_service import user_service
from app.config import init_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    try:
        logger.info("开始TgGod系统初始化...")
        
        # 1. 创建数据库表
        logger.info("创建数据库表...")
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建完成")
        
        # 2. 初始化设置
        logger.info("初始化系统设置...")
        init_settings()
        logger.info("系统设置初始化完成")
        
        # 3. 初始化用户账户
        logger.info("初始化用户账户...")
        db = SessionLocal()
        try:
            init_result = user_service.initialize_system(db)
            
            if init_result["success"]:
                admin_info = user_service.get_admin_info()
                system_status = init_result["system_status"]
                
                print("\n" + "=" * 60)
                print("🎉 TgGod 系统初始化完成！")
                print("=" * 60)
                print(f"📊 总用户数: {system_status['total_users']}")
                print(f"👑 管理员数: {system_status['admin_users']}")
                print(f"🔑 默认管理员用户名: {admin_info['username']}")
                print(f"🔐 默认管理员密码: {admin_info['password']}")
                print(f"📧 默认管理员邮箱: {admin_info['email']}")
                print("\n⚠️  安全提示:")
                print("   - 首次登录后请立即修改密码")
                print("   - 建议在生产环境中禁用默认账户")
                print("   - 可通过环境变量自定义默认账户信息")
                print("=" * 60)
                
                # 显示API使用示例
                print("\n🚀 API 使用示例:")
                print("1. 获取管理员信息:")
                print("   curl -X GET http://localhost:8000/api/auth/admin-info")
                print("\n2. 登录:")
                print("   curl -X POST http://localhost:8000/api/auth/login \\")
                print("        -H 'Content-Type: application/x-www-form-urlencoded' \\")
                print(f"        -d 'username={admin_info['username']}&password={admin_info['password']}'")
                print("\n3. 启动服务:")
                print("   python -m uvicorn app.main:app --reload")
                print("=" * 60)
                
            else:
                print(f"\n❌ 系统初始化失败: {init_result['message']}")
                if "error" in init_result:
                    print(f"错误详情: {init_result['error']}")
                sys.exit(1)
                
        finally:
            db.close()
            
        logger.info("系统初始化完成")
        
    except Exception as e:
        logger.error(f"系统初始化失败: {e}")
        print(f"\n❌ 系统初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()