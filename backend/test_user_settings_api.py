#!/usr/bin/env python3
"""
测试用户设置API和数据库自动修复功能
"""
import requests
import json
import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API基础URL
BASE_URL = "http://localhost:8000/api"  # 本地测试
AUTH_URL = f"{BASE_URL}/auth/login"
SETTINGS_URL = f"{BASE_URL}/user/settings"

def login():
    """登录获取token"""
    credentials = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(AUTH_URL, json=credentials)
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                logger.info("登录成功，获取到token")
                return token
        
        logger.error(f"登录失败: {response.status_code}, {response.text}")
        return None
    except Exception as e:
        logger.error(f"登录异常: {e}")
        return None

def test_settings_api(token):
    """测试用户设置API"""
    if not token:
        logger.error("未提供token，无法测试API")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 测试获取设置
    try:
        logger.info("1. 测试获取用户设置")
        response = requests.get(SETTINGS_URL, headers=headers)
        if response.status_code == 200:
            settings = response.json()
            logger.info(f"成功获取设置: {json.dumps(settings, ensure_ascii=False, indent=2)}")
        else:
            logger.error(f"获取设置失败: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        logger.error(f"获取设置异常: {e}")
        return False
    
    # 测试更新设置
    try:
        logger.info("2. 测试更新用户设置")
        # 创建包含时间戳的测试设置
        test_settings = {
            "settings_data": {
                "theme": "dark",
                "language": "en_US",
                "display_density": "comfortable",
                "test_timestamp": datetime.now().isoformat()
            }
        }
        
        response = requests.post(SETTINGS_URL, json=test_settings, headers=headers)
        if response.status_code == 200:
            updated = response.json()
            logger.info(f"成功更新设置: {json.dumps(updated, ensure_ascii=False, indent=2)}")
            
            # 验证设置是否已更新
            response = requests.get(SETTINGS_URL, headers=headers)
            if response.status_code == 200:
                verify = response.json()
                
                # 验证设置值是否匹配
                if verify.get("theme") == "dark" and verify.get("language") == "en_US":
                    logger.info("✅ 设置更新验证成功")
                else:
                    logger.error(f"❌ 设置更新验证失败: {json.dumps(verify, ensure_ascii=False)}")
                    return False
            else:
                logger.error(f"验证更新失败: {response.status_code}")
                return False
        else:
            logger.error(f"更新设置失败: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        logger.error(f"更新设置异常: {e}")
        return False
    
    # 测试重置设置
    try:
        logger.info("3. 测试重置用户设置")
        response = requests.delete(SETTINGS_URL, headers=headers)
        if response.status_code == 200:
            logger.info(f"成功重置设置: {response.text}")
            
            # 验证设置是否已重置
            response = requests.get(SETTINGS_URL, headers=headers)
            if response.status_code == 200:
                verify = response.json()
                
                # 验证是否为默认值
                if verify.get("theme") == "system":
                    logger.info("✅ 设置重置验证成功")
                else:
                    logger.error(f"❌ 设置重置验证失败: {json.dumps(verify, ensure_ascii=False)}")
                    return False
            else:
                logger.error(f"验证重置失败: {response.status_code}")
                return False
        else:
            logger.error(f"重置设置失败: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        logger.error(f"重置设置异常: {e}")
        return False
    
    logger.info("所有用户设置API测试通过 ✅")
    return True

def main():
    """主函数"""
    logger.info("开始测试用户设置API和自动修复功能")
    
    # 登录获取token
    token = login()
    if not token:
        logger.error("获取token失败，退出测试")
        sys.exit(1)
    
    # 测试设置API
    success = test_settings_api(token)
    
    if success:
        logger.info("===== 测试结果: 成功 =====")
        sys.exit(0)
    else:
        logger.error("===== 测试结果: 失败 =====")
        sys.exit(1)

if __name__ == "__main__":
    main()