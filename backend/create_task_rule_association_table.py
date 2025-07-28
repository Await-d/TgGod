#!/usr/bin/env python3
"""
创建任务-规则关联表的数据库迁移脚本
"""
import os
import sys
import sqlite3
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_task_rule_association_table():
    """创建任务规则关联表并迁移现有数据"""
    db_path = "/app/data/tggod.db"
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查关联表是否已存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='task_rule_associations'
        """)
        
        association_table_exists = cursor.fetchone() is not None
        
        # 检查download_tasks表是否还有rule_id字段
        cursor.execute("PRAGMA table_info(download_tasks)")
        columns = [col[1] for col in cursor.fetchall()]
        rule_id_exists = 'rule_id' in columns
        
        if association_table_exists and not rule_id_exists:
            logger.info("task_rule_associations 表已存在且 rule_id 字段已移除，跳过迁移")
            conn.close()
            return True
        
        # 创建关联表（如果不存在）
        if not association_table_exists:
            logger.info("创建 task_rule_associations 表...")
            
            cursor.execute("""
                CREATE TABLE task_rule_associations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    rule_id INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    priority INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES download_tasks (id) ON DELETE CASCADE,
                    FOREIGN KEY (rule_id) REFERENCES filter_rules (id) ON DELETE CASCADE,
                    UNIQUE(task_id, rule_id)
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX idx_task_rule_task_id ON task_rule_associations(task_id)")
            cursor.execute("CREATE INDEX idx_task_rule_rule_id ON task_rule_associations(rule_id)")
            cursor.execute("CREATE INDEX idx_task_rule_active ON task_rule_associations(is_active)")
            
            logger.info("✅ task_rule_associations 表创建成功")
        else:
            logger.info("task_rule_associations 表已存在，跳过创建")
        
        # 迁移现有数据：从 download_tasks 表的 rule_id 字段迁移到关联表
        logger.info("检查是否需要迁移现有数据...")
        
        if rule_id_exists:
            logger.info("发现 rule_id 字段，开始迁移数据...")
            
            # 查询所有有 rule_id 的任务
            cursor.execute("""
                SELECT id, rule_id FROM download_tasks 
                WHERE rule_id IS NOT NULL
            """)
            tasks_with_rules = cursor.fetchall()
            
            # 插入到关联表
            for task_id, rule_id in tasks_with_rules:
                cursor.execute("""
                    INSERT OR IGNORE INTO task_rule_associations (task_id, rule_id, is_active, priority)
                    VALUES (?, ?, 1, 0)
                """, (task_id, rule_id))
            
            logger.info(f"✅ 成功迁移 {len(tasks_with_rules)} 条任务-规则关联记录")
            
            # 获取当前表的所有字段（除了rule_id）
            logger.info("获取原表结构...")
            existing_columns = [col[1] for col in cursor.execute("PRAGMA table_info(download_tasks)").fetchall() if col[1] != 'rule_id']
            
            # 创建新的下载任务表（不包含rule_id字段）
            logger.info("重建 download_tasks 表以移除 rule_id 字段...")
            
            # 备份原表
            cursor.execute("ALTER TABLE download_tasks RENAME TO download_tasks_backup")
            
            # 动态构建新表的CREATE语句
            create_sql = """
                CREATE TABLE download_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    group_id INTEGER NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    progress INTEGER DEFAULT 0,
                    total_messages INTEGER DEFAULT 0,
                    downloaded_messages INTEGER DEFAULT 0,
                    download_path VARCHAR(500) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """
            
            # 添加其他可能存在的字段
            optional_fields = [
                ("use_jellyfin_structure", "BOOLEAN DEFAULT 0"),
                ("include_metadata", "BOOLEAN DEFAULT 1"),
                ("download_thumbnails", "BOOLEAN DEFAULT 1"),
                ("use_series_structure", "BOOLEAN DEFAULT 0"),
                ("organize_by_date", "BOOLEAN DEFAULT 1"),
                ("max_filename_length", "INTEGER DEFAULT 150"),
                ("thumbnail_size", "VARCHAR(20) DEFAULT '400x300'"),
                ("poster_size", "VARCHAR(20) DEFAULT '600x900'"),
                ("fanart_size", "VARCHAR(20) DEFAULT '1920x1080'"),
                ("date_from", "TIMESTAMP"),
                ("date_to", "TIMESTAMP"),
                ("updated_at", "TIMESTAMP"),
                ("completed_at", "TIMESTAMP"),
                ("error_message", "TEXT"),
                ("task_type", "VARCHAR(20) DEFAULT 'once'"),
                ("schedule_type", "VARCHAR(20)"),
                ("schedule_config", "TEXT"),
                ("next_run_time", "TIMESTAMP"),
                ("last_run_time", "TIMESTAMP"),
                ("is_active", "BOOLEAN DEFAULT 1"),
                ("max_runs", "INTEGER"),
                ("run_count", "INTEGER DEFAULT 0")
            ]
            
            for field_name, field_def in optional_fields:
                if field_name in existing_columns:
                    create_sql += f",\n                    {field_name} {field_def}"
            
            create_sql += ",\n                    FOREIGN KEY (group_id) REFERENCES telegram_groups (id)\n                )"
            
            cursor.execute(create_sql)
            
            # 动态构建SELECT字段列表（排除rule_id）
            select_fields = [col for col in existing_columns if col != 'rule_id']
            select_sql = f"""
                INSERT INTO download_tasks ({', '.join(select_fields)})
                SELECT {', '.join(select_fields)}
                FROM download_tasks_backup
            """
            
            cursor.execute(select_sql)
            
            # 删除备份表
            cursor.execute("DROP TABLE download_tasks_backup")
            
            logger.info("✅ download_tasks 表重建完成，rule_id 字段已移除")
        
        conn.commit()
        conn.close()
        
        logger.info("🎉 任务-规则关联表创建和数据迁移完成")
        return True
        
    except Exception as e:
        logger.error(f"创建关联表失败: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    logger.info("开始执行任务-规则关联表创建脚本...")
    success = create_task_rule_association_table()
    
    if success:
        logger.info("✅ 脚本执行成功")
        sys.exit(0)
    else:
        logger.error("❌ 脚本执行失败")
        sys.exit(1)