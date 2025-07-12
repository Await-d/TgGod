import React, { useState, useEffect } from 'react';
import { Avatar, Badge, Tag, Tooltip, Spin } from 'antd';
import { 
  TeamOutlined, 
  CheckCircleOutlined, 
  PauseCircleOutlined,
  PushpinOutlined,
  MessageOutlined,
  FileImageOutlined,
  VideoCameraOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import { GroupListItemProps } from '../../types/chat';
import { telegramApi } from '../../services/apiService';

const GroupItem: React.FC<GroupListItemProps> = ({
  group,
  isSelected,
  onClick,
  unreadCount = 0,
  lastMessageTime
}) => {
  const [groupStats, setGroupStats] = useState<any>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  
  // 获取群组统计信息
  useEffect(() => {
    const fetchGroupStats = async () => {
      if (!group.id) return;
      
      setLoadingStats(true);
      try {
        const stats = await telegramApi.getGroupStats(group.id);
        setGroupStats(stats);
      } catch (error) {
        // 静默失败，不影响基本功能
        console.warn('获取群组统计失败:', error);
      } finally {
        setLoadingStats(false);
      }
    };

    // 只在选中状态或者首次加载时获取统计
    if (isSelected || !groupStats) {
      fetchGroupStats();
    }
  }, [group.id, isSelected, groupStats]);
  
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

  // 获取统计信息摘要
  const getStatsDisplay = () => {
    if (loadingStats) {
      return <Spin size="small" />;
    }
    
    if (!groupStats) {
      return (
        <div className="stats-item">
          <MessageOutlined style={{ marginRight: 4, color: '#999' }} />
          <span style={{ color: '#999' }}>统计加载中...</span>
        </div>
      );
    }

    const items = [];
    
    // 总消息数
    if (groupStats.total_messages > 0) {
      items.push(
        <div key="total" className="stats-item">
          <MessageOutlined style={{ marginRight: 4 }} />
          <span>{groupStats.total_messages.toLocaleString()} 消息</span>
        </div>
      );
    }

    // 媒体消息统计
    const mediaCount = (groupStats.photo_messages || 0) + 
                      (groupStats.video_messages || 0) + 
                      (groupStats.document_messages || 0) + 
                      (groupStats.audio_messages || 0);
    
    if (mediaCount > 0) {
      items.push(
        <div key="media" className="stats-item">
          <FileImageOutlined style={{ marginRight: 4 }} />
          <span>{mediaCount.toLocaleString()} 媒体</span>
        </div>
      );
    }

    // 置顶消息
    if (groupStats.pinned_messages > 0) {
      items.push(
        <div key="pinned" className="stats-item">
          <PushpinOutlined style={{ marginRight: 4, color: '#1890ff' }} />
          <span style={{ color: '#1890ff' }}>{groupStats.pinned_messages} 置顶</span>
        </div>
      );
    }

    return items.slice(0, 2); // 最多显示2个统计项
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
          
          <div className="group-username">
            @{group.username || 'unknown'}
          </div>
        </div>

        {/* 群组描述 */}
        {group.description && (
          <div className="group-description">
            {group.description}
          </div>
        )}

        {/* 群组统计信息 - 新设计 */}
        <div className="group-stats">
          {getStatsDisplay()}
        </div>

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