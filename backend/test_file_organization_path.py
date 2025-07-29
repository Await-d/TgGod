#!/usr/bin/env python3
"""
测试基于关键字的文件路径生成
验证文件整理服务是否正确使用匹配的关键字
"""
import sys
import logging
from datetime import datetime

# 添加应用路径到Python路径
sys.path.append('/root/project/tg/backend')

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_keyword_based_file_organization():
    """测试基于关键字的文件路径生成"""
    try:
        logger.info("🧪 测试基于关键字的文件路径生成...")
        
        from app.services.file_organizer_service import FileOrganizerService
        
        # 创建文件整理服务
        organizer = FileOrganizerService()
        logger.info("✅ 文件整理服务创建成功")
        
        # 模拟消息对象
        class MockMessage:
            def __init__(self, message_id=16956, id=82925, text="", media_filename=""):
                self.message_id = message_id
                self.id = id
                self.text = text
                self.media_filename = media_filename
                self.date = datetime(2025, 7, 29, 9, 49, 50)  # 使用用户日志中的时间
        
        # 模拟任务数据（基于用户日志中的实际数据）
        task_data = {
            'download_path': '/downloads',
            'rule_name': '基于消息 #125468 的规则',
            'matched_keyword': '美女',  # 假设匹配的关键字是"美女"
            'organize_by_date': True,
            'use_jellyfin_structure': False
        }
        
        # 测试用例
        test_cases = [
            {
                'name': '基于关键字"美女"的文件组织',
                'message': MockMessage(text="这是一个关于美女的精彩内容"),
                'task_data': task_data,
                'filename': '16956_82925.mp4',
                'expected_keyword': '美女'
            },
            {
                'name': '使用规则名称的文件组织（无关键字）',
                'message': MockMessage(text="其他内容"),
                'task_data': {**task_data, 'matched_keyword': None},
                'filename': '16956_82925.mp4',
                'expected_rule_name': '基于消息 #125468 的规则'
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"\n测试{i}: {test_case['name']}")
            
            try:
                # 生成组织后的路径
                organized_path = organizer.generate_organized_path(
                    test_case['message'], 
                    test_case['task_data'], 
                    test_case['filename']
                )
                
                logger.info(f"原始文件名: {test_case['filename']}")
                logger.info(f"生成路径: {organized_path}")
                
                # 验证路径格式
                if 'matched_keyword' in test_case['task_data'] and test_case['task_data']['matched_keyword']:
                    expected_keyword = test_case['task_data']['matched_keyword']
                    if expected_keyword in organized_path:
                        # 检查期望的格式：/downloads/关键字/[关键字] - [标题] - [日期]/[关键字] - [标题] - [日期].扩展名
                        if f"/downloads/{expected_keyword}/" in organized_path:
                            logger.info(f"✅ 关键字 '{expected_keyword}' 正确用于目录结构")
                        else:
                            logger.error(f"❌ 关键字 '{expected_keyword}' 未正确用于目录结构")
                        
                        # 检查文件名是否包含关键字
                        if organized_path.endswith(f"{expected_keyword} - "):
                            logger.warning("⚠️ 文件名格式可能不完整")
                        elif expected_keyword in organized_path.split('/')[-1]:
                            logger.info(f"✅ 文件名包含关键字 '{expected_keyword}'")
                        else:
                            logger.error(f"❌ 文件名不包含关键字 '{expected_keyword}'")
                    else:
                        logger.error(f"❌ 关键字 '{expected_keyword}' 完全未出现在路径中")
                else:
                    # 测试规则名称
                    expected_rule_name = test_case.get('expected_rule_name')
                    if expected_rule_name and expected_rule_name in organized_path:
                        logger.info(f"✅ 规则名称 '{expected_rule_name}' 正确用于路径")
                    else:
                        logger.warning("⚠️ 规则名称未在路径中找到")
                
                logger.info("✅ 测试完成")
                
            except Exception as e:
                logger.error(f"❌ 测试失败: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 文件路径生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_actual_task_data():
    """使用实际的任务数据进行测试"""
    try:
        logger.info("🧪 使用实际任务数据测试文件路径生成...")
        
        # 模拟实际的任务执行环境
        from app.services.task_execution_service import TaskExecutionService
        from app.services.file_organizer_service import FileOrganizerService
        
        task_service = TaskExecutionService()
        organizer = FileOrganizerService()
        
        # 模拟消息对象（基于用户日志）
        class MockMessage:
            def __init__(self):
                self.message_id = 16956
                self.id = 82925
                self.text = "美女主播精彩内容"  # 假设的消息内容，包含"美女"关键字
                self.media_filename = "video.mp4"
                self.sender_name = "测试用户"
                self.date = datetime(2025, 7, 29, 9, 49, 50)
                
        # 模拟规则数据
        rule_data = {
            'id': 1,
            'name': '基于消息 #125468 的规则',
            'keywords': ['美女', '精彩', '主播']
        }
        
        message = MockMessage()
        
        # 测试关键字匹配
        matched_keyword = task_service._get_matched_keyword(message, rule_data)
        logger.info(f"检测到的匹配关键字: {matched_keyword}")
        
        # 创建带有匹配关键字的任务数据
        task_data = {
            'download_path': '/downloads',
            'rule_name': rule_data['name'],
            'matched_keyword': matched_keyword,
            'organize_by_date': True,
            'use_jellyfin_structure': False
        }
        
        # 生成最终的文件路径
        filename = f"{message.message_id}_{message.id}.mp4"  # 16956_82925.mp4
        organized_path = organizer.generate_organized_path(message, task_data, filename)
        
        logger.info(f"原始文件名: {filename}")
        logger.info(f"最终组织路径: {organized_path}")
        
        # 检查路径是否符合期望格式
        expected_format = f"/downloads/{matched_keyword}/"
        if expected_format in organized_path:
            logger.info("✅ 文件路径生成符合预期的关键字格式")
            return True
        else:
            logger.error(f"❌ 文件路径不符合预期格式，期望包含: {expected_format}")
            return False
        
    except Exception as e:
        logger.error(f"❌ 实际任务数据测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    logger.info("🧪 文件路径生成测试")
    logger.info("=" * 60)
    
    success_count = 0
    total_tests = 2
    
    # 测试1: 基本文件路径生成
    logger.info("测试1: 基本文件路径生成")
    if test_keyword_based_file_organization():
        success_count += 1
    
    logger.info("\n" + "-" * 30 + "\n")
    
    # 测试2: 实际任务数据测试
    logger.info("测试2: 实际任务数据测试")
    if test_actual_task_data():
        success_count += 1
    
    logger.info("\n" + "=" * 60)
    
    if success_count == total_tests:
        logger.info("🎉 所有测试通过！文件路径生成功能正常")
        logger.info("基于关键字的文件组织功能应该正常工作")
        return True
    else:
        logger.warning(f"⚠️ {total_tests - success_count} 个测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)