# 数据库管理文档

## 概述

TgGod 项目包含自动化的数据库检查和修复系统，确保应用启动时数据库结构正确。

## 数据库检查脚本

### 1. 自动检查和修复 (check_database.py)

这个脚本会自动检查数据库结构并进行必要的修复：

```bash
python check_database.py
```

功能：
- 检查数据库连接
- 验证必需的表是否存在
- 检查表的列结构
- 自动运行迁移来修复缺失的表或列
- 验证数据库版本

### 2. 应用启动器 (start_app.py)

集成了数据库检查的应用启动器：

```bash
python start_app.py
```

功能：
- 启动前自动检查数据库
- 修复发现的问题
- 启动 FastAPI 应用

### 3. 手动迁移 (migrate.py)

手动运行数据库迁移：

```bash
python migrate.py
```

## 常见问题解决

### 1. 数据库连接错误

如果出现 `database connection failed` 错误：
1. 检查 `.env` 文件中的数据库配置
2. 确保数据库服务正在运行
3. 验证数据库用户权限

### 2. 缺少字段错误

如果出现 `'field_name' is an invalid keyword argument` 错误：
1. 运行数据库检查脚本：`python check_database.py`
2. 或者手动运行迁移：`python migrate.py`

### 3. 表缺失错误

如果出现表不存在的错误：
1. 运行数据库检查脚本会自动创建缺失的表
2. 或者使用 alembic 命令：`alembic upgrade head`

## 数据库架构

### 主要表结构

1. **users** - 用户表
2. **telegram_groups** - Telegram群组表
3. **telegram_messages** - Telegram消息表
4. **filter_rules** - 过滤规则表
5. **system_logs** - 系统日志表
6. **alembic_version** - 迁移版本表

### 重要字段

**telegram_messages 表的关键字段：**
- `is_own_message`: 标记是否为当前用户发送的消息
- `reply_to_message_id`: 回复的消息ID
- `is_forwarded`: 是否为转发消息
- `forwarded_from`: 转发来源
- `is_pinned`: 是否为置顶消息
- `reactions`: 消息反应数据
- `mentions`: 提及的用户
- `hashtags`: 话题标签
- `urls`: 消息中的链接

## 环境变量

确保在 `.env` 文件中设置了正确的数据库连接：

```env
DATABASE_URL=sqlite:///./tggod.db
# 或者使用 PostgreSQL
DATABASE_URL=postgresql://user:password@localhost/tggod
```

## 开发指南

### 添加新字段

1. 修改模型文件 (`app/models/telegram.py`)
2. 创建新的迁移文件：
   ```bash
   alembic revision --autogenerate -m "add new field"
   ```
3. 运行迁移：
   ```bash
   alembic upgrade head
   ```

### 创建新表

1. 在 `app/models/` 目录中创建新的模型文件
2. 在 `app/models/__init__.py` 中导入新模型
3. 创建迁移文件
4. 运行迁移

## 生产环境部署

在生产环境中，建议：

1. 使用 `start_app.py` 启动应用，它会自动检查数据库
2. 设置适当的日志级别
3. 使用 PostgreSQL 或 MySQL 而不是 SQLite
4. 定期备份数据库

## 监控和维护

### 日志检查

应用会记录所有数据库操作的日志，包括：
- 数据库连接状态
- 迁移执行结果
- 错误信息

### 性能监控

定期检查：
- 数据库查询性能
- 表大小和增长率
- 索引使用情况

### 数据清理

根据需要清理旧数据：
- 定期删除过期的消息
- 清理无效的规则
- 压缩日志文件

## 故障排除

### 常见错误代码

1. **SQLAlchemy 错误**：通常是模型定义或迁移问题
2. **连接超时**：检查数据库服务状态
3. **权限错误**：确保数据库用户有足够权限

### 恢复步骤

如果数据库损坏：
1. 停止应用
2. 从备份恢复数据库
3. 运行 `python check_database.py` 验证结构
4. 重启应用

### 联系支持

如果遇到无法解决的问题，请提供：
- 错误日志
- 数据库版本信息
- 环境配置信息