#!/usr/bin/env python3
import sqlite3
import os

db_path = "/app/data/tggod.db"

if os.path.exists(db_path):
    print(f"数据库文件存在: {db_path}")
    print(f"文件大小: {os.path.getsize(db_path)} bytes")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"数据库中的表: {[table[0] for table in tables]}")
    
    # 如果有telegram_groups表，检查数据
    if any('telegram_groups' in table[0] for table in tables):
        cursor.execute("SELECT COUNT(*) FROM telegram_groups")
        count = cursor.fetchone()[0]
        print(f"telegram_groups表中的记录数: {count}")
        
        if count > 0:
            cursor.execute("SELECT id, telegram_id, title FROM telegram_groups LIMIT 5")
            records = cursor.fetchall()
            print("前5条记录:")
            for record in records:
                print(f"  ID: {record[0]}, telegram_id: {record[1]}, title: {record[2]}")
    
    conn.close()
else:
    print(f"数据库文件不存在: {db_path}")