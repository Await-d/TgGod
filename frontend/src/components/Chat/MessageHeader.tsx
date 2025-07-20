import React, { useState, useCallback, useEffect } from 'react';
import { Typography, Tag, Avatar, Spin, Button } from 'antd';
import { 
  TeamOutlined,
  CheckCircleOutlined,
  PauseCircleOutlined,
  MessageOutlined,
  UpOutlined,
  DownOutlined
} from '@ant-design/icons';
import { TelegramGroup } from '../../types';
import { telegramApi } from '../../services/apiService';
import './MessageHeader.css';

const { Title, Text } = Typography;

interface MessageHeaderProps {
  group: TelegramGroup;
  onJumpToMessage?: (messageId: number) => void;
  onRefresh?: () => Promise<void>;
  onSync?: () => Promise<void>;
  loading?: boolean;
  isMobile?: boolean;
}

const MessageHeader: React.FC<MessageHeaderProps> = ({
  group,
  onJumpToMessage,
  onRefresh,
  onSync,
  loading = false,
  isMobile = false
}) => {
  
  // 群组统计信息状态
  const [groupStats, setGroupStats] = useState<any>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [showStats, setShowStats] = useState(true); // 统计信息显示状态

  // 获取群组统计信息
  const fetchGroupStats = useCallback(async () => {
    if (!group) return;
    
    setLoadingStats(true);
    try {
      const stats = await telegramApi.getGroupStats(group.id);
      setGroupStats(stats);
    } catch (error: any) {
      console.error('获取群组统计信息失败:', error);
      setGroupStats(null);
    } finally {
      setLoadingStats(false);
    }
  }, [group]);

  // 当群组变化时获取信息
  useEffect(() => {
    if (group) {
      fetchGroupStats();
    }
  }, [group, fetchGroupStats]);

  // 获取群组头像
  const getGroupAvatar = () => {
    const firstChar = group.title.charAt(0).toUpperCase();
    const getAvatarColor = (name: string) => {
      const colors = [
        '#f56a00', '#7265e6', '#ffbf00', '#00a2ae', 
        '#87d068', '#1890ff', '#722ed1', '#eb2f96'
      ];
      let hash = 0;
      for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
      }
      return colors[Math.abs(hash) % colors.length];
    };
    
    return (
      <Avatar 
        size={isMobile ? 36 : 42} 
        style={{ 
          backgroundColor: getAvatarColor(group.title),
          color: 'white',
          fontWeight: 'bold',
          fontSize: isMobile ? '14px' : '18px'
        }}
      >
        {firstChar}
      </Avatar>
    );
  };

  return (
    <div className="message-header-container">
      {/* 群组基本信息 */}
      <div className="group-info-section">
        <div className="group-main-info">
          {/* 群组头像 */}
          {getGroupAvatar()}
          
          {/* 群组信息 */}
          <div className="group-details">
            <div className="group-title-row">
              <Title level={4} className="group-title">
                {group.title}
              </Title>
              <Tag 
                color={group.is_active ? 'success' : 'error'} 
                icon={group.is_active ? <CheckCircleOutlined /> : <PauseCircleOutlined />}
                className="group-status-tag"
              >
                {group.is_active ? '活跃' : '暂停'}
              </Tag>
            </div>
            
            <div className="group-meta-row">
              <Text type="secondary" className="member-count">
                <TeamOutlined className="member-icon" />
                {group.member_count?.toLocaleString() || 0} 成员
              </Text>
              {group.username && (
                <Text type="secondary" className="group-username">
                  @{group.username}
                </Text>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 群组统计信息 */}
      {groupStats && (
        <div className="stats-section">
          <div className="stats-header">
            <div className="stats-header-left">
              <MessageOutlined className="stats-icon" />
              <span className="stats-title">消息统计</span>
            </div>
            <Button 
              type="text" 
              size="small"
              icon={showStats ? <UpOutlined /> : <DownOutlined />}
              onClick={() => setShowStats(!showStats)}
              className="stats-toggle-btn"
              title={showStats ? '隐藏统计' : '显示统计'}
            />
          </div>
          {showStats && (loadingStats ? (
            <div className="stats-loading">
              <Spin size="small" />
            </div>
          ) : (
            <div className="stats-grid">
              <div className="stat-item">
                <div className="stat-value" style={{ color: '#1890ff' }}>
                  {groupStats.total_messages}
                </div>
                <div className="stat-label">总数</div>
              </div>
              <div className="stat-item">
                <div className="stat-value" style={{ color: '#52c41a' }}>
                  {groupStats.text_messages}
                </div>
                <div className="stat-label">文本</div>
              </div>
              <div className="stat-item">
                <div className="stat-value" style={{ color: '#faad14' }}>
                  {groupStats.media_messages}
                </div>
                <div className="stat-label">媒体</div>
              </div>
              <div className="stat-item">
                <div className="stat-value" style={{ color: '#13c2c2' }}>
                  {groupStats.photo_messages}
                </div>
                <div className="stat-label">图片</div>
              </div>
              {!isMobile && (
                <>
                  <div className="stat-item">
                    <div className="stat-value" style={{ color: '#722ed1' }}>
                      {groupStats.video_messages}
                    </div>
                    <div className="stat-label">视频</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value" style={{ color: '#fa8c16' }}>
                      {groupStats.forwarded_messages}
                    </div>
                    <div className="stat-label">转发</div>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MessageHeader;