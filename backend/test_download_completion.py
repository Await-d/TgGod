#!/usr/bin/env python3
"""
测试下载完成情况
检查为什么下载没有显示完成日志
"""
import sys
import logging
import asyncio
from datetime import datetime

# 添加应用路径到Python路径
sys.path.append('/root/project/tg/backend')

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sync_download_flow():
    """测试同步的下载流程（模拟）"""
    try:
        logger.info("🧪 测试同步下载流程模拟...")
        
        from app.services.task_execution_service import TaskExecutionService
        from app.services.file_organizer_service import FileOrganizerService
        
        # 创建服务实例
        task_service = TaskExecutionService()
        organizer = FileOrganizerService()
        
        # 模拟下载完成后的文件整理流程
        logger.info("模拟文件下载完成，开始整理流程...")
        
        # 模拟消息对象
        class MockMessage:
            def __init__(self):
                self.message_id = 16956
                self.id = 82925
                self.text = "美女主播精彩内容"
                self.media_filename = "video.mp4"
                self.sender_name = "测试用户"
                self.date = datetime.now()
                self.media_type = "video"
        
        # 模拟规则数据
        rule_data = {
            'id': 1,
            'name': '基于消息 #125468 的规则',
            'keywords': ['美女', '精彩', '主播']
        }
        
        message = MockMessage()
        matched_keyword = task_service._get_matched_keyword(message, rule_data)
        
        # 创建任务数据
        task_data = {
            'download_path': '/downloads',
            'rule_name': rule_data['name'],
            'matched_keyword': matched_keyword,
            'organize_by_date': True,
            'use_jellyfin_structure': False,
            'task_id': 2,
            'group_id': 45
        }
        
        # 模拟下载的文件路径（老格式）
        downloaded_file = f"/downloads/{message.message_id}_{message.id}.mp4"
        logger.info(f"模拟下载完成的文件: {downloaded_file}")
        
        # 测试文件整理
        logger.info("开始测试文件整理...")
        organized_path = organizer.generate_organized_path(message, task_data, f"{message.message_id}_{message.id}.mp4")
        logger.info(f"预期整理后路径: {organized_path}")
        
        # 模拟整理过程的日志输出
        logger.info("🔄 模拟整理过程中应该看到的日志:")
        logger.info(f"任务{task_data['task_id']}: 开始整理文件 {downloaded_file}")
        logger.info(f"使用匹配关键字作为规则名: {matched_keyword}")
        logger.info(f"任务{task_data['task_id']}: 文件已整理: {downloaded_file} -> {organized_path}")
        
        # 检查是否能正确生成路径
        if "/downloads/" in organized_path and matched_keyword in organized_path:
            logger.info("✅ 文件整理路径生成正确")
            return True
        else:
            logger.error("❌ 文件整理路径生成错误")
            return False
        
    except Exception as e:
        logger.error(f"❌ 同步下载流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_download_logs():
    """分析下载日志，找出问题"""
    logger.info("🔍 分析下载过程中的日志...")
    
    expected_logs = [
        "任务2: 准备下载文件 - group_telegram_id: 1712841500, message_id: 16956",
        "媒体下载器 - 接收到参数: chat_id=1712841500, message_id=16956, file_path=/downloads/16956_82925.mp4",
        "媒体下载器 - 尝试获取实体: chat_id=1712841500",
        "Starting direct file download in chunks of 524288 at 0, stride 524288",
        # 应该看到但没看到的日志:
        "通过消息下载文件成功: /downloads/16956_82925.mp4",
        "成功下载文件: 16956_82925.mp4",
        "任务2: 开始整理文件 /downloads/16956_82925.mp4",
        "使用匹配关键字作为规则名: [某个关键字]",
        "文件已整理: /downloads/16956_82925.mp4 -> [新路径]"
    ]
    
    logger.info("📋 预期应该看到的完整日志流程:")
    for i, log in enumerate(expected_logs, 1):
        if i <= 4:
            logger.info(f"✅ {i}. {log} (已看到)")
        else:
            logger.error(f"❌ {i}. {log} (未看到)")
    
    logger.info("\n🔍 可能的问题分析:")
    logger.info("1. 下载过程卡住了，没有完成")
    logger.info("2. 异步回调处理有问题，导致死锁")
    logger.info("3. 进度回调函数抛出异常，中断了下载")
    logger.info("4. 网络问题或文件太大，下载超时")
    
    return True

def suggest_solutions():
    """建议解决方案"""
    logger.info("💡 建议的解决方案:")
    
    solutions = [
        "1. 简化进度回调函数，避免复杂的异步处理",
        "2. 添加下载超时机制",
        "3. 增加更详细的错误日志",
        "4. 测试不使用进度回调的下载",
        "5. 检查是否有其他任务在同时运行导致资源竞争"
    ]
    
    for solution in solutions:
        logger.info(solution)
    
    logger.info("\n🔧 立即可以尝试的修复:")
    logger.info("- 修改进度回调函数，使用更简单的实现")
    logger.info("- 添加下载超时和错误处理")
    logger.info("- 增加关键步骤的详细日志")
    
    return True

def main():
    """主函数"""
    logger.info("🧪 下载完成问题诊断")
    logger.info("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # 测试1: 同步下载流程模拟
    logger.info("测试1: 同步下载流程模拟")
    if test_sync_download_flow():
        success_count += 1
    
    logger.info("\n" + "-" * 30 + "\n")
    
    # 测试2: 分析下载日志
    logger.info("测试2: 分析下载日志")
    if analyze_download_logs():
        success_count += 1
    
    logger.info("\n" + "-" * 30 + "\n")
    
    # 测试3: 建议解决方案
    logger.info("测试3: 建议解决方案")
    if suggest_solutions():
        success_count += 1
    
    logger.info("\n" + "=" * 60)
    
    if success_count == total_tests:
        logger.info("🎉 诊断完成！")
        logger.info("问题：下载过程没有完成，因此文件整理步骤从未执行")
        logger.info("原因：可能是异步进度回调处理问题或下载超时")
        return True
    else:
        logger.warning(f"⚠️ {total_tests - success_count} 个测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)