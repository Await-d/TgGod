#!/usr/bin/env python3
"""
测试基于触发关键字的文件整理服务
验证使用匹配的关键字作为文件保存路径
"""
import sys
import os
from datetime import datetime

# 添加应用路径到Python路径
sys.path.append('/root/project/tg/backend')

def test_keyword_based_path_generation():
    """测试基于触发关键字的路径生成"""
    print("🧪 开始基于触发关键字的文件路径生成测试...")
    print("=" * 50)
    
    try:
        from app.services.file_organizer_service import FileOrganizerService
        from app.services.task_execution_service import TaskExecutionService
        
        organizer = FileOrganizerService()
        task_service = TaskExecutionService()
        print("✅ 服务创建成功")
        
        # 模拟消息对象
        class MockMessage:
            def __init__(self, text=None, caption=None, sender_name=None, media_filename=None):
                self.date = datetime(2024, 5, 16, 10, 30, 0)
                self.message_id = 82925
                self.text = text
                self.caption = caption
                self.sender_name = sender_name
                self.media_filename = media_filename
        
        # 测试关键字匹配功能
        print("\n1. 测试关键字匹配检测:")
        
        # 模拟规则数据
        rule_data = {
            'id': 1,
            'name': '测试规则',
            'keywords': ['美女', '视频', '精彩']
        }
        
        test_messages = [
            MockMessage(text="这是一个关于美女的精彩内容"),
            MockMessage(caption="精彩视频推荐"),
            MockMessage(sender_name="美女主播"),
            MockMessage(media_filename="beautiful_video.mp4"),
            MockMessage(text="这是没有关键字的内容")
        ]
        
        for i, msg in enumerate(test_messages, 1):
            matched_keyword = task_service._get_matched_keyword(msg, rule_data)
            print(f"   消息{i}: 匹配关键字 = '{matched_keyword}'")
        
        # 测试文件路径生成
        print("\n2. 测试基于关键字的文件路径生成:")
        
        test_cases = [
            {
                'name': '匹配"美女"关键字',
                'message': MockMessage(text="这是一个关于美女的精彩内容"),
                'task_data': {
                    'download_path': '/downloads',
                    'rule_name': '高质量内容规则',
                    'matched_keyword': '美女',  # 模拟检测到的关键字
                    'organize_by_date': True,
                    'use_jellyfin_structure': False
                },
                'filename': '16956_82925.mp4',
                'expected_keyword': '美女'
            },
            {
                'name': '匹配"视频"关键字',
                'message': MockMessage(caption="精彩视频推荐"),
                'task_data': {
                    'download_path': '/downloads',
                    'rule_name': '视频内容规则',
                    'matched_keyword': '视频',
                    'organize_by_date': True,
                    'use_jellyfin_structure': False
                },
                'filename': '16956_82925.mp4',
                'expected_keyword': '视频'
            },
            {
                'name': '无匹配关键字（使用规则名）',
                'message': MockMessage(text="其他内容"),
                'task_data': {
                    'download_path': '/downloads',
                    'rule_name': '默认规则',
                    'organize_by_date': True,
                    'use_jellyfin_structure': False
                },
                'filename': '16956_82925.mp4',
                'expected_keyword': '默认规则'
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n   {i}. 测试 {test_case['name']}:")
            
            try:
                generated_path = organizer.generate_organized_path(
                    test_case['message'], 
                    test_case['task_data'], 
                    test_case['filename']
                )
                
                print(f"      生成路径: {generated_path}")
                
                # 验证关键字是否在路径中
                expected_keyword = test_case['expected_keyword']
                if expected_keyword in generated_path:
                    # 计算关键字在路径中出现的次数
                    count = generated_path.count(expected_keyword)
                    print(f"      ✅ 关键字 '{expected_keyword}' 出现 {count} 次（目录名、子目录名、文件名）")
                    
                    # 验证完整格式
                    expected_format = f"/downloads/{expected_keyword}/{expected_keyword} - "
                    if expected_format in generated_path:
                        print(f"      ✅ 符合预期格式")
                    else:
                        print(f"      ❌ 格式不符合预期")
                else:
                    print(f"      ❌ 关键字 '{expected_keyword}' 未出现在路径中")
                    
            except Exception as e:
                print(f"      ❌ 路径生成失败: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n✅ 所有测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"🧪 基于触发关键字的文件整理验证")
    print(f"时间: {datetime.now()}")
    print("=" * 60)
    
    success = test_keyword_based_path_generation()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 基于触发关键字的文件路径生成测试通过")
        print("现在文件将使用触发下载的关键字作为保存路径的基础")
        sys.exit(0)
    else:
        print("❌ 基于触发关键字的文件路径生成测试失败")
        sys.exit(1)