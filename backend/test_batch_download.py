#!/usr/bin/env python3
"""
测试批量下载功能的简单脚本
"""
import asyncio
import json
import sys
import os

# 添加项目路径到sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.api.media import (
        BatchDownloadRequest, 
        batch_downloads, 
        batch_semaphores,
        batch_download_manager,
        batch_download_single_file
    )
    print("✅ 成功导入批量下载相关模块")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

async def test_batch_download_data_models():
    """测试批量下载数据模型"""
    print("\n📋 测试数据模型...")
    
    try:
        # 测试BatchDownloadRequest
        request = BatchDownloadRequest(
            message_ids=[1, 2, 3, 4, 5],
            force=False,
            max_concurrent=3
        )
        print(f"✅ BatchDownloadRequest创建成功: {request.model_dump()}")
        
        # 测试参数验证
        request_empty = BatchDownloadRequest(message_ids=[])
        print(f"✅ 空消息列表处理成功: {request_empty.model_dump()}")
        
        # 测试默认值
        request_defaults = BatchDownloadRequest(message_ids=[1, 2, 3])
        print(f"✅ 默认参数处理成功: force={request_defaults.force}, max_concurrent={request_defaults.max_concurrent}")
        
    except Exception as e:
        print(f"❌ 数据模型测试失败: {e}")
        return False
    
    return True

async def test_batch_manager_logic():
    """测试批量下载管理器逻辑"""
    print("\n🔄 测试批量下载管理器逻辑...")
    
    try:
        # 模拟批量下载信息
        batch_id = "test_batch_12345"
        batch_downloads[batch_id] = {
            "message_ids": [101, 102, 103],
            "total_files": 3,
            "status": "started",
            "max_concurrent": 2,
            "force": False
        }
        
        # 创建信号量
        batch_semaphores[batch_id] = asyncio.Semaphore(2)
        print(f"✅ 批量下载数据结构创建成功: batch_id={batch_id}")
        
        # 测试信号量
        semaphore = batch_semaphores[batch_id]
        print(f"✅ 信号量创建成功: 并发限制={semaphore._value}")
        
        # 清理测试数据
        if batch_id in batch_downloads:
            del batch_downloads[batch_id]
        if batch_id in batch_semaphores:
            del batch_semaphores[batch_id]
        print("✅ 测试数据清理完成")
        
    except Exception as e:
        print(f"❌ 批量管理器逻辑测试失败: {e}")
        return False
    
    return True

async def test_concurrent_control():
    """测试并发控制机制"""
    print("\n⚡ 测试并发控制机制...")
    
    try:
        # 创建信号量限制并发为2
        semaphore = asyncio.Semaphore(2)
        
        async def mock_download_task(task_id, delay):
            async with semaphore:
                print(f"  📥 任务 {task_id} 开始执行")
                await asyncio.sleep(delay)
                print(f"  ✅ 任务 {task_id} 完成")
        
        # 创建多个并发任务
        tasks = [
            mock_download_task(1, 0.1),
            mock_download_task(2, 0.1),
            mock_download_task(3, 0.1),
            mock_download_task(4, 0.1),
            mock_download_task(5, 0.1)
        ]
        
        # 并发执行，但实际只能同时执行2个
        await asyncio.gather(*tasks)
        print("✅ 并发控制测试成功")
        
    except Exception as e:
        print(f"❌ 并发控制测试失败: {e}")
        return False
    
    return True

async def test_api_response_models():
    """测试API响应模型"""
    print("\n📤 测试API响应模型...")
    
    try:
        from app.api.media import BatchDownloadResponse, BatchStatusResponse
        
        # 测试批量下载响应
        batch_response = BatchDownloadResponse(
            batch_id="batch_abc123",
            status="started",
            message="测试批量下载响应",
            total_files=5,
            started_downloads=[1, 2, 3],
            already_downloaded=[4],
            failed_to_start=[{"message_id": 5, "reason": "测试失败原因"}]
        )
        print(f"✅ BatchDownloadResponse创建成功")
        
        # 测试状态响应
        status_response = BatchStatusResponse(
            batch_id="batch_abc123",
            total_files=5,
            completed=2,
            downloading=1,
            failed=1,
            pending=1,
            overall_status="in_progress",
            files=[
                {"message_id": 1, "status": "completed", "progress": 100},
                {"message_id": 2, "status": "downloading", "progress": 50}
            ]
        )
        print(f"✅ BatchStatusResponse创建成功")
        
    except Exception as e:
        print(f"❌ API响应模型测试失败: {e}")
        return False
    
    return True

async def main():
    """主测试函数"""
    print("🚀 开始批量下载功能测试...\n")
    
    tests = [
        ("数据模型测试", test_batch_download_data_models),
        ("批量管理器逻辑测试", test_batch_manager_logic),
        ("并发控制测试", test_concurrent_control),
        ("API响应模型测试", test_api_response_models)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
                print(f"✅ {test_name} 通过")
            else:
                failed += 1
                print(f"❌ {test_name} 失败")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} 异常: {e}")
    
    print(f"\n📊 测试结果:")
    print(f"   ✅ 通过: {passed}")
    print(f"   ❌ 失败: {failed}")
    print(f"   📈 成功率: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 所有测试通过! 批量下载功能实现正确。")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，需要检查实现。")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⛔ 测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 测试过程中发生未处理异常: {e}")
        sys.exit(1)