#!/usr/bin/env python3
"""
测试规则执行逻辑的脚本
验证规则过滤、任务执行、API功能是否正常
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_connection():
    """测试数据库连接"""
    try:
        from app.database import SessionLocal, engine
        from sqlalchemy import text
        
        db = SessionLocal()
        try:
            # 测试连接
            result = db.execute(text("SELECT 1"))
            logger.info("✅ 数据库连接正常")
            return True
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return False

def test_model_imports():
    """测试模型导入"""
    try:
        from app.models.rule import FilterRule, DownloadTask
        from app.models.telegram import TelegramGroup, TelegramMessage
        logger.info("✅ 模型导入正常")
        return True
    except Exception as e:
        logger.error(f"❌ 模型导入失败: {e}")
        return False

def test_rule_crud():
    """测试规则 CRUD 操作"""
    try:
        from app.database import SessionLocal
        from app.models.rule import FilterRule
        from app.models.telegram import TelegramGroup
        
        db = SessionLocal()
        try:
            # 检查是否有群组数据
            groups_count = db.query(TelegramGroup).count()
            logger.info(f"数据库中群组数量: {groups_count}")
            
            # 检查是否有规则数据
            rules_count = db.query(FilterRule).count()
            logger.info(f"数据库中规则数量: {rules_count}")
            
            if rules_count > 0:
                # 获取第一个规则进行测试
                rule = db.query(FilterRule).first()
                logger.info(f"测试规则: {rule.name} (ID: {rule.id})")
                logger.info(f"规则配置:")
                logger.info(f"  群组ID: {rule.group_id}")
                logger.info(f"  关键词: {rule.keywords}")
                logger.info(f"  排除关键词: {rule.exclude_keywords}")
                logger.info(f"  媒体类型: {rule.media_types}")
                logger.info(f"  发送者过滤: {rule.sender_filter}")
                logger.info(f"  日期范围: {rule.date_from} - {rule.date_to}")
                logger.info(f"  浏览量范围: {rule.min_views} - {rule.max_views}")
                logger.info(f"  文件大小范围: {rule.min_file_size} - {rule.max_file_size}")
                logger.info(f"  包含转发: {rule.include_forwarded}")
                logger.info(f"  是否激活: {rule.is_active}")
                
                logger.info("✅ 规则查询正常")
                return True
            else:
                logger.warning("⚠️ 数据库中没有规则数据")
                return False
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ 规则 CRUD 测试失败: {e}")
        return False

def test_rule_filter_logic():
    """测试规则过滤逻辑"""
    try:
        from app.database import SessionLocal
        from app.models.rule import FilterRule
        from app.models.telegram import TelegramGroup, TelegramMessage
        from app.api.rule import _apply_rule_filter
        import asyncio
        
        async def run_test():
            db = SessionLocal()
            try:
                # 获取第一个规则和群组
                rule = db.query(FilterRule).first()
                if not rule:
                    logger.warning("⚠️ 没有规则可以测试")
                    return False
                
                group = db.query(TelegramGroup).filter(TelegramGroup.id == rule.group_id).first()
                if not group:
                    logger.warning("⚠️ 规则关联的群组不存在")
                    return False
                
                # 检查群组消息数量
                total_messages = db.query(TelegramMessage).filter(TelegramMessage.group_id == group.id).count()
                logger.info(f"群组 {group.title} 总消息数: {total_messages}")
                
                # 应用规则过滤
                matched_messages = await _apply_rule_filter(rule, group, db)
                matched_count = len(matched_messages)
                
                logger.info(f"规则 '{rule.name}' 匹配消息数: {matched_count}")
                
                if matched_count > 0:
                    # 显示前几条匹配的消息样本
                    logger.info("匹配消息样本:")
                    for i, msg in enumerate(matched_messages[:3]):
                        logger.info(f"  消息 {i+1}: ID={msg.message_id}, 类型={msg.media_type}, 大小={msg.file_size}, 发送者={msg.sender_name}")
                
                logger.info("✅ 规则过滤逻辑测试正常")
                return True
                
            finally:
                db.close()
        
        return asyncio.run(run_test())
        
    except Exception as e:
        logger.error(f"❌ 规则过滤逻辑测试失败: {e}")
        return False

def test_task_execution_logic():
    """测试任务执行逻辑"""
    try:
        from app.database import SessionLocal
        from app.models.rule import DownloadTask
        
        db = SessionLocal()
        try:
            # 检查是否有任务数据
            tasks_count = db.query(DownloadTask).count()
            logger.info(f"数据库中任务数量: {tasks_count}")
            
            if tasks_count > 0:
                # 获取第一个任务进行测试
                task = db.query(DownloadTask).first()
                logger.info(f"测试任务: {task.name} (ID: {task.id})")
                logger.info(f"任务配置:")
                logger.info(f"  状态: {task.status}")
                logger.info(f"  进度: {task.progress}%")
                logger.info(f"  总消息数: {task.total_messages}")
                logger.info(f"  已下载: {task.downloaded_messages}")
                logger.info(f"  下载路径: {task.download_path}")
                logger.info(f"  任务日期范围: {task.date_from} - {task.date_to}")
                logger.info(f"  Jellyfin结构: {task.use_jellyfin_structure}")
                logger.info(f"  包含元数据: {task.include_metadata}")
                
                logger.info("✅ 任务查询正常")
                return True
            else:
                logger.warning("⚠️ 数据库中没有任务数据")
                return False
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ 任务执行逻辑测试失败: {e}")
        return False

def test_api_endpoints():
    """测试 API 端点基本功能"""
    try:
        # 测试规则 API 模型
        from app.api.rule import RuleCreate, RuleResponse, RuleTestResponse, RuleValidationResponse
        
        # 测试任务 API 模型  
        from app.api.task import TaskCreate, TaskResponse
        
        logger.info("✅ API 模型导入正常")
        return True
        
    except Exception as e:
        logger.error(f"❌ API 端点测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    logger.info("开始规则执行逻辑全面测试...")
    logger.info("=" * 60)
    
    tests = [
        ("数据库连接", test_database_connection),
        ("模型导入", test_model_imports),
        ("规则 CRUD", test_rule_crud),
        ("规则过滤逻辑", test_rule_filter_logic),
        ("任务执行逻辑", test_task_execution_logic),
        ("API 端点", test_api_endpoints),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 测试: {test_name}")
        logger.info("-" * 40)
        
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} 通过")
            else:
                logger.error(f"❌ {test_name} 失败")
        except Exception as e:
            logger.error(f"❌ {test_name} 异常: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"测试完成! 通过: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 所有测试通过!")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} 个测试失败")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)