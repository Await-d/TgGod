#!/usr/bin/env python3
"""
简化的服务检查测试
"""
import subprocess
import shutil
import os

def test_system_tools():
    """测试系统工具"""
    print("🔧 测试系统工具...")
    
    tools = ["curl", "wget", "git", "unzip", "ffmpeg", "convert"]
    results = {}
    
    for tool in tools:
        if shutil.which(tool):
            results[tool] = "✅ 已安装"
        else:
            results[tool] = "❌ 未安装"
    
    for tool, status in results.items():
        print(f"  {tool}: {status}")
    
    return results

def test_python_packages():
    """测试Python包"""
    print("\n🐍 测试Python包...")
    
    packages = {
        "psutil": "系统监控",
        "cpuinfo": "CPU信息",
        "PIL": "图像处理",
        "requests": "HTTP请求"
    }
    
    results = {}
    
    for package, description in packages.items():
        try:
            __import__(package)
            results[package] = f"✅ 已安装 - {description}"
        except ImportError:
            results[package] = f"❌ 未安装 - {description}"
    
    for package, status in results.items():
        print(f"  {package}: {status}")
    
    return results

def test_fonts():
    """测试字体文件"""
    print("\n🔤 测试字体文件...")
    
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/Windows/Fonts/msyh.ttc"
    ]
    
    found_fonts = []
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            font_name = os.path.basename(font_path)
            found_fonts.append(font_name)
            print(f"  ✅ 找到字体: {font_name}")
    
    if not found_fonts:
        print("  ❌ 未找到任何系统字体")
    
    return found_fonts

def test_system_resources():
    """测试系统资源获取"""
    print("\n📊 测试系统资源获取...")
    
    try:
        import psutil
        
        # CPU测试
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        print(f"  ✅ CPU: {cpu_percent:.1f}% 使用率, {cpu_count} 核心")
        
        # 内存测试
        memory = psutil.virtual_memory()
        print(f"  ✅ 内存: {memory.percent:.1f}% 使用率, {memory.total//1024//1024:.0f}MB 总量")
        
        # 磁盘测试
        try:
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            print(f"  ✅ 磁盘: {disk_percent:.1f}% 使用率, {disk.total//1024//1024//1024:.1f}GB 总量")
        except:
            print("  ⚠️ 磁盘信息获取失败")
        
        return True
        
    except ImportError:
        print("  ❌ psutil未安装，无法获取系统资源信息")
        return False

def test_media_processing():
    """测试媒体处理能力"""
    print("\n🎨 测试媒体处理能力...")
    
    # 测试FFmpeg
    if shutil.which("ffmpeg"):
        try:
            result = subprocess.run(["ffmpeg", "-version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"  ✅ FFmpeg: {version_line}")
            else:
                print("  ❌ FFmpeg运行异常")
        except:
            print("  ❌ FFmpeg测试失败")
    else:
        print("  ❌ FFmpeg未安装")
    
    # 测试ImageMagick
    if shutil.which("convert"):
        try:
            result = subprocess.run(["convert", "-version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0].split()[2:4]
                print(f"  ✅ ImageMagick: {' '.join(version_line)}")
            else:
                print("  ❌ ImageMagick运行异常")
        except:
            print("  ❌ ImageMagick测试失败")
    else:
        print("  ❌ ImageMagick未安装")

def main():
    """主测试函数"""
    print("🧪 TgGod 服务依赖检查测试")
    print("="*50)
    
    # 执行各项测试
    system_tools = test_system_tools()
    python_packages = test_python_packages()
    fonts = test_fonts()
    resources_ok = test_system_resources()
    test_media_processing()
    
    # 统计结果
    print("\n" + "="*50)
    print("📋 测试汇总")
    print("="*50)
    
    # 系统工具统计
    installed_tools = sum(1 for status in system_tools.values() if "✅" in status)
    total_tools = len(system_tools)
    print(f"🔧 系统工具: {installed_tools}/{total_tools} 已安装")
    
    # Python包统计
    installed_packages = sum(1 for status in python_packages.values() if "✅" in status)  
    total_packages = len(python_packages)
    print(f"🐍 Python包: {installed_packages}/{total_packages} 已安装")
    
    # 字体统计
    print(f"🔤 系统字体: {len(fonts)} 个可用")
    
    # 资源监控
    print(f"📊 资源监控: {'✅ 可用' if resources_ok else '❌ 不可用'}")
    
    # 关键服务检查
    critical_services = {
        "ffmpeg": "✅" in system_tools.get("ffmpeg", ""),
        "psutil": "✅" in python_packages.get("psutil", ""),
        "PIL": "✅" in python_packages.get("PIL", ""),
        "fonts": len(fonts) > 0
    }
    
    critical_ok = sum(critical_services.values())
    total_critical = len(critical_services)
    
    print(f"\n🎯 关键服务: {critical_ok}/{total_critical} 就绪")
    
    if critical_ok == total_critical:
        print("✅ 所有关键服务就绪，项目可以正常运行")
        return 0
    else:
        print("⚠️ 部分关键服务缺失，建议运行服务安装器进行补充")
        
        missing_services = []
        for service, available in critical_services.items():
            if not available:
                missing_services.append(service)
        
        print(f"缺失服务: {', '.join(missing_services)}")
        return 1

if __name__ == "__main__":
    exit(main())