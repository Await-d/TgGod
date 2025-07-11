import React from 'react';
import { Avatar, Badge, Tag, Tooltip } from 'antd';
import { TeamOutlined, CheckCircleOutlined, PauseCircleOutlined } from '@ant-design/icons';
import { GroupListItemProps } from '../../types/chat';

const GroupItem: React.FC<GroupListItemProps> = ({
  group,
  isSelected,
  onClick,
  unreadCount = 0,
  lastMessageTime
}) => {
  
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
      className={`group-item ${isSelected ? 'selected' : ''}`}
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