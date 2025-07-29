#!/usr/bin/env python3
"""
测试服务安装器功能
"""
import asyncio
import sys
import os

# 将backend目录添加到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_service_installer():
    """测试服务安装器"""
    print("🚀 开始测试服务安装器...")
    
    try:
        from backend.app.services.service_installer import run_service_installation
        
        # 运行服务安装检查
        result = await run_service_installation()
        
        print("\n" + "="*50)
        print("📋 服务安装测试结果")
        print("="*50)
        
        print(f"✅ 总体状态: {'成功' if result['success'] else '失败'}")
        print(f"🔍 检查项目数: {result.get('total_checks', 0)}")
        
        if result.get('installed_services'):
            print(f"\n🎉 新安装的服务 ({len(result['installed_services'])} 个):")
            for service in result['installed_services']:
                print(f"  - {service['name']}: {service['details']}")
        
        if result.get('already_installed'):
            print(f"\n✓ 已存在的服务 ({len(result['already_installed'])} 个):")
            for service in result['already_installed']:
                print(f"  - {service}")
        
        if result.get('skipped_services'):
            print(f"\n⏭️ 跳过的服务 ({len(result['skipped_services'])} 个):")
            for service in result['skipped_services']:
                print(f"  - {service['name']}: {service['reason']}")
        
        if result.get('failed_services'):
            print(f"\n❌ 安装失败的服务 ({len(result['failed_services'])} 个):")
            for service in result['failed_services']:
                print(f"  - {service['name']}: {service['error']}")
        
        print("\n" + "="*50)
        
        return result['success']
        
    except Exception as e:
        print(f"❌ 测试过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_service_monitor():
    """测试服务监控器"""
    print("\n🔍 开始测试服务监控器...")
    
    try:
        from backend.app.services.service_monitor import service_monitor
        
        # 执行健康检查
        health_result = await service_monitor.check_all_services()
        
        print("\n" + "="*50)
        print("🏥 服务健康检查结果")
        print("="*50)
        
        print(f"📊 整体状态: {health_result.get('overall_status', 'unknown')}")
        print(f"🕐 检查时间: {health_result.get('check_time', 'unknown')}")
        
        services = health_result.get('services', {})
        print(f"\n🔧 服务详情 ({len(services)} 个):")
        
        for service_name, service_data in services.items():
            status = service_data.get('status', 'unknown')
            message = service_data.get('message', '无消息')
            
            status_icon = {
                'healthy': '✅',
                'warning': '⚠️',
                'error': '❌'
            }.get(status, '❓')
            
            print(f"  {status_icon} {service_name}: {message}")
        
        if health_result.get('warnings'):
            print(f"\n⚠️ 警告信息:")
            for warning in health_result['warnings']:
                print(f"  - {warning}")
        
        if health_result.get('errors'):
            print(f"\n❌ 错误信息:")
            for error in health_result['errors']:
                print(f"  - {error}")
        
        print("\n" + "="*50)
        
        return health_result.get('overall_status') in ['healthy', 'degraded']
        
    except Exception as e:
        print(f"❌ 监控测试过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🧪 TgGod 服务依赖自动下载测试")
    print("="*50)
    
    # 测试服务安装器
    installer_success = await test_service_installer()
    
    # 测试服务监控器
    monitor_success = await test_service_monitor()
    
    # 汇总结果
    print("\n" + "="*50)
    print("📋 测试汇总")
    print("="*50)
    
    print(f"🔧 服务安装器: {'✅ 通过' if installer_success else '❌ 失败'}")
    print(f"🔍 服务监控器: {'✅ 通过' if monitor_success else '❌ 失败'}")
    
    overall_success = installer_success and monitor_success
    print(f"\n🎯 总体结果: {'✅ 全部通过' if overall_success else '❌ 存在问题'}")
    
    if not overall_success:
        print("\n💡 建议:")
        print("  - 检查系统权限 (某些包需要root权限安装)")
        print("  - 确保网络连接正常")
        print("  - 查看详细错误信息进行排查")
    
    return 0 if overall_success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)