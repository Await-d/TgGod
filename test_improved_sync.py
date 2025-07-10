#!/usr/bin/env python3
"""
优化版群组同步测试脚本
测试改进后的错误处理和flood wait机制
"""

import requests
import json
import time

def test_improved_sync():
    """测试改进后的群组同步功能"""
    
    base_url = "http://localhost:8001/api/telegram"
    
    print("🔧 测试优化后的Telegram群组同步功能")
    print("=" * 50)
    
    # 1. 测试连接状态
    print("1. 检查Telegram连接状态...")
    try:
        response = requests.post(f"{base_url}/test-connection", timeout=30)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   连接状态: {result.get('connection_status', 'unknown')}")
            print(f"   认证状态: {'已认证' if result.get('success') else '未认证'}")
            
            if result.get('success'):
                stats = result.get('stats', {})
                print(f"   总对话数: {stats.get('total_dialogs', 0)}")
                print(f"   群组数量: {stats.get('total_groups', 0)}")
            
            if not result.get('success'):
                print("   ⚠️  需要先完成Telegram认证")
                return False
        else:
            print(f"   ❌ API调用失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ 连接测试失败: {e}")
        return False
    
    # 2. 测试群组同步（带进度监控）
    print("\n2. 开始群组同步...")
    try:
        print("   正在同步群组，请耐心等待...")
        start_time = time.time()
        
        response = requests.post(f"{base_url}/sync-groups", timeout=300)  # 5分钟超时
        end_time = time.time()
        
        print(f"   同步耗时: {end_time - start_time:.2f} 秒")
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   同步结果: {result}")
            
            if result.get('success'):
                print(f"   ✅ 同步成功!")
                print(f"      - 成功同步: {result.get('synced_count', 0)} 个群组")
                print(f"      - 总群组数: {result.get('total_groups', 0)} 个")
                
                errors = result.get('errors', [])
                if errors:
                    print(f"      - 错误数量: {len(errors)} 个")
                    print("      - 错误详情:")
                    for error in errors[:5]:  # 只显示前5个错误
                        print(f"        * {error}")
                    if len(errors) > 5:
                        print(f"        ... 还有 {len(errors) - 5} 个错误")
                else:
                    print("      - 没有错误")
            else:
                print(f"   ❌ 同步失败: {result.get('message', 'Unknown error')}")
                return False
        else:
            print(f"   ❌ 同步失败: HTTP {response.status_code}")
            try:
                error_info = response.json()
                print(f"      错误信息: {error_info}")
            except:
                print(f"      错误内容: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ 同步过程出错: {e}")
        return False
    
    # 3. 验证同步结果
    print("\n3. 验证同步结果...")
    try:
        response = requests.get(f"{base_url}/groups", timeout=30)
        
        if response.status_code == 200:
            groups = response.json()
            print(f"   数据库中的群组数量: {len(groups)}")
            
            if groups:
                print("   群组列表:")
                for i, group in enumerate(groups[:10]):  # 显示前10个群组
                    username = group.get('username', '无用户名')
                    title = group.get('title', '未知标题')
                    member_count = group.get('member_count', 0)
                    print(f"      {i+1}. {title} (@{username}) - {member_count} 成员")
                
                if len(groups) > 10:
                    print(f"      ... 还有 {len(groups) - 10} 个群组")
            else:
                print("   ⚠️  数据库中没有群组，可能同步失败")
                
        else:
            print(f"   ❌ 获取群组列表失败: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ 验证失败: {e}")
        return False
    
    # 4. 性能统计
    print("\n4. 性能统计:")
    print(f"   总耗时: {end_time - start_time:.2f} 秒")
    if result.get('synced_count', 0) > 0:
        avg_time = (end_time - start_time) / result['synced_count']
        print(f"   平均每个群组: {avg_time:.2f} 秒")
    
    return True

def main():
    success = test_improved_sync()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 所有测试通过！群组同步功能正常工作")
        print("\n💡 如果遇到Flood Wait错误，这是正常的，系统会自动重试")
        print("💡 建议在低峰期进行大量群组同步，避免频率限制")
    else:
        print("❌ 测试失败，请检查:")
        print("   1. 后端服务是否正常运行")
        print("   2. Telegram认证是否完成")
        print("   3. 网络连接是否正常")
        print("   4. API配置是否正确")
        
    print("\n📋 故障排除建议:")
    print("   - 查看后端日志: docker logs <container_name>")
    print("   - 检查认证状态: curl http://localhost:8001/api/telegram/auth/status")
    print("   - 手动测试连接: curl http://localhost:8001/api/telegram/test-connection")

if __name__ == "__main__":
    main()