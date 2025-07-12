#!/bin/bash

# TgGod Telegram API 配置脚本
# 用于快速配置Telegram API ID和API Hash

echo "============================================================"
echo "TgGod Telegram API 配置向导"
echo "============================================================"
echo ""

# 检查数据库文件
DB_PATH="/app/data/tggod.db"
if [ ! -f "$DB_PATH" ]; then
    DB_PATH="./data/tggod.db"
    if [ ! -f "$DB_PATH" ]; then
        echo "❌ 错误: 数据库文件不存在"
        echo "请先启动TgGod主程序以创建数据库"
        exit 1
    fi
fi

echo "✅ 找到数据库文件: $DB_PATH"
echo ""

# 检查当前配置
echo "📋 当前配置:"
sqlite3 "$DB_PATH" "SELECT key, CASE WHEN value = '' THEN '未设置' ELSE '已设置' END FROM system_config WHERE key IN ('telegram_api_id', 'telegram_api_hash');"
echo ""

# 询问是否要更新配置
read -p "是否要更新Telegram API配置? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "配置未更改"
    exit 0
fi

echo ""
echo "📖 获取Telegram API配置:"
echo "1. 访问 https://my.telegram.org"
echo "2. 使用您的手机号登录"
echo "3. 点击 'API development tools'"
echo "4. 填写应用信息创建新应用"
echo "5. 获取 API ID 和 API Hash"
echo ""

# 输入API ID
while true; do
    read -p "请输入 API ID: " api_id
    if [[ "$api_id" =~ ^[0-9]+$ ]]; then
        break
    else
        echo "❌ API ID必须是数字，请重新输入"
    fi
done

# 输入API Hash
while true; do
    read -p "请输入 API Hash: " api_hash
    if [[ ${#api_hash} -eq 32 ]]; then
        break
    else
        echo "❌ API Hash应该是32位字符串，请重新输入"
    fi
done

echo ""
echo "🔄 更新配置中..."

# 更新数据库配置
sqlite3 "$DB_PATH" <<EOF
UPDATE system_config SET value='$api_id' WHERE key='telegram_api_id';
UPDATE system_config SET value='$api_hash' WHERE key='telegram_api_hash';
EOF

if [ $? -eq 0 ]; then
    echo "✅ 配置更新成功!"
    echo ""
    echo "📋 新配置:"
    sqlite3 "$DB_PATH" "SELECT key, CASE WHEN key='telegram_api_hash' THEN '已设置 (隐藏)' ELSE value END FROM system_config WHERE key IN ('telegram_api_id', 'telegram_api_hash');"
    echo ""
    echo "🔄 请重启TgGod程序以应用新配置"
    echo ""
    echo "💡 提示:"
    echo "- 如果这是首次配置，程序启动时可能需要进行手机验证"
    echo "- 媒体下载功能现在应该可以正常工作了"
else
    echo "❌ 配置更新失败"
    exit 1
fi

echo ""
echo "============================================================"
echo "配置完成!"
echo "============================================================"