import React, { useState, useCallback, useEffect } from 'react';
import { Typography, Tag, Avatar, Spin, Button } from 'antd';
import { 
  TeamOutlined,
  CheckCircleOutlined,
  PauseCircleOutlined,
  MessageOutlined,
  UpOutlined,
  DownOutlined,
  PlayCircleOutlined,
  PushpinOutlined,
  LeftOutlined,
  RightOutlined,
  ArrowLeftOutlined
} from '@ant-design/icons';
import { TelegramGroup } from '../../types';
import { telegramApi, messageApi } from '../../services/apiService';
import { useMediaDuration } from '../../hooks/useMediaDuration';
import { TelegramMessage } from '../../types';
import './MessageHeader.css';

const { Title, Text } = Typography;

interface MessageHeaderProps {
  group: TelegramGroup;
  messages?: TelegramMessage[]; // 添加消息列表用于计算媒体时长
  onJumpToMessage?: (messageId: number) => void;
  onRefresh?: () => Promise<void>;
  onSync?: () => Promise<void>;
  loading?: boolean;
  isMobile?: boolean;
  // 添加导航相关属性
  onNavigateBack?: () => void;
  hasNavigationHistory?: boolean;
}

const MessageHeader: React.FC<MessageHeaderProps> = ({
  group,
  messages = [],
  onJumpToMessage,
  onRefresh,
  onSync,
  loading = false,
  isMobile = false,
  onNavigateBack,
  hasNavigationHistory = false
}) => {
  
  // 群组统计信息状态
  const [groupStats, setGroupStats] = useState<any>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [showStats, setShowStats] = useState(true); // 统计信息显示状态

  // 置顶消息状态
  const [pinnedMessages, setPinnedMessages] = useState<TelegramMessage[]>([]);
  const [currentPinnedIndex, setCurrentPinnedIndex] = useState(0);

  // 使用媒体时长Hook
  const {
    totalDuration,
    audioCount,
    videoCount,
    voiceCount,
    isLoading: durationLoading,
    formatDuration
  } = useMediaDuration({ 
    messages: messages || [],
    enabled: showStats 
  });

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

  // 获取置顶消息
  const fetchPinnedMessages = useCallback(async () => {
    if (!group) return;
    
    try {
      const messages = await messageApi.getPinnedMessages(group.id);
      setPinnedMessages(messages);
      setCurrentPinnedIndex(0);
    } catch (error: any) {
      console.error('获取置顶消息失败:', error);
      setPinnedMessages([]);
    } finally {
    }
  }, [group]);

  // 置顶消息导航
  const handlePinnedPrevious = useCallback(() => {
    if (pinnedMessages.length <= 1) return;
    setCurrentPinnedIndex(prev => prev > 0 ? prev - 1 : pinnedMessages.length - 1);
  }, [pinnedMessages.length]);

  const handlePinnedNext = useCallback(() => {
    if (pinnedMessages.length <= 1) return;
    setCurrentPinnedIndex(prev => prev < pinnedMessages.length - 1 ? prev + 1 : 0);
  }, [pinnedMessages.length]);

  // 跳转到置顶消息
  const handleJumpToPinnedMessage = useCallback(() => {
    if (pinnedMessages.length > 0 && onJumpToMessage) {
      const currentMessage = pinnedMessages[currentPinnedIndex];
      onJumpToMessage(currentMessage.id || currentMessage.message_id);
    }
  }, [pinnedMessages, currentPinnedIndex, onJumpToMessage]);

  // 当群组变化时获取信息
  useEffect(() => {
    if (group) {
      fetchGroupStats();
      fetchPinnedMessages();
    }
  }, [group, fetchGroupStats, fetchPinnedMessages]);

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
      {/* 导航区域 */}
      {hasNavigationHistory && onNavigateBack && (
        <div className="navigation-section">
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={onNavigateBack}
            className="back-button"
            title="返回上一群组"
            size={isMobile ? 'small' : 'middle'}
          />
        </div>
      )}
      
      {/* 群组基本信息 */}
      <div className="group-info-section">
        <div className="group-main-info">
          {/* 群组头像 */}
          {getGroupAvatar()}
          
          {/* 群组信息 */}
          <div className="group-details">
            <div className="group-title-row">
              <div className="group-title-section">
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
              
              {/* 置顶消息内联显示 */}
              {pinnedMessages.length > 0 && (
                <div className="pinned-inline">
                  <div className="pinned-content">
                    <PushpinOutlined className="pinned-icon" />
                    <span 
                      className="pinned-text"
                      onClick={handleJumpToPinnedMessage}
                      title="点击跳转到置顶消息"
                    >
                      {pinnedMessages[currentPinnedIndex]?.text?.substring(0, 50) || '(媒体消息)'}
                      {(pinnedMessages[currentPinnedIndex]?.text?.length || 0) > 50 && '...'}
                    </span>
                    {pinnedMessages.length > 1 && (
                      <div className="pinned-nav">
                        <Button
                          type="text"
                          size="small"
                          icon={<LeftOutlined />}
                          onClick={handlePinnedPrevious}
                          className="pinned-nav-btn"
                        />
                        <span className="pinned-count">
                          {currentPinnedIndex + 1}/{pinnedMessages.length}
                        </span>
                        <Button
                          type="text"
                          size="small"
                          icon={<RightOutlined />}
                          onClick={handlePinnedNext}
                          className="pinned-nav-btn"
                        />
                      </div>
                    )}
                  </div>
                </div>
              )}
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
            <div className="stats-content">
              {/* 基础统计 */}
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

              {/* 媒体时长统计 */}
              {(audioCount > 0 || videoCount > 0 || voiceCount > 0) && (
                <div className="media-duration-section">
                  <div className="media-duration-header">
                    <PlayCircleOutlined className="duration-icon" />
                    <span className="duration-title">媒体时长统计</span>
                    {durationLoading && <Spin size="small" />}
                  </div>
                  <div className="media-duration-grid">
                    <div className="duration-item total-duration">
                      <div className="duration-value" style={{ color: '#f5222d' }}>
                        {formatDuration(totalDuration)}
                      </div>
                      <div className="duration-label">总时长</div>
                    </div>
                    {voiceCount > 0 && (
                      <div className="duration-item">
                        <div className="duration-value" style={{ color: '#722ed1' }}>
                          {voiceCount}
                        </div>
                        <div className="duration-label">语音</div>
                      </div>
                    )}
                    {audioCount > 0 && (
                      <div className="duration-item">
                        <div className="duration-value" style={{ color: '#faad14' }}>
                          {audioCount}
                        </div>
                        <div className="duration-label">音频</div>
                      </div>
                    )}
                    {videoCount > 0 && (
                      <div className="duration-item">
                        <div className="duration-value" style={{ color: '#52c41a' }}>
                          {videoCount}
                        </div>
                        <div className="duration-label">视频</div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MessageHeader;