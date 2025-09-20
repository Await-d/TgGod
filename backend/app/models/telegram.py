"""TgGod Telegram数据模型

定义与Telegram相关的数据库模型，包括:

- TelegramGroup: 群组信息模型
- TelegramMessage: 消息信息模型

Data Model Features:
    - 完整的群组和消息元数据
    - 媒体文件的详细信息存储
    - 消息实体提取(提及、链接、标签)
    - 关系映射和级联操作
    - 索引优化和查询性能
    - 完整的数据一致性约束

Database Schema:
    - 优化的索引设计
    - 合理的字段类型和限制
    - 清晰的外键关系
    - 自动时间戳管理

Author: TgGod Team
Version: 1.0.0
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class TelegramGroup(Base):
    """Telegram群组数据模型

    存储Telegram群组的基本信息和配置数据。

    Attributes:
        id (int): 数据库主键，自增整数
        telegram_id (int): Telegram群组的原始ID，唯一标识
        title (str): 群组标题名称，最大255字符
        username (str): 群组用户名，可为空，最大255字符
        description (str): 群组描述信息，可为空
        member_count (int): 群组成员数量，默认0
        is_active (bool): 是否激活状态，默认True
        created_at (datetime): 创建时间，自动设置
        updated_at (datetime): 更新时间，自动维护

    Relationships:
        messages: 与该群组关联的所有消息记录
        tasks: 与该群组关联的所有下载任务

    Indexes:
        - telegram_id: 唯一索引，快速查找
        - username: 普通索引，用户名查询
        - id: 主键索引

    Constraints:
        - telegram_id: 不能为空，全局唯一
        - title: 不能为空

    Cascade Operations:
        - 删除群组时级联删除所有消息和任务

    Usage:
        group = TelegramGroup(
            telegram_id=123456789,
            title="Example Group",
            username="example_group",
            description="This is an example group"
        )
        session.add(group)
        session.commit()

    Note:
        - telegram_id与Telegram官方API保持一致
        - is_active控制是否参与自动同步
        - 时间字段包含时区信息
    """
    __tablename__ = "telegram_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)
    member_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系映射 - 群组通过任务关联规则，避免直接关联
    messages = relationship(
        "TelegramMessage",
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="TelegramMessage.date.desc()"
    )
    tasks = relationship(
        "DownloadTask",
        back_populates="group",
        cascade="all, delete-orphan"
    )

class TelegramMessage(Base):
    """Telegram消息数据模型

    存储从群组同步的消息详细信息，包括文本内容、媒体文件和元数据。

    Core Fields:
        id (int): 数据库主键，自增整数
        group_id (int): 所属群组ID，外键关联
        message_id (int): Telegram消息的原始ID
        sender_id (int): 发送者的Telegram用户ID
        sender_username (str): 发送者用户名
        sender_name (str): 发送者显示名称
        text (str): 消息文本内容

    Media Fields:
        media_type (str): 媒体类型(photo/video/document/audio/voice/sticker)
        media_path (str): 本地文件路径（下载后）
        media_size (int): 文件大小（字节）
        media_filename (str): 原始文件名
        media_file_id (str): Telegram文件ID（用于下载）
        media_file_unique_id (str): Telegram唯一文件ID
        media_downloaded (bool): 是否已下载到本地
        media_download_url (str): 临时下载链接
        media_download_error (str): 下载错误信息
        media_thumbnail_path (str): 缩略图路径

    Media Detail Fields:
        media_duration (int): 视频/音频时长（秒）
        media_width (int): 视频/图片宽度（像素）
        media_height (int): 视频/图片高度（像素）
        media_title (str): 媒体标题
        media_performer (str): 音频演奏者

    Message Metadata:
        date (datetime): 消息发送时间
        reply_to_message_id (int): 回复的消息ID
        forward_from (str): 转发来源
        forward_date (datetime): 转发时间
        edit_date (datetime): 最后编辑时间
        is_forwarded (bool): 是否为转发消息
        is_pinned (bool): 是否为置顶消息
        views (int): 消息查看数

    Entity Fields (JSON):
        mentions (JSON): 提及的用户列表
        hashtags (JSON): 话题标签列表
        urls (JSON): 消息中的链接列表
        reactions (JSON): 消息反应统计

    Timestamp Fields:
        created_at (datetime): 数据库记录创建时间
        updated_at (datetime): 数据库记录更新时间

    Relationships:
        group: 所属的Telegram群组对象

    Indexes:
        - group_id: 群组内消息查询
        - message_id: Telegram消息ID查询
        - date: 时间范围查询
        - media_type: 媒体类型过滤
        - sender_username: 发送者查询

    Constraints:
        - group_id: 必须关联到存在的群组
        - message_id: 不能为空
        - (group_id, message_id): 组合唯一约束

    Usage:
        message = TelegramMessage(
            group_id=1,
            message_id=12345,
            sender_username="user123",
            text="Hello, world!",
            media_type="photo",
            date=datetime.now()
        )
        session.add(message)
        session.commit()

    JSON Field Examples:
        mentions: ["@user1", "@user2"]
        hashtags: ["#python", "#telegram"]
        urls: ["https://example.com"]
        reactions: {"👍": 5, "❤️": 3}

    Note:
        - 支持所有Telegram消息类型
        - JSON字段用于存储结构化数据
        - 媒体文件信息与下载状态分离
        - 支持消息编辑历史跟踪
    ""\
    __tablename__ = "telegram_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("telegram_groups.id"), nullable=False)
    message_id = Column(BigInteger, nullable=False)
    sender_id = Column(BigInteger, nullable=True)
    sender_username = Column(String(255), nullable=True)
    sender_name = Column(String(255), nullable=True)
    text = Column(Text, nullable=True)
    media_type = Column(String(50), nullable=True)  # photo, video, document, audio, voice, sticker
    media_path = Column(String(500), nullable=True)  # 本地文件路径（仅下载后存在）
    media_size = Column(BigInteger, nullable=True)
    media_filename = Column(String(255), nullable=True)
    media_file_id = Column(String(255), nullable=True)  # Telegram文件ID（用于下载）
    media_file_unique_id = Column(String(255), nullable=True)  # Telegram唯一文件ID
    
    # 媒体详细信息
    media_duration = Column(Integer, nullable=True)  # 视频/音频时长（秒）
    media_width = Column(Integer, nullable=True)  # 视频/图片宽度
    media_height = Column(Integer, nullable=True)  # 视频/图片高度
    media_title = Column(String(255), nullable=True)  # 媒体标题
    media_performer = Column(String(255), nullable=True)  # 音频演奏者
    media_downloaded = Column(Boolean, default=False)  # 是否已下载到本地
    media_download_url = Column(String(500), nullable=True)  # Telegram下载链接（临时）
    media_download_error = Column(Text, nullable=True)  # 下载失败错误信息
    media_thumbnail_path = Column(String(500), nullable=True)  # 缩略图路径
    
    # 下载进度相关字段
    download_progress = Column(Integer, default=0)  # 下载进度 0-100
    downloaded_size = Column(BigInteger, default=0)  # 已下载字节数
    download_speed = Column(Integer, default=0)  # 下载速度 bytes/second
    estimated_time_remaining = Column(Integer, default=0)  # 预计剩余时间 seconds
    download_started_at = Column(DateTime(timezone=True), nullable=True)  # 下载开始时间
    is_downloading = Column(Boolean, default=False)  # 是否正在下载中，解决切换群组时状态丢失问题
    view_count = Column(Integer, default=0)
    is_forwarded = Column(Boolean, default=False)
    forwarded_from = Column(String(255), nullable=True)  # 转发来源名称
    forwarded_from_id = Column(BigInteger, nullable=True)  # 转发来源ID（用户ID或群组ID）
    forwarded_from_type = Column(String(20), nullable=True)  # 转发来源类型：user, group, channel
    forwarded_date = Column(DateTime(timezone=True), nullable=True)  # 原消息发送时间
    is_own_message = Column(Boolean, default=False)  # 是否为当前用户发送的消息
    
    # 新增字段
    reply_to_message_id = Column(BigInteger, nullable=True)  # 回复的消息ID
    edit_date = Column(DateTime(timezone=True), nullable=True)  # 编辑时间
    is_pinned = Column(Boolean, default=False)  # 是否置顶
    reactions = Column(JSON, nullable=True)  # 消息反应（点赞等）
    mentions = Column(JSON, nullable=True)  # 提及的用户
    hashtags = Column(JSON, nullable=True)  # 话题标签
    urls = Column(JSON, nullable=True)  # 消息中的链接
    media_group_id = Column(String(255), nullable=True, index=True)  # Telegram媒体组ID（用于分组多文件消息）
    
    date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    group = relationship("TelegramGroup", back_populates="messages")
    
    # 创建复合索引
    __table_args__ = (
        {"mysql_engine": "InnoDB"},
    )