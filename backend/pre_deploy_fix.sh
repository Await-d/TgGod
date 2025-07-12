#!/bin/bash
# 生产环境部署前数据库修复脚本

echo "=========================================="
echo "TgGod 生产环境数据库修复脚本"
echo "=========================================="

# 设置脚本在遇到错误时继续执行
set +e

# 进入项目目录
cd "$(dirname "$0")"

echo "当前目录: $(pwd)"

# 检查Python环境
echo "检查Python环境..."
python --version

# 检查数据库文件
if [ -f "tggod.db" ]; then
    echo "✅ 数据库文件存在: tggod.db"
else
    echo "⚠️  数据库文件不存在，将创建新数据库"
fi

# 运行强制修复脚本
echo ""
echo "运行转发消息字段强制修复..."
python force_fix_forwarded_columns.py

if [ $? -eq 0 ]; then
    echo "✅ 转发消息字段修复成功"
else
    echo "❌ 转发消息字段修复失败，但将继续部署"
fi

# 运行完整数据库检查
echo ""
echo "运行完整数据库检查..."
python check_database.py

if [ $? -eq 0 ]; then
    echo "✅ 数据库检查通过"
else
    echo "❌ 数据库检查失败，但将继续部署"
fi

# 检查关键字段是否存在
echo ""
echo "验证关键转发消息字段..."
python -c "
import sqlite3
try:
    conn = sqlite3.connect('tggod.db')
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(telegram_messages)')
    columns = [row[1] for row in cursor.fetchall()]
    
    required_fields = ['forwarded_from_id', 'forwarded_from_type', 'forwarded_date']
    missing = [field for field in required_fields if field not in columns]
    
    if missing:
        print(f'❌ 缺失字段: {missing}')
        exit(1)
    else:
        print('✅ 所有转发消息字段存在')
        exit(0)
        
except Exception as e:
    print(f'❌ 验证失败: {e}')
    exit(1)
finally:
    if 'conn' in locals():
        conn.close()
"

if [ $? -eq 0 ]; then
    echo "✅ 字段验证通过"
    FIELD_CHECK_PASSED=true
else
    echo "❌ 字段验证失败"
    FIELD_CHECK_PASSED=false
fi

echo ""
echo "=========================================="
echo "数据库修复完成报告"
echo "=========================================="

if [ "$FIELD_CHECK_PASSED" = true ]; then
    echo "✅ 所有转发消息字段正常，可以启动应用"
    exit 0
else
    echo "⚠️  转发消息字段可能存在问题，但应用仍可启动"
    echo "   应用启动时会尝试自动修复"
    exit 0
fi