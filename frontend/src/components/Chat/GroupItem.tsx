import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Avatar, Badge, Tag, Tooltip } from 'antd';
import { 
  TeamOutlined, 
  CheckCircleOutlined, 
  PauseCircleOutlined,
  PushpinOutlined
} from '@ant-design/icons';
import { GroupListItemProps } from '../../types/chat';
import { telegramApi } from '../../services/apiService';

const GroupItem: React.FC<GroupListItemProps> = ({
  group,
  isSelected,
  onClick,
  unreadCount = 0,
  lastMessageTime,

}) => {
  const [groupStats, setGroupStats] = useState<any>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [statsLoaded, setStatsLoaded] = useState(false);
  const elementRef = useRef<HTMLDivElement>(null);
  
  // 懒加载统计信息的函数
  const fetchGroupStats = useCallback(async () => {
    if (!group.id || statsLoaded || loadingStats) return;
    
    setLoadingStats(true);
    try {
      const stats = await telegramApi.getGroupStats(group.id);
      setGroupStats(stats);
      setStatsLoaded(true);
    } catch (error) {
      // 静默失败，不影响基本功能
    } finally {
      setLoadingStats(false);
    }
  }, [group.id, statsLoaded, loadingStats]);

  // 使用Intersection Observer实现懒加载
  useEffect(() => {
    const currentElement = elementRef.current;
    
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsVisible(true);
            // 当元素可见时加载统计信息
            if (!statsLoaded && !loadingStats) {
              fetchGroupStats();
            }
          }
        });
      },
      {
        threshold: 0.1, // 10%可见时触发
        rootMargin: '50px' // 提前50px开始加载
      }
    );

    if (currentElement) {
      observer.observe(currentElement);
    }

    return () => {
      if (currentElement) {
        observer.unobserve(currentElement);
      }
      observer.disconnect();
    };
  }, [fetchGroupStats, statsLoaded, loadingStats]);

  // 当群组被选中时立即加载统计（如果还没加载）
  useEffect(() => {
    if (isSelected && !statsLoaded && !loadingStats) {
      fetchGroupStats();
    }
  }, [isSelected, fetchGroupStats, statsLoaded, loadingStats]);
  
  // 格式化时间
  const formatTime = (dateString: string) => {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);
      
      if (diffMins < 1) return '刚刚';
      if (diffMins < 60) return `${diffMins}分钟前`;
      if (diffHours < 24) return `${diffHours}小时前`;
      if (diffDays < 7) return `${diffDays}天前`;
      
      return date.toLocaleDateString();
    } catch {
      return '未知时间';
    }
  };

  // 获取精简的统计信息显示
  const getStatsDisplay = () => {
    if (loadingStats) {
      return (
        <span className="stats-summary loading">
          <span style={{ opacity: 0.6 }}>加载中...</span>
        </span>
      );
    }
    
    if (!groupStats && !isVisible && !isSelected) {
      // 未可见且未选中时显示空状态
      return (
        <span className="stats-summary placeholder">
          <span style={{ opacity: 0.4, fontSize: '12px' }}>滚动加载</span>
        </span>
      );
    }
    
    if (!groupStats) {
      return null;
    }

    const stats = [];
    
    // 总消息数 - 简化显示，超过1k显示为k
    if (groupStats.total_messages > 0) {
      const count = groupStats.total_messages;
      if (count >= 10000) {
        stats.push(`${Math.floor(count / 1000)}k条`);
      } else if (count >= 1000) {
        stats.push(`${(count / 1000).toFixed(1)}k条`);
      } else {
        stats.push(`${count}条`);
      }
    }

    // 置顶消息数 - 只在有置顶时显示
    if (groupStats.pinned_messages > 0) {
      stats.push(`📌${groupStats.pinned_messages}`);
    }

    // 添加媒体消息统计（如果有的话）
    const mediaCount = (groupStats.photo_messages || 0) + (groupStats.video_messages || 0);
    if (mediaCount > 0) {
      stats.push(`📸${mediaCount > 99 ? '99+' : mediaCount}`);
    }

    return stats.length > 0 ? (
      <span className="stats-summary">
        {stats.join(' · ')}
      </span>
    ) : (
      <span className="stats-summary empty">
        <span style={{ opacity: 0.5 }}>暂无数据</span>
      </span>
    );
  };

  // 获取群组头像
  const getGroupAvatar = () => {
    // 使用群组名称的首字母作为头像
    const firstChar = group.title.charAt(0).toUpperCase();
    
    // 生成随机颜色基于群组名称
    const getAvatarColor = (name: string) => {
      const colors = [
        '#f56a00', '#7265e6', '#ffbf00', '#00a2ae', 
        '#87d068', '#1890ff', '#722ed1', '#eb2f96',
        '#52c41a', '#faad14', '#13c2c2', '#f5222d',
        '#1890ff', '#722ed1', '#eb2f96', '#52c41a'
      ];
      let hash = 0;
      for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
      }
      return colors[Math.abs(hash) % colors.length];
    };
    
    return (
      <Avatar 
        size={40} 
        style={{ 
          backgroundColor: isSelected ? '#1890ff' : getAvatarColor(group.title),
          color: 'white',
          fontWeight: 'bold',
          fontSize: 16,
          border: isSelected ? '2px solid #40a9ff' : '1px solid #d9d9d9'
        }}
      >
        {firstChar}
      </Avatar>
    );
  };

  // 获取状态图标
  const getStatusIcon = () => {
    if (group.is_active) {
      return (
        <Tooltip title="群组活跃">
          <CheckCircleOutlined style={{ color: '#52c41a' }} />
        </Tooltip>
      );
    } else {
      return (
        <Tooltip title="群组暂停">
          <PauseCircleOutlined style={{ color: '#ff4d4f' }} />
        </Tooltip>
      );
    }
  };

  return (
    <div
      ref={elementRef}
      className={`group-item ${isSelected ? 'selected' : ''} ${group.is_pinned ? 'pinned' : ''}`}
      onClick={() => onClick(group)}
    >
      {/* 群组头像 */}
      <div className="group-avatar">
        {getGroupAvatar()}
        {unreadCount > 0 && (
          <Badge 
            count={unreadCount} 
            size="small" 
            style={{ 
              position: 'absolute', 
              top: -4, 
              right: -4,
              zIndex: 1 
            }} 
          />
        )}
      </div>

      {/* 群组信息 */}
      <div className="group-info">
        <div className="group-main-info">
          <div className="group-name">
            <div className="name-section">
              {/* 置顶图标 */}
              {group.is_pinned && (
                <Tooltip title="已置顶群组">
                  <PushpinOutlined 
                    style={{ 
                      marginRight: 6, 
                      color: '#1890ff', 
                      fontSize: 14,
                      transform: 'rotate(45deg)' 
                    }} 
                  />
                </Tooltip>
              )}
              <span className="name-text">{group.title}</span>
              {getStatusIcon()}
            </div>
          </div>
          {/* 统计信息 - 移到外层，与group-name并行 */}
          <div className="stats-section">
            {getStatsDisplay()}
          </div>
        </div>
        
        <div className="group-username">
          @{group.username || 'unknown'}
        </div>

        {/* 群组描述 */}
        {group.description && (
          <div className="group-description">
            {group.description}
          </div>
        )}

        {/* 群组元数据 */}
        <div className="group-metadata">
          <div className="metadata-item">
            <TeamOutlined style={{ marginRight: 4 }} />
            <span>{group.member_count?.toLocaleString() || 0} 成员</span>
          </div>
          
          {lastMessageTime && (
            <div className="metadata-item">
              <span className="last-message-time">
                {formatTime(lastMessageTime)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* 群组状态标签 */}
      <div className="group-status">
        {group.is_pinned && (
          <Tag 
            icon={<PushpinOutlined />}
            color="blue"
            style={{ marginBottom: 4 }}
          >
            置顶
          </Tag>
        )}
        
        <Tag 
          color={group.is_active ? 'success' : 'error'}
        >
          {group.is_active ? '活跃' : '暂停'}
        </Tag>
        
        {unreadCount > 0 && (
          <Badge 
            count={unreadCount} 
            style={{ 
              backgroundColor: '#1890ff',
              marginTop: 4
            }} 
          />
        )}
      </div>
    </div>
  );
};

export default GroupItem;