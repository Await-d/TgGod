import React, { useState, useEffect, useCallback } from 'react';
import { Space, Button, Typography, Tag, Avatar, Tooltip } from 'antd';
import { 
  ReloadOutlined, 
  SyncOutlined, 
  SettingOutlined, 
  TeamOutlined,
  CheckCircleOutlined,
  PauseCircleOutlined,
  PushpinOutlined,
  LeftOutlined,
  RightOutlined
} from '@ant-design/icons';
import { TelegramGroup, TelegramMessage } from '../../types';
import { messageApi } from '../../services/apiService';

const { Title, Text } = Typography;

interface MessageHeaderProps {
  group: TelegramGroup;
  onRefresh: () => void;
  onSync: () => void;
  onJumpToMessage?: (messageId: number) => void;
  loading?: boolean;
  isMobile?: boolean;
}

const MessageHeader: React.FC<MessageHeaderProps> = ({
  group,
  onRefresh,
  onSync,
  onJumpToMessage,
  loading = false,
  isMobile = false
}) => {
  
  // 置顶消息状态
  const [pinnedMessages, setPinnedMessages] = useState<TelegramMessage[]>([]);
  const [currentPinnedIndex, setCurrentPinnedIndex] = useState(0);
  const [loadingPinned, setLoadingPinned] = useState(false);
  
  // 获取置顶消息
  const fetchPinnedMessages = useCallback(async () => {
    if (!group) return;
    
    setLoadingPinned(true);
    try {
      const messages = await messageApi.getPinnedMessages(group.id);
      setPinnedMessages(messages);
      setCurrentPinnedIndex(0);
    } catch (error: any) {
      console.error('获取置顶消息失败:', error);
      setPinnedMessages([]);
    } finally {
      setLoadingPinned(false);
    }
  }, [group]);

  // 当群组变化时获取置顶消息
  useEffect(() => {
    if (group) {
      fetchPinnedMessages();
    }
  }, [group, fetchPinnedMessages]);

  // 切换置顶消息
  const handlePinnedPrevious = () => {
    setCurrentPinnedIndex(prev => prev > 0 ? prev - 1 : pinnedMessages.length - 1);
  };

  const handlePinnedNext = () => {
    setCurrentPinnedIndex(prev => prev < pinnedMessages.length - 1 ? prev + 1 : 0);
  };

  // 跳转到置顶消息
  const handleJumpToPinned = () => {
    if (pinnedMessages.length > 0 && onJumpToMessage) {
      onJumpToMessage(pinnedMessages[currentPinnedIndex].message_id);
    }
  };
  
  // 获取群组头像
  const getGroupAvatar = () => {
    const firstChar = group.title.charAt(0).toUpperCase();
    return (
      <Avatar 
        size={isMobile ? 32 : 40} 
        style={{ 
          backgroundColor: '#1890ff',
          color: 'white',
          fontWeight: 'bold'
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
    <div className="message-header">
      {/* 左侧群组信息 */}
      <div className="header-group-info">
        {getGroupAvatar()}
        <div className="group-details">
          <div className="group-title-row">
            <div className="group-title">
              <Title level={isMobile ? 5 : 4} style={{ margin: 0 }}>
                {group.title}
              </Title>
              {getStatusIcon()}
            </div>
            
            {/* 置顶消息 - 与群名在同一行 */}
            {pinnedMessages.length > 0 && (
              <div className="pinned-inline">
                <div className="pinned-content">
                  <PushpinOutlined className="pinned-icon" />
                  <span className="pinned-text" onClick={handleJumpToPinned}>
                    {pinnedMessages[currentPinnedIndex].text?.substring(0, isMobile ? 30 : 60) || '置顶消息'}
                    {pinnedMessages[currentPinnedIndex].text && pinnedMessages[currentPinnedIndex].text!.length > (isMobile ? 30 : 60) ? '...' : ''}
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
                      <span className="pinned-count">{currentPinnedIndex + 1}/{pinnedMessages.length}</span>
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
          
          <div className="group-meta">
            <Space size="small" wrap>
              <Text type="secondary">@{group.username}</Text>
              
              <div className="member-info">
                <TeamOutlined style={{ marginRight: 4 }} />
                <Text type="secondary">{group.member_count?.toLocaleString() || 0} 成员</Text>
              </div>
              
              <Tag 
                color={group.is_active ? 'success' : 'error'}
              >
                {group.is_active ? '活跃' : '暂停'}
              </Tag>
            </Space>
          </div>
          
          {group.description && !isMobile && (
            <div className="group-description">
              <Text type="secondary" ellipsis>
                {group.description}
              </Text>
            </div>
          )}
        </div>
      </div>

      {/* 右侧操作按钮 */}
      <div className="header-actions">
        <Space size="small">
          <Tooltip title="刷新消息">
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={onRefresh}
              loading={loading}
              size={isMobile ? 'small' : 'middle'}
            />
          </Tooltip>
          
          <Tooltip title="同步消息">
            <Button
              type="text"
              icon={<SyncOutlined />}
              onClick={onSync}
              size={isMobile ? 'small' : 'middle'}
            />
          </Tooltip>
          
          {!isMobile && (
            <Tooltip title="群组设置">
              <Button
                type="text"
                icon={<SettingOutlined />}
                size="middle"
              />
            </Tooltip>
          )}
        </Space>
      </div>
    </div>
  );
};

export default MessageHeader;