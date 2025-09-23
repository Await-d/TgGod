# SQLite迁移管理器使用指南

本文档介绍TgGod项目中SQLite迁移管理的解决方案，特别是如何处理SQLite不支持的DROP COLUMN操作。

## 背景问题

SQLite数据库有一些DDL操作限制：
- **不支持 DROP COLUMN** - 这是最常见的问题
- **不支持 ALTER COLUMN** - 无法修改现有列的类型或约束
- **有限的 ALTER TABLE 支持** - 只支持 ADD COLUMN 和 RENAME TO

## 解决方案

我们开发了完整的SQLite迁移管理系统：

### 1. SQLite迁移管理器 (`sqlite_migration_manager.py`)

核心功能：
- **表重建策略** - 通过创建新表、复制数据、删除旧表的方式实现DROP COLUMN
- **自动备份** - 每次操作前自动创建数据库备份
- **数据完整性验证** - 确保迁移后数据不丢失
- **索引和约束保持** - 自动重建索引、触发器等数据库对象
- **事务支持** - 失败时自动回滚

#### 主要方法：

```python
# 删除列（通过表重建）
success = migration_manager.rebuild_table_drop_columns(
    table_name='filter_rules',
    columns_to_drop=['column1', 'column2']
)

# 添加列（SQLite原生支持）
success = migration_manager.add_columns(
    table_name='filter_rules',
    columns=[
        {
            'name': 'new_column',
            'type': 'VARCHAR(100)',
            'not_null': False,
            'default': "'default_value'"
        }
    ]
)

# 重命名列（通过表重建）
success = migration_manager.rename_column(
    table_name='filter_rules',
    old_name='old_column',
    new_name='new_column'
)
```

### 2. 迁移运行器 (`migration_runner.py`)

提供完整的迁移管理：
- **自动发现迁移文件** - 扫描migrations目录
- **版本控制** - 跟踪已应用的迁移
- **顺序执行** - 按文件名顺序执行迁移
- **回滚支持** - 支持迁移的回滚操作
- **进度报告** - 实时迁移进度通知

#### 使用方法：

```python
# 运行所有待应用的迁移
from backend.app.core.migration_runner import run_migrations

results = await run_migrations(
    database_url="sqlite:///./data/tggod.db",
    migrations_dir="./backend/migrations"
)
```

### 3. 修复的迁移脚本

现有的`add_rule_sync_tracking.py`迁移脚本已经修复：

**升级操作 (upgrade):**
- 使用标准的 ALTER TABLE ADD COLUMN
- 创建必要的索引

**降级操作 (downgrade):**
- 使用SQLite迁移管理器的表重建功能
- 安全删除添加的列和索引

## 使用示例

### 运行迁移测试

```bash
# 运行完整的迁移功能测试
python3 test_sqlite_migration.py
```

### 在应用中集成

```python
# 在应用启动时运行迁移
from backend.app.core.migration_runner import MigrationRunner

async def run_database_migrations():
    runner = MigrationRunner(
        database_url=settings.DATABASE_URL,
        migrations_dir="./backend/migrations"
    )

    results = await runner.run_all_migrations()

    if results['success']:
        logger.info(f"迁移完成: {results['applied_count']} 个成功")
    else:
        logger.error(f"迁移失败: {results['failed_migrations']}")
```

### 创建新的迁移文件

```python
# 例如: 002_add_new_features.py
"""添加新功能的迁移"""

import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

def upgrade():
    """升级操作"""
    try:
        with engine.connect() as conn:
            # 添加新列
            conn.execute(text("""
                ALTER TABLE filter_rules
                ADD COLUMN new_feature_flag BOOLEAN DEFAULT FALSE
            """))

            # 创建新索引
            conn.execute(text("""
                CREATE INDEX idx_filter_rules_new_feature
                ON filter_rules(new_feature_flag)
            """))

            conn.commit()
            logger.info("✅ 新功能迁移应用成功")

    except Exception as e:
        logger.error(f"❌ 新功能迁移失败: {e}")
        raise

def downgrade():
    """降级操作"""
    try:
        # 删除索引
        with engine.connect() as conn:
            conn.execute(text("DROP INDEX IF EXISTS idx_filter_rules_new_feature"))
            conn.commit()

        # 使用迁移管理器删除列
        success = migration_manager.rebuild_table_drop_columns(
            'filter_rules',
            ['new_feature_flag']
        )

        if not success:
            raise Exception("删除新功能列失败")

        logger.info("✅ 新功能迁移回滚成功")

    except Exception as e:
        logger.error(f"❌ 新功能迁移回滚失败: {e}")
        raise
```

## 安全特性

1. **自动备份**: 每次表重建前都会创建完整的数据库备份
2. **完整性验证**: 操作后验证数据完整性和行数一致性
3. **事务支持**: 失败时自动回滚到操作前状态
4. **错误恢复**: 从备份自动恢复数据库
5. **详细日志**: 完整的操作日志和错误信息

## 性能考虑

1. **表重建开销**: DROP COLUMN操作需要重建整个表，对大表可能耗时较长
2. **备份空间**: 每次操作都会创建备份，需要足够的磁盘空间
3. **索引重建**: 索引和触发器需要重新创建，会有额外开销

## 故障排除

### 常见问题

1. **磁盘空间不足**
   - 清理旧备份：`migration_manager.cleanup_old_backups(keep_count=5)`
   - 检查可用空间

2. **迁移文件错误**
   - 检查迁移文件语法
   - 确保upgrade/downgrade函数存在

3. **数据库锁定**
   - 确保没有其他连接占用数据库
   - 检查SQLite WAL模式配置

### 调试技巧

```python
# 获取迁移历史
history = runner.get_migration_history()
for record in history:
    print(f"{record['filename']}: {record['success']}")

# 获取迁移管理器信息
info = migration_manager.get_migration_info()
print(f"SQLite版本: {info['sqlite_version']}")
print(f"表数量: {info['table_count']}")
```

## 测试结果

所有测试已通过：
- ✅ DROP COLUMN功能测试
- ✅ 备份和恢复功能测试
- ✅ 迁移运行器测试
- ✅ 数据完整性验证测试

TgGod项目现在完全支持SQLite的所有DDL操作，包括之前不支持的DROP COLUMN。迁移系统提供了企业级的安全性和可靠性保证。