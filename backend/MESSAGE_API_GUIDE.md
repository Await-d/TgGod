# TgGod 群消息查看和发送功能使用说明

## 功能概述

TgGod 现已支持完整的群消息查看和发送功能，包括：

### 消息查看功能
- 📖 **消息列表查看** - 支持分页、搜索和过滤
- 🔍 **消息搜索** - 支持关键词、发送者、媒体类型等多维度搜索
- 💬 **消息回复查看** - 查看消息的回复链
- 📊 **群组统计** - 查看群组消息统计信息
- 📱 **消息详情** - 查看单条消息的完整信息

### 消息发送功能
- ✍️ **发送消息** - 向群组发送文本消息
- 💬 **回复消息** - 回复特定消息
- 🗑️ **删除消息** - 删除已发送的消息
- 📌 **置顶消息** - 消息置顶功能（服务端已实现）

## API 端点

### 🔐 认证要求
所有API端点都需要JWT认证，请先登录获取token：

```bash
# 登录获取token
curl -X POST "http://localhost:8000/api/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=admin123"
```

### 📋 消息查看API

#### 1. 获取群组消息列表

```bash
# 基础查看
curl -X GET "http://localhost:8000/api/telegram/groups/1/messages" \
     -H "Authorization: Bearer YOUR_TOKEN"

# 带搜索和过滤
curl -X GET "http://localhost:8000/api/telegram/groups/1/messages?search=hello&sender_username=user1&has_media=true&limit=50" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

**支持的查询参数：**
- `skip` - 跳过的记录数（分页）
- `limit` - 返回的记录数（最大1000）
- `search` - 搜索消息内容
- `sender_username` - 按发送者用户名过滤
- `media_type` - 按媒体类型过滤 (photo, video, document, audio)
- `has_media` - 是否包含媒体文件
- `is_forwarded` - 是否为转发消息
- `start_date` - 开始日期
- `end_date` - 结束日期

#### 2. 获取单条消息详情

```bash
curl -X GET "http://localhost:8000/api/telegram/groups/1/messages/12345" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

#### 3. 获取消息回复

```bash
curl -X GET "http://localhost:8000/api/telegram/groups/1/messages/12345/replies" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

#### 4. 高级搜索

```bash
curl -X POST "http://localhost:8000/api/telegram/groups/1/messages/search" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "重要通知",
       "sender_username": "admin",
       "media_type": "photo",
       "start_date": "2025-01-01T00:00:00Z",
       "end_date": "2025-12-31T23:59:59Z"
     }'
```

### 💬 消息发送API

#### 1. 发送消息

```bash
curl -X POST "http://localhost:8000/api/telegram/groups/1/send" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "text": "Hello, World!",
       "reply_to_message_id": null
     }'
```

#### 2. 回复消息

```bash
curl -X POST "http://localhost:8000/api/telegram/groups/1/messages/12345/reply" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "text": "Thanks for the message!"
     }'
```

#### 3. 删除消息

```bash
curl -X DELETE "http://localhost:8000/api/telegram/groups/1/messages/12345" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

### 📊 统计信息API

#### 获取群组统计

```bash
curl -X GET "http://localhost:8000/api/telegram/groups/1/stats" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

**返回信息：**
```json
{
  "total_messages": 1500,
  "media_messages": 300,
  "text_messages": 1200,
  "member_count": 50
}
```

## 消息字段说明

### 完整消息对象

```json
{
  "id": 1,
  "group_id": 1,
  "message_id": 12345,
  "sender_id": 98765,
  "sender_username": "user1",
  "sender_name": "John Doe",
  "text": "Hello, World!",
  "media_type": "photo",
  "media_path": "/media/photo_123.jpg",
  "media_size": 1024000,
  "media_filename": "image.jpg",
  "view_count": 10,
  "is_forwarded": false,
  "forwarded_from": null,
  "reply_to_message_id": 12340,
  "edit_date": "2025-07-09T10:00:00Z",
  "is_pinned": false,
  "reactions": {"👍": 5, "❤️": 3},
  "mentions": ["@user2", "@user3"],
  "hashtags": ["#important", "#news"],
  "urls": ["https://example.com"],
  "date": "2025-07-09T09:00:00Z",
  "created_at": "2025-07-09T09:00:00Z",
  "updated_at": "2025-07-09T09:05:00Z"
}
```

### 关键字段说明

- **reply_to_message_id** - 回复的消息ID
- **edit_date** - 消息编辑时间
- **is_pinned** - 是否置顶
- **reactions** - 消息反应（点赞等）
- **mentions** - 提及的用户列表
- **hashtags** - 话题标签列表
- **urls** - 消息中的链接列表

## 使用示例

### 1. 查看最新消息

```bash
# 获取最新50条消息
curl -X GET "http://localhost:8000/api/telegram/groups/1/messages?limit=50" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. 搜索包含图片的消息

```bash
# 搜索包含图片的消息
curl -X GET "http://localhost:8000/api/telegram/groups/1/messages?media_type=photo&limit=20" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. 发送带回复的消息

```bash
# 回复特定消息
curl -X POST "http://localhost:8000/api/telegram/groups/1/send" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "text": "收到，谢谢！",
       "reply_to_message_id": 12345
     }'
```

### 4. 搜索用户的所有消息

```bash
# 搜索特定用户的所有消息
curl -X GET "http://localhost:8000/api/telegram/groups/1/messages?sender_username=admin&limit=100" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

## 错误处理

### 常见错误代码

- `401` - 未授权，需要登录
- `404` - 群组或消息不存在
- `500` - 服务器内部错误

### 错误响应格式

```json
{
  "detail": "群组不存在"
}
```

## 注意事项

1. **认证要求** - 所有API都需要JWT认证
2. **速率限制** - 建议适当控制请求频率
3. **权限管理** - 确保用户有相应的群组访问权限
4. **数据同步** - 新消息需要通过同步API获取
5. **媒体文件** - 媒体文件需要单独下载

## 技术实现

### 新增功能
- ✅ 扩展消息模型支持更多字段
- ✅ 实现消息搜索和过滤
- ✅ 添加消息发送和回复功能
- ✅ 集成用户权限验证
- ✅ 支持消息分页和排序
- ✅ 添加消息类型处理

### 数据库变更
- 新增消息扩展字段：reply_to_message_id, edit_date, is_pinned, reactions, mentions, hashtags, urls
- 更新消息模型以支持更丰富的数据结构

### 安全特性
- JWT认证保护所有端点
- 用户权限验证
- 输入验证和过滤
- 错误处理和日志记录

现在您可以使用这些API来构建完整的群消息管理功能！