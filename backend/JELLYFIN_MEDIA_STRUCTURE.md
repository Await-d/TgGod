# Jellyfin 兼容的媒体文件结构设计

## 文件组织结构

### 基本结构
```
[下载根目录]/
├── [群组名称或频道名]/
│   ├── [视频标题] - [YYYY-MM-DD]/
│   │   ├── [视频标题].mp4           # 主视频文件
│   │   ├── [视频标题].nfo           # NFO元数据文件
│   │   ├── poster.jpg              # 封面图(竖版)
│   │   ├── fanart.jpg              # 背景图(横版)
│   │   ├── thumb.jpg               # 缩略图
│   │   └── [视频标题].srt          # 字幕文件(如果有)
│   └── [另一个视频] - [YYYY-MM-DD]/
│       └── ...
└── [另一个群组]/
    └── ...
```

### 命名规范

#### 1. 群组/频道目录名
- 使用群组/频道的标题
- 去除非法字符：`< > : " | ? * \ /`
- 限制长度为100字符
- 示例：`TechNews频道`, `电影分享群`

#### 2. 视频目录名
- 格式：`[视频标题] - [YYYY-MM-DD]`
- 视频标题：使用消息文本或媒体文件名
- 日期：消息发送日期
- 去除非法字符，限制长度为150字符
- 示例：`最新科技新闻 - 2025-07-25`, `经典电影分享 - 2025-07-25`

#### 3. 文件命名
- 视频文件：`[视频标题].{原始扩展名}`
- NFO文件：`[视频标题].nfo`
- 封面图：`poster.jpg` (竖版，适合海报)
- 背景图：`fanart.jpg` (横版，适合背景)
- 缩略图：`thumb.jpg` (小尺寸预览图)

## NFO 文件内容

### 视频 NFO 结构 (基于 Kodi/Jellyfin 标准)
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<movie>
    <title>视频标题</title>
    <plot>视频描述/消息内容</plot>
    <year>2025</year>
    <premiered>2025-07-25</premiered>
    <dateadded>2025-07-25 10:30:00</dateadded>
    <genre>Telegram</genre>
    <studio>群组/频道名称</studio>
    <director>发送者</director>
    <runtime>视频时长(分钟)</runtime>
    <thumb>poster.jpg</thumb>
    <fanart>fanart.jpg</fanart>
    <source>
        <name>Telegram</name>
        <url>t.me/群组名</url>
    </source>
    <telegram>
        <message_id>123456</message_id>
        <sender_id>789012</sender_id>
        <sender_name>发送者姓名</sender_name>
        <group_id>345678</group_id>
        <group_name>群组名称</group_name>
        <forward_info>
            <from>原始发送者</from>
            <date>2025-07-25</date>
        </forward_info>
    </telegram>
</movie>
```

## 配置选项

### 任务规则新增字段
- `use_jellyfin_structure`: 是否使用Jellyfin格式 (Boolean, 默认false)
- `jellyfin_library_path`: Jellyfin媒体库根路径 (String)
- `include_metadata`: 是否生成NFO文件 (Boolean, 默认true)
- `download_thumbnails`: 是否下载缩略图 (Boolean, 默认true)
- `organize_by_date`: 是否按日期组织 (Boolean, 默认true)

### 文件处理选项
- `max_filename_length`: 最大文件名长度 (默认150)
- `thumbnail_size`: 缩略图尺寸 (默认400x300)
- `poster_size`: 海报图尺寸 (默认600x900)
- `fanart_size`: 背景图尺寸 (默认1920x1080)

## 实现要点

1. **目录安全性**：确保目录名不包含非法字符
2. **重复处理**：相同标题+日期的内容添加序号后缀
3. **图片处理**：自动调整图片尺寸和格式
4. **元数据提取**：从Telegram消息中提取完整信息
5. **向后兼容**：现有的简单保存方式仍然可用

## 扩展性

- 支持剧集/系列的季度组织
- 支持多语言字幕文件
- 支持章节信息 (如果视频有分段)
- 支持演员信息 (如果消息中提到)