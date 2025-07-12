# TgGod 媒体下载器 EOF 错误解决方案

## 问题诊断

### 错误现象
```
app.services.media_downloader - ERROR - Telegram媒体下载器初始化失败: EOF when reading a line
```

### 根本原因
经过诊断，发现问题的根本原因是 **Telegram API 配置未设置**：
- `telegram_api_id` 为空
- `telegram_api_hash` 为空

这导致 Telegram 客户端在初始化时无法正确连接，产生 EOF 错误。

## 解决方案

### 方法1: 使用自动配置脚本 (推荐)

1. 运行配置脚本：
```bash
cd /root/project/TgGod/backend
./setup_telegram_api.sh
```

2. 按照提示完成配置：
   - 访问 https://my.telegram.org
   - 登录并创建应用
   - 输入获取的 API ID 和 API Hash

### 方法2: 手动配置

1. 获取 Telegram API 配置：
   - 访问 https://my.telegram.org
   - 使用手机号登录
   - 创建新应用获取 API ID 和 API Hash

2. 更新数据库配置：
```bash
sqlite3 /app/data/tggod.db
UPDATE system_config SET value='YOUR_API_ID' WHERE key='telegram_api_id';
UPDATE system_config SET value='YOUR_API_HASH' WHERE key='telegram_api_hash';
.exit
```

### 方法3: 检查当前配置状态

运行诊断脚本：
```bash
python check_telegram_config.py
```

## 代码修复内容

### 1. 媒体下载器改进 (`media_downloader.py`)

- ✅ 使用与主服务相同的 session 路径
- ✅ 添加认证状态检查
- ✅ 改进连接状态验证
- ✅ 增强错误处理和重试机制
- ✅ 添加 FloodWait 错误处理

### 2. 下载任务错误处理 (`media.py`)

- ✅ 添加下载器初始化异常处理
- ✅ 针对 EOF 和认证错误的特殊处理
- ✅ 改进错误信息提示

### 3. 诊断工具

- ✅ `check_telegram_config.py` - 配置状态检查
- ✅ `setup_telegram_api.sh` - 自动配置脚本
- ✅ `test_media_downloader.py` - 功能测试脚本

## 验证修复

配置完成后，可以通过以下步骤验证：

1. 检查配置状态：
```bash
python check_telegram_config.py
```

2. 测试媒体下载器：
```bash
python test_media_downloader.py
```

3. 重启 TgGod 程序并尝试下载媒体文件

## 预防措施

1. **配置备份**: 定期备份数据库配置
2. **监控日志**: 关注 Telegram 认证相关错误
3. **定期检查**: 使用诊断脚本定期检查配置状态

## 技术细节

### EOF 错误的常见原因
1. **API 配置缺失** - 主要原因
2. **Session 文件损坏** - 次要原因  
3. **网络连接问题** - 偶发原因
4. **Telegram API 限制** - FloodWait 错误

### 修复后的改进
- 统一 session 管理
- 智能重连机制
- 详细错误分类
- 用户友好的错误提示

---

**配置完成后，媒体下载功能应该能够正常工作！**