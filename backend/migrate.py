#!/usr/bin/env python3
"""
手动运行数据库迁移脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_migration():
    """运行数据库迁移"""
    print("正在运行数据库迁移...")
    
    # 使用alembic命令
    os.system("cd /root/project/TgGod/backend && alembic upgrade head")
    
    print("数据库迁移完成")

if __name__ == "__main__":
    run_migration()