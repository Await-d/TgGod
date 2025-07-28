"""任务规则关联模型"""
from sqlalchemy import Column, Integer, ForeignKey, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class TaskRuleAssociation(Base):
    """任务规则关联表 - 多对多关系"""
    __tablename__ = "task_rule_associations"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("download_tasks.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(Integer, ForeignKey("filter_rules.id", ondelete="CASCADE"), nullable=False)
    
    # 关联配置
    is_active = Column(Boolean, default=True)  # 是否启用该规则
    priority = Column(Integer, default=0)  # 规则优先级 (数字越大优先级越高)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    task = relationship("DownloadTask", back_populates="rule_associations")
    rule = relationship("FilterRule", back_populates="task_associations")
    
    # 复合唯一约束
    __table_args__ = (
        {"schema": None}  # 确保在默认schema中
    )