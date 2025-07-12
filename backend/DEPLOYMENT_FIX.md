# 生产环境部署指南

## 问题描述
在生产环境中可能出现 `no such column: telegram_messages.forwarded_from_id` 错误，这是因为数据库缺少转发消息的新字段。

## 解决方案

### 方法1：自动修复（推荐）
应用启动时会自动检查并修复缺失的字段，无需手动干预。

### 方法2：手动修复
如果自动修复失败，可以手动运行修复脚本：

```bash
# 进入后端目录
cd backend

# 运行强制修复脚本
python force_fix_forwarded_columns.py

# 或运行完整的部署前检查
./pre_deploy_fix.sh
```

### 方法3：SQL手动修复
如果以上方法都失败，可以直接执行SQL语句：

```sql
-- 添加转发消息相关字段
ALTER TABLE telegram_messages ADD COLUMN forwarded_from_id BIGINT;
ALTER TABLE telegram_messages ADD COLUMN forwarded_from_type VARCHAR(20);
ALTER TABLE telegram_messages ADD COLUMN forwarded_date DATETIME;
```

## 字段说明

新增的转发消息字段：

- `forwarded_from_id` (BIGINT) - 转发来源ID（用户ID或群组ID）
- `forwarded_from_type` (VARCHAR(20)) - 转发来源类型（user/group/channel）
- `forwarded_date` (DATETIME) - 原消息发送时间

## 验证修复

修复完成后，可以验证字段是否存在：

```bash
python -c "
import sqlite3
conn = sqlite3.connect('tggod.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(telegram_messages)')
columns = [row[1] for row in cursor.fetchall()]
required = ['forwarded_from_id', 'forwarded_from_type', 'forwarded_date']
for field in required:
    if field in columns:
        print(f'✅ {field} 存在')
    else:
        print(f'❌ {field} 缺失')
conn.close()
"
```

## 注意事项

1. **数据备份**：修复前建议备份数据库文件
2. **权限检查**：确保应用有数据库写入权限
3. **容器环境**：在Docker环境中，确保数据库文件在持久化卷中
4. **自动修复**：应用启动时会自动尝试修复，通常无需手动干预