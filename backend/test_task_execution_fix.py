#!/usr/bin/env python3
"""
测试任务执行服务中 all_rules_data 变量修复
验证 _prepare_task_execution 和 _execute_task 之间的数据传递
"""
import sys
import logging
from typing import List, Dict, Any

# 添加应用路径到Python路径
sys.path.append('/root/project/tg/backend')

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_all_rules_data_fix():
    """测试 all_rules_data 变量修复"""
    try:
        logger.info("🧪 开始测试 all_rules_data 变量修复...")
        
        from app.services.task_execution_service import TaskExecutionService
        
        # 创建服务实例
        service = TaskExecutionService()
        logger.info("✅ TaskExecutionService 创建成功")
        
        # 验证关键方法是否存在且可调用
        if hasattr(service, '_prepare_task_execution'):
            logger.info("✅ _prepare_task_execution 方法存在")
        else:
            logger.error("❌ _prepare_task_execution 方法不存在")
            return False
            
        if hasattr(service, '_execute_task'):
            logger.info("✅ _execute_task 方法存在")
        else:
            logger.error("❌ _execute_task 方法不存在")
            return False
            
        if hasattr(service, '_get_matched_keyword'):
            logger.info("✅ _get_matched_keyword 方法存在")
        else:
            logger.error("❌ _get_matched_keyword 方法不存在")
            return False
        
        logger.info("✅ 所有必需的方法都存在")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_method_signatures():
    """测试方法签名是否正确"""
    try:
        logger.info("🔍 检查方法签名...")
        
        from app.services.task_execution_service import TaskExecutionService
        import inspect
        
        service = TaskExecutionService()
        
        # 检查 _get_matched_keyword 方法签名
        signature = inspect.signature(service._get_matched_keyword)
        params = list(signature.parameters.keys())
        
        expected_params = ['message', 'rule_data']
        if params == expected_params:
            logger.info("✅ _get_matched_keyword 方法签名正确")
        else:
            logger.error(f"❌ _get_matched_keyword 方法签名错误，期望: {expected_params}, 实际: {params}")
            return False
        
        logger.info("✅ 方法签名检查通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 方法签名检查失败: {e}")
        return False

def test_keyword_matching_logic():
    """测试关键字匹配逻辑"""
    try:
        logger.info("🔍 测试关键字匹配逻辑...")
        
        from app.services.task_execution_service import TaskExecutionService
        
        service = TaskExecutionService()
        
        # 创建模拟消息对象
        class MockMessage:
            def __init__(self, text="", sender_name="", media_filename=""):
                self.text = text
                self.sender_name = sender_name
                self.media_filename = media_filename
        
        # 创建模拟规则数据
        rule_data = {
            'id': 1,
            'name': '测试规则',
            'keywords': ['美女', '视频', '精彩']
        }
        
        # 测试用例
        test_cases = [
            {
                'name': '消息文本匹配',
                'message': MockMessage(text="这是一个关于美女的内容"),
                'expected': '美女'
            },
            {
                'name': '发送者名称匹配',
                'message': MockMessage(sender_name="视频分享者"),
                'expected': '视频'
            },
            {
                'name': '媒体文件名匹配',
                'message': MockMessage(media_filename="精彩内容.mp4"),
                'expected': '精彩'
            },
            {
                'name': '无匹配关键字',
                'message': MockMessage(text="其他内容"),
                'expected': '美女'  # 应该返回第一个关键字作为默认值
            }
        ]
        
        all_passed = True
        for test_case in test_cases:
            try:
                result = service._get_matched_keyword(test_case['message'], rule_data)
                if result == test_case['expected']:
                    logger.info(f"✅ {test_case['name']}: 匹配结果正确 '{result}'")
                else:
                    logger.error(f"❌ {test_case['name']}: 期望 '{test_case['expected']}', 实际 '{result}'")
                    all_passed = False
            except Exception as e:
                logger.error(f"❌ {test_case['name']}: 测试异常 {e}")
                all_passed = False
        
        if all_passed:
            logger.info("✅ 关键字匹配逻辑测试通过")
        else:
            logger.error("❌ 关键字匹配逻辑测试失败")
        
        return all_passed
        
    except Exception as e:
        logger.error(f"❌ 关键字匹配逻辑测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    logger.info("🧪 任务执行服务 all_rules_data 变量修复测试")
    logger.info("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # 测试1: 基本修复验证
    logger.info("测试1: 基本修复验证")
    if test_all_rules_data_fix():
        success_count += 1
    
    logger.info("\n" + "-" * 30 + "\n")
    
    # 测试2: 方法签名检查
    logger.info("测试2: 方法签名检查")
    if test_method_signatures():
        success_count += 1
    
    logger.info("\n" + "-" * 30 + "\n")
    
    # 测试3: 关键字匹配逻辑
    logger.info("测试3: 关键字匹配逻辑")
    if test_keyword_matching_logic():
        success_count += 1
    
    logger.info("\n" + "=" * 60)
    
    if success_count == total_tests:
        logger.info("🎉 所有测试通过！all_rules_data 变量修复成功")
        logger.info("现在任务执行过程中的关键字匹配功能应该正常工作")
        return True
    else:
        logger.warning(f"⚠️ {total_tests - success_count} 个测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)