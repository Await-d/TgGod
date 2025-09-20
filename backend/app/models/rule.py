"""TgGod 规则和任务数据模型

定义与过滤规则和下载任务相关的数据库模型，包括:

- FilterRule: 消息过滤规则模型，支持复杂的过滤条件
- DownloadTask: 下载任务模型，管理媒体下载的完整生命周期

Data Model Features:
    - 灵活的过滤条件配置(关键词、媒体类型、文件属性)
    - 完整的任务状态管理和进度跟踪
    - Jellyfin媒体库集成支持
    - 多对多任务-规则关联关系
    - 详细的同步状态和历史记录
    - 调度和自动化任务支持

Database Schema:
    - 优化的JSON字段存储复杂配置
    - 时区感知的时间戳字段
    - 适当的索引和外键约束
    - 级联删除和关系管理
    - 自动更新时间戳

Filter Rule Capabilities:
    - 关键词包含和排除逻辑
    - 媒体类型和文件大小过滤
    - 视频尺寸和时长限制
    - 消息元信息过滤(发送者、时间、状态)
    - 高级文本分析(URL、提及、标签)
    - 时间范围和年龄限制

Download Task Features:
    - 完整的任务生命周期管理
    - 实时进度监控和统计
    - 灵活的文件组织配置
    - Jellyfin媒体库自动化集成
    - 调度和重复执行支持
    - 详细的错误处理和日志

Author: TgGod Team
Version: 1.0.0
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class FilterRule(Base):
    """消息过滤规则数据模型

    定义复杂的消息过滤条件，支持多维度的消息筛选逻辑。
    规则可以被多个下载任务共享使用，提供灵活的过滤配置。

    Attributes:
        id (int): 规则唯一标识ID，主键
        name (str): 规则显示名称，最大255字符

        # 基础过滤条件
        keywords (JSON): 包含关键词列表，消息文本匹配
        exclude_keywords (JSON): 排除关键词列表，匹配则跳过
        sender_filter (JSON): 发送者用户名/ID过滤列表
        media_types (JSON): 媒体类型过滤['photo','video','audio','document']

        # 时间范围过滤
        date_from (DateTime): 消息时间范围开始，时区感知
        date_to (DateTime): 消息时间范围结束，时区感知

        # 数值范围过滤
        min_views (int): 最小查看次数
        max_views (int): 最大查看次数
        min_file_size (int): 最小文件大小(字节)
        max_file_size (int): 最大文件大小(字节)

        # 媒体属性过滤
        min_duration (int): 最小媒体时长(秒)
        max_duration (int): 最大媒体时长(秒)
        min_width (int): 最小视频宽度(像素)
        max_width (int): 最大视频宽度(像素)
        min_height (int): 最小视频高度(像素)
        max_height (int): 最大视频高度(像素)

        # 文本内容过滤
        min_text_length (int): 最小文本长度(字符)
        max_text_length (int): 最大文本长度(字符)

        # 高级内容过滤
        has_urls (bool): 是否包含URL链接
        has_mentions (bool): 是否包含@用户提及
        has_hashtags (bool): 是否包含#话题标签
        is_reply (bool): 是否为回复消息
        is_edited (bool): 是否为编辑后的消息
        is_pinned (bool): 是否为置顶消息

        # 时间相关过滤
        message_age_days (int): 消息年龄限制(天数内)
        exclude_weekends (bool): 是否排除周末消息，默认False
        time_range_start (str): 每日时间范围开始(HH:MM格式)
        time_range_end (str): 每日时间范围结束(HH:MM格式)

        # 消息类型过滤
        include_forwarded (bool): 是否包含转发消息，默认True
        is_active (bool): 规则是否激活，默认True

        # 同步状态跟踪
        last_sync_time (DateTime): 最后同步时间
        last_sync_message_count (int): 最后同步消息数量，默认0
        sync_status (str): 同步状态(pending/syncing/completed/failed)
        needs_full_resync (bool): 是否需要完全重新同步，默认True

        # 时间戳
        created_at (DateTime): 创建时间，自动设置
        updated_at (DateTime): 更新时间，自动维护

    Relationships:
        task_associations: 与任务的多对多关联关系
        tasks: 便捷属性，返回使用该规则的活跃任务列表

    Example:
        ```python
        rule = FilterRule(
            name="高清视频过滤",
            keywords=["1080p", "高清"],
            media_types=["video"],
            min_file_size=50*1024*1024,  # 50MB
            min_width=1920,
            min_height=1080
        )
        ```

    Note:
        - JSON字段支持复杂的列表和对象配置
        - 所有过滤条件支持空值，表示不限制
        - 多个条件之间为AND关系
        - 支持正则表达式匹配(在keywords中)
    """
    __tablename__ = "filter_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    # 移除群组关联 - 群组关联现在由任务管理
    
    # 过滤条件
    keywords = Column(JSON, nullable=True)  # 包含关键词列表
    exclude_keywords = Column(JSON, nullable=True)  # 排除关键词列表
    sender_filter = Column(JSON, nullable=True)  # 发送者过滤列表
    media_types = Column(JSON, nullable=True)  # 媒体类型过滤列表
    
    # 时间过滤
    date_from = Column(DateTime(timezone=True), nullable=True)
    date_to = Column(DateTime(timezone=True), nullable=True)
    
    # 数值过滤
    min_views = Column(Integer, nullable=True)
    max_views = Column(Integer, nullable=True)
    
    # 文件大小过滤（字节）
    min_file_size = Column(Integer, nullable=True)  # 最小文件大小
    max_file_size = Column(Integer, nullable=True)  # 最大文件大小
    
    # 视频/音频时长过滤（秒）
    min_duration = Column(Integer, nullable=True)  # 最小时长
    max_duration = Column(Integer, nullable=True)  # 最大时长
    
    # 视频尺寸过滤（像素）
    min_width = Column(Integer, nullable=True)  # 最小宽度
    max_width = Column(Integer, nullable=True)  # 最大宽度
    min_height = Column(Integer, nullable=True)  # 最小高度
    max_height = Column(Integer, nullable=True)  # 最大高度
    
    # 文本长度过滤（字符数）
    min_text_length = Column(Integer, nullable=True)  # 最小文本长度
    max_text_length = Column(Integer, nullable=True)  # 最大文本长度
    
    # 高级过滤选项
    has_urls = Column(Boolean, nullable=True)  # 是否包含链接
    has_mentions = Column(Boolean, nullable=True)  # 是否包含@提及
    has_hashtags = Column(Boolean, nullable=True)  # 是否包含#话题
    is_reply = Column(Boolean, nullable=True)  # 是否为回复消息
    is_edited = Column(Boolean, nullable=True)  # 是否为编辑过的消息
    is_pinned = Column(Boolean, nullable=True)  # 是否为置顶消息
    
    # 时间相关过滤
    message_age_days = Column(Integer, nullable=True)  # 消息年龄（天数内）
    exclude_weekends = Column(Boolean, default=False)  # 排除周末消息
    time_range_start = Column(String(5), nullable=True)  # 时间范围开始（HH:MM格式）
    time_range_end = Column(String(5), nullable=True)  # 时间范围结束（HH:MM格式）
    
    # 其他选项
    include_forwarded = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    # 同步跟踪字段
    last_sync_time = Column(DateTime(timezone=True), nullable=True)  # 最后同步时间
    last_sync_message_count = Column(Integer, default=0)  # 最后同步的消息数量
    sync_status = Column(String(20), default='pending')  # 同步状态: pending, syncing, completed, failed
    needs_full_resync = Column(Boolean, default=True)  # 是否需要完全重新同步
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系 - 移除与群组的直接关联
    task_associations = relationship("TaskRuleAssociation", back_populates="rule", cascade="all, delete-orphan")
    
    # 便捷属性：获取所有使用该规则的任务
    @property
    def tasks(self):
        return [assoc.task for assoc in self.task_associations if assoc.is_active]

class DownloadTask(Base):
    __tablename__ = "download_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    group_id = Column(Integer, ForeignKey("telegram_groups.id"), nullable=False)
    # rule_id 字段已移除，改用多对多关联
    
    # 任务状态
    status = Column(String(50), default="pending")  # pending, running, completed, failed, paused
    progress = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    downloaded_messages = Column(Integer, default=0)
    
    # 下载配置
    download_path = Column(String(500), nullable=False)
    
    # Jellyfin 兼容配置
    use_jellyfin_structure = Column(Boolean, default=False)  # 是否使用Jellyfin格式
    include_metadata = Column(Boolean, default=True)  # 是否生成NFO文件
    download_thumbnails = Column(Boolean, default=True)  # 是否下载缩略图
    use_series_structure = Column(Boolean, default=False)  # 是否使用剧集结构
    organize_by_date = Column(Boolean, default=True)  # 是否按日期组织
    max_filename_length = Column(Integer, default=150)  # 最大文件名长度
    
    # 图片尺寸配置 (存储为 "宽x高" 格式)
    thumbnail_size = Column(String(20), default="400x300")  # 缩略图尺寸
    poster_size = Column(String(20), default="600x900")  # 海报图尺寸
    fanart_size = Column(String(20), default="1920x1080")  # 背景图尺寸
    
    # 时间范围过滤（用于下载任务的时间筛选）
    date_from = Column(DateTime(timezone=True), nullable=True)  # 开始时间
    date_to = Column(DateTime(timezone=True), nullable=True)    # 结束时间
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    
    # 调度配置
    task_type = Column(String(20), default='once')  # 任务类型: once, recurring
    schedule_type = Column(String(20), nullable=True)  # 调度类型: interval, cron, daily, weekly, monthly
    schedule_config = Column(JSON, nullable=True)  # 调度配置 JSON
    next_run_time = Column(DateTime(timezone=True), nullable=True)  # 下次执行时间
    last_run_time = Column(DateTime(timezone=True), nullable=True)  # 最后执行时间
    is_active = Column(Boolean, default=True)  # 是否启用调度
    max_runs = Column(Integer, nullable=True)  # 最大执行次数 (None表示无限制)
    run_count = Column(Integer, default=0)  # 已执行次数
    
    # 关系
    group = relationship("TelegramGroup", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")
    download_records = relationship("DownloadRecord", back_populates="task", cascade="all, delete-orphan")
    
    # 多对多关系：任务关联的规则
    rule_associations = relationship("TaskRuleAssociation", back_populates="task", cascade="all, delete-orphan")
    
    # 便捷属性：获取所有关联的规则
    @property
    def rules(self):
        return [assoc.rule for assoc in self.rule_associations if assoc.is_active]

class DownloadRecord(Base):
    """下载记录模型 - 记录每个具体下载的文件"""
    __tablename__ = "download_records"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("download_tasks.id"), nullable=False)
    
    # 文件信息
    file_name = Column(String(500), nullable=False)  # 原始文件名
    local_file_path = Column(String(1000), nullable=False)  # 本地存储路径
    file_size = Column(Integer, nullable=True)  # 文件大小（字节）
    file_type = Column(String(50), nullable=True)  # 文件类型（photo, video, document等）
    
    # Telegram消息信息
    message_id = Column(Integer, nullable=False)  # 消息ID
    sender_id = Column(Integer, nullable=True)  # 发送者ID
    sender_name = Column(String(255), nullable=True)  # 发送者名称
    message_date = Column(DateTime(timezone=True), nullable=True)  # 消息发送时间
    message_text = Column(Text, nullable=True)  # 消息文本内容
    
    # 下载状态
    download_status = Column(String(50), default="completed")  # completed, failed, partial
    download_progress = Column(Integer, default=100)  # 下载进度 0-100
    error_message = Column(Text, nullable=True)  # 错误信息
    
    # 时间戳
    download_started_at = Column(DateTime(timezone=True), nullable=True)  # 下载开始时间
    download_completed_at = Column(DateTime(timezone=True), server_default=func.now())  # 下载完成时间
    
    # 关系
    task = relationship("DownloadTask", back_populates="download_records")
