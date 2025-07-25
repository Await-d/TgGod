"""
下载历史相关的Pydantic模型
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class DownloadRecordBase(BaseModel):
    """下载记录基础模型"""
    task_id: int = Field(..., description="任务ID")
    file_name: str = Field(..., description="文件名")
    local_file_path: str = Field(..., description="本地文件路径")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    file_type: Optional[str] = Field(None, description="文件类型")
    message_id: int = Field(..., description="消息ID")
    sender_id: Optional[int] = Field(None, description="发送者ID")
    sender_name: Optional[str] = Field(None, description="发送者名称")
    message_date: Optional[datetime] = Field(None, description="消息发送时间")
    message_text: Optional[str] = Field(None, description="消息文本内容")

class DownloadRecordCreate(DownloadRecordBase):
    """创建下载记录的请求模型"""
    download_status: str = Field("completed", description="下载状态")
    download_progress: int = Field(100, description="下载进度")
    error_message: Optional[str] = Field(None, description="错误信息")
    download_started_at: Optional[datetime] = Field(None, description="下载开始时间")
    download_completed_at: Optional[datetime] = Field(None, description="下载完成时间")

class DownloadRecordResponse(DownloadRecordBase):
    """下载记录响应模型"""
    id: int = Field(..., description="记录ID")
    task_name: Optional[str] = Field(None, description="任务名称")
    group_name: Optional[str] = Field(None, description="群组名称")
    download_status: str = Field(..., description="下载状态")
    download_progress: int = Field(..., description="下载进度")
    error_message: Optional[str] = Field(None, description="错误信息")
    download_started_at: Optional[datetime] = Field(None, description="下载开始时间")
    download_completed_at: Optional[datetime] = Field(None, description="下载完成时间")

    class Config:
        from_attributes = True

class DownloadHistoryListResponse(BaseModel):
    """下载历史列表响应模型"""
    records: List[DownloadRecordResponse] = Field(..., description="下载记录列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")

class DownloadHistoryStatsResponse(BaseModel):
    """下载历史统计响应模型"""
    total_downloads: int = Field(..., description="总下载数量")
    successful_downloads: int = Field(..., description="成功下载数量")
    failed_downloads: int = Field(..., description="失败下载数量")
    success_rate: float = Field(..., description="成功率（百分比）")
    total_file_size: int = Field(..., description="总文件大小（字节）")
    file_types: Dict[str, int] = Field(..., description="按文件类型统计")
    top_tasks: List[Dict[str, Any]] = Field(..., description="下载量最多的任务")
    period_days: int = Field(..., description="统计期间天数")

class TaskDownloadSummary(BaseModel):
    """任务下载汇总信息"""
    task_name: str = Field(..., description="任务名称")
    download_count: int = Field(..., description="下载数量")

class BatchDeleteRequest(BaseModel):
    """批量删除请求模型"""
    record_ids: List[int] = Field(..., description="要删除的记录ID列表")

class BatchDeleteResponse(BaseModel):
    """批量删除响应模型"""
    message: str = Field(..., description="操作结果消息")
    deleted_count: int = Field(..., description="实际删除的记录数")
    requested_count: int = Field(..., description="请求删除的记录数")

class DownloadRecordFilter(BaseModel):
    """下载记录过滤条件"""
    task_id: Optional[int] = Field(None, description="任务ID")
    group_id: Optional[int] = Field(None, description="群组ID")
    file_type: Optional[str] = Field(None, description="文件类型")
    status: Optional[str] = Field(None, description="下载状态")
    date_from: Optional[datetime] = Field(None, description="开始日期")
    date_to: Optional[datetime] = Field(None, description="结束日期")
    search: Optional[str] = Field(None, description="搜索关键词")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页大小")

class FileTypeStats(BaseModel):
    """文件类型统计"""
    file_type: str = Field(..., description="文件类型")
    count: int = Field(..., description="数量")
    total_size: int = Field(..., description="总大小")
    percentage: float = Field(..., description="占比")

class DailyDownloadStats(BaseModel):
    """每日下载统计"""
    date: datetime = Field(..., description="日期")
    download_count: int = Field(..., description="下载数量")
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")
    total_size: int = Field(..., description="总大小")

class DetailedStatsResponse(BaseModel):
    """详细统计响应"""
    overview: DownloadHistoryStatsResponse = Field(..., description="概览统计")
    file_type_details: List[FileTypeStats] = Field(..., description="文件类型详细统计")
    daily_stats: List[DailyDownloadStats] = Field(..., description="每日统计")
    top_senders: List[Dict[str, Any]] = Field(..., description="发送者排行")
    largest_files: List[DownloadRecordResponse] = Field(..., description="最大文件列表")