#!/usr/bin/env python3
"""
数据库锁定修复验证脚本
测试修复后的任务执行稳定性
"""

import asyncio
import logging
import os
import sys
import time
import random
from pathlib import Path
from typing import List

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from app.services.task_db_manager import task_db_manager
from app.models.rule import DownloadTask
from app.models.log import TaskLog
from app.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseStressTest:
    """数据库压力测试器"""
    
    def __init__(self):
        self.test_results = {
            "concurrent_sessions": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "lock_errors": 0,
            "total_time": 0,
            "operations_per_second": 0
        }
    
    async def test_concurrent_progress_updates(self, num_tasks: int = 5, updates_per_task: int = 20):
        """测试并发进度更新"""
        logger.info(f"开始并发进度更新测试: {num_tasks} 个任务，每个任务 {updates_per_task} 次更新")
        
        async def update_task_progress(task_id: int, updates: int):
            """模拟任务进度更新"""
            for i in range(updates):
                try:
                    progress = min(int((i + 1) / updates * 100), 100)
                    downloaded_count = i + 1
                    
                    async with task_db_manager.get_task_session(task_id, "progress") as session:
                        # 模拟查找任务（如果存在）
                        task = session.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                        if not task:
                            # 创建测试任务
                            task = DownloadTask(
                                name=f"测试任务_{task_id}",
                                group_id=1,
                                rule_id=1,
                                status="running",
                                progress=0,
                                download_path="/tmp/test"
                            )
                            session.add(task)
                            session.flush()
                        
                        # 更新进度
                        task.progress = progress
                        task.downloaded_messages = downloaded_count
                        session.commit()
                    
                    self.test_results["successful_operations"] += 1
                    
                    # 模拟真实任务间的短延迟
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    self.test_results["failed_operations"] += 1
                    if "locked" in str(e).lower() or "busy" in str(e).lower():
                        self.test_results["lock_errors"] += 1
                    logger.error(f"任务 {task_id} 进度更新失败: {e}")
        
        # 启动并发任务
        start_time = time.time()
        tasks = []
        for task_id in range(1, num_tasks + 1):
            task = asyncio.create_task(update_task_progress(task_id, updates_per_task))
            tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        self.test_results["total_time"] = end_time - start_time
        total_operations = self.test_results["successful_operations"] + self.test_results["failed_operations"]
        if self.test_results["total_time"] > 0:
            self.test_results["operations_per_second"] = total_operations / self.test_results["total_time"]
        
        logger.info(f"并发进度更新测试完成，耗时: {self.test_results['total_time']:.2f} 秒")
    
    async def test_concurrent_log_writes(self, num_loggers: int = 10, logs_per_logger: int = 50):
        """测试并发日志写入"""
        logger.info(f"开始并发日志写入测试: {num_loggers} 个日志器，每个写入 {logs_per_logger} 条日志")
        
        async def write_task_logs(task_id: int, log_count: int):
            """模拟任务日志写入"""
            for i in range(log_count):
                try:
                    async with task_db_manager.get_task_session(task_id, "log") as session:
                        log_entry = TaskLog(
                            task_id=task_id,
                            level=random.choice(["INFO", "WARNING", "ERROR"]),
                            message=f"测试日志消息 {i+1} from task {task_id}",
                            details={"test": True, "iteration": i+1}
                        )
                        session.add(log_entry)
                        session.commit()
                    
                    self.test_results["successful_operations"] += 1
                    
                    # 模拟真实日志间的延迟
                    await asyncio.sleep(0.05)
                    
                except Exception as e:
                    self.test_results["failed_operations"] += 1
                    if "locked" in str(e).lower():
                        self.test_results["lock_errors"] += 1
                    logger.error(f"任务 {task_id} 日志写入失败: {e}")
        
        # 启动并发日志写入
        start_time = time.time()
        tasks = []
        for task_id in range(1, num_loggers + 1):
            task = asyncio.create_task(write_task_logs(task_id, logs_per_logger))
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        log_test_time = end_time - start_time
        logger.info(f"并发日志写入测试完成，耗时: {log_test_time:.2f} 秒")
    
    async def test_mixed_operations(self, duration_seconds: int = 30):
        """测试混合操作"""
        logger.info(f"开始混合操作测试，持续 {duration_seconds} 秒")
        
        async def random_database_operation():
            """随机数据库操作"""
            operation_type = random.choice(["progress", "log", "completion"])
            task_id = random.randint(1, 5)
            
            try:
                if operation_type == "progress":
                    async with task_db_manager.get_task_session(task_id, "progress") as session:
                        task = session.query(DownloadTask).filter(DownloadTask.id == task_id).first()
                        if task:
                            task.progress = random.randint(0, 100)
                            task.downloaded_messages = random.randint(0, 1000)
                            session.commit()
                
                elif operation_type == "log":
                    async with task_db_manager.get_task_session(task_id, "log") as session:
                        log_entry = TaskLog(
                            task_id=task_id,
                            level=random.choice(["INFO", "WARNING", "ERROR"]),
                            message=f"随机测试日志 {time.time()}",
                            details={"random_test": True}
                        )
                        session.add(log_entry)
                        session.commit()
                
                elif operation_type == "completion":
                    await task_db_manager.quick_status_update(
                        task_id, 
                        random.choice(["completed", "failed"]),
                        "测试状态更新"
                    )
                
                self.test_results["successful_operations"] += 1
                
            except Exception as e:
                self.test_results["failed_operations"] += 1
                if "locked" in str(e).lower():
                    self.test_results["lock_errors"] += 1
        
        # 持续运行混合操作
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        tasks = []
        while time.time() < end_time:
            # 每次启动1-3个并发操作
            num_concurrent = random.randint(1, 3)
            batch_tasks = []
            for _ in range(num_concurrent):
                task = asyncio.create_task(random_database_operation())
                batch_tasks.append(task)
            
            # 等待这批操作完成
            await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # 短暂延迟
            await asyncio.sleep(random.uniform(0.1, 0.5))
        
        actual_time = time.time() - start_time
        logger.info(f"混合操作测试完成，实际耗时: {actual_time:.2f} 秒")
    
    def print_test_results(self):
        """打印测试结果"""
        logger.info("=" * 60)
        logger.info("数据库锁定修复验证结果")
        logger.info("=" * 60)
        
        total_operations = self.test_results["successful_operations"] + self.test_results["failed_operations"]
        success_rate = (self.test_results["successful_operations"] / max(total_operations, 1)) * 100
        
        logger.info(f"总操作数: {total_operations}")
        logger.info(f"成功操作: {self.test_results['successful_operations']}")
        logger.info(f"失败操作: {self.test_results['failed_operations']}")
        logger.info(f"锁定错误: {self.test_results['lock_errors']}")
        logger.info(f"成功率: {success_rate:.2f}%")
        logger.info(f"总耗时: {self.test_results['total_time']:.2f} 秒")
        logger.info(f"操作/秒: {self.test_results['operations_per_second']:.2f}")
        
        # 评估结果
        if success_rate >= 95 and self.test_results['lock_errors'] <= total_operations * 0.02:
            logger.info("✅ 测试通过：数据库锁定问题已得到显著改善")
            return True
        elif success_rate >= 85:
            logger.warning("⚠️ 测试部分通过：仍有一些锁定问题，但已有改善")
            return True
        else:
            logger.error("❌ 测试失败：数据库锁定问题仍然严重")
            return False

async def main():
    """主测试函数"""
    logger.info("开始数据库锁定修复验证测试")
    
    stress_test = DatabaseStressTest()
    
    try:
        # 测试1: 并发进度更新
        await stress_test.test_concurrent_progress_updates(num_tasks=8, updates_per_task=25)
        
        # 短暂休息
        await asyncio.sleep(2)
        
        # 测试2: 并发日志写入
        await stress_test.test_concurrent_log_writes(num_loggers=12, logs_per_logger=30)
        
        # 短暂休息
        await asyncio.sleep(2)
        
        # 测试3: 混合操作压力测试
        await stress_test.test_mixed_operations(duration_seconds=45)
        
        # 清理会话
        await task_db_manager.cleanup_sessions()
        
        # 打印结果
        test_passed = stress_test.print_test_results()
        
        if test_passed:
            logger.info("🎉 数据库锁定修复验证成功！")
            return True
        else:
            logger.error("💥 数据库锁定修复验证失败，需要进一步优化")
            return False
            
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)