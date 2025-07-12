import React, { useState, useCallback } from 'react';
import { Space, Tag, Button, Tooltip, message as antMessage } from 'antd';
import {
  ShareAltOutlined,
  MessageOutlined,
  UserOutlined,
  ClockCircleOutlined,
  RightOutlined,
  TeamOutlined,
  SoundOutlined
} from '@ant-design/icons';
import { TelegramMessage } from '../../types';
import { telegramApi } from '../../services/apiService';
import styles from './ForwardedMessagePreview.module.css';

interface ForwardedMessagePreviewProps {
  message: TelegramMessage;
  onJumpToOriginal?: (messageId: number) => void;
  onJumpToGroup?: (groupId: number) => void;
  className?: string;
  compact?: boolean;
  showOriginalContent?: boolean;
}

const ForwardedMessagePreview: React.FC<ForwardedMessagePreviewProps> = ({
  message,
  onJumpToOriginal,
  onJumpToGroup,
  className = '',
  compact = false,
  showOriginalContent = true
}) => {
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  // 跳转到转发来源群组
  const handleJumpToSourceGroup = useCallback(async () => {
    if (!message.forwarded_from_id || message.forwarded_from_type === 'user') {
      antMessage.info('无法跳转到用户私聊');
      return;
    }

    if (!onJumpToGroup) {
      antMessage.warning('跳转功能不可用');
      return;
    }

    setLoading(true);
    try {
      // 查找对应的群组
      const group = await telegramApi.searchGroupByTelegramId(message.forwarded_from_id);
      if (group) {
        onJumpToGroup(group.id);
        antMessage.success(`跳转到${message.forwarded_from_type === 'channel' ? '频道' : '群组'}：${group.title}`);
      } else {
        antMessage.warning('未找到对应的群组，可能未加入该群组');
      }
    } catch (error: any) {
      console.error('跳转群组失败:', error);
      antMessage.error('跳转失败');
    } finally {
      setLoading(false);
    }
  }, [message.forwarded_from_id, message.forwarded_from_type, onJumpToGroup]);

  // 获取转发来源类型图标
  const getForwardSourceIcon = () => {
    switch (message.forwarded_from_type) {
      case 'channel':
        return <SoundOutlined style={{ color: '#1890ff' }} />;
      case 'group':
        return <TeamOutlined style={{ color: '#52c41a' }} />;
      case 'user':
        return <UserOutlined style={{ color: '#8c8c8c' }} />;
      default:
        return <UserOutlined style={{ color: '#8c8c8c' }} />;
    }
  };

  // 获取转发来源类型名称
  const getForwardSourceTypeName = () => {
    switch (message.forwarded_from_type) {
      case 'channel':
        return '频道';
      case 'group':
        return '群组';
      case 'user':
        return '用户';
      default:
        return '未知来源';
    }
  };

  // 切换展开/收起
  const toggleExpanded = useCallback(() => {
    setExpanded(!expanded);
  }, [expanded]);

  // 格式化时间
  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // 渲染转发标识
  const renderForwardBadge = () => (
    <div className={styles.forwardBadge}>
      <ShareAltOutlined className={styles.icon} />
      <span>转发</span>
    </div>
  );

  // 渲染转发来源信息
  const renderForwardSource = () => (
    <div className={styles.forwardSource}>
      <Space size="small">
        {getForwardSourceIcon()}
        <span>
          转发自{getForwardSourceTypeName()}：{message.forwarded_from || '未知来源'}
        </span>
        {message.forwarded_date && (
          <Tag color="blue">
            <ClockCircleOutlined style={{ marginRight: 4 }} />
            {formatTime(message.forwarded_date)}
          </Tag>
        )}
        {message.forwarded_from_id && message.forwarded_from_type !== 'user' && (
          <Tooltip title={`跳转到${getForwardSourceTypeName()}`}>
            <Button
              type="text"
              size="small"
              icon={<RightOutlined />}
              onClick={handleJumpToSourceGroup}
              loading={loading}
              className={styles.jumpButton}
            >
              跳转
            </Button>
          </Tooltip>
        )}
        {showOriginalContent && (message.text || message.media_type) && (
          <Tooltip title={expanded ? "收起内容" : "展开内容"}>
            <Button
              type="text"
              size="small"
              icon={<MessageOutlined />}
              onClick={toggleExpanded}
              className={styles.expandButton}
            >
              {expanded ? '收起' : '预览'}
            </Button>
          </Tooltip>
        )}
      </Space>
    </div>
  );

  // 渲染转发消息内容
  const renderForwardedContent = () => {
    if (!showOriginalContent || !expanded) return null;

    return (
      <div className={styles.forwardedContent}>
        <div className={styles.contentHeader}>
          <Space size="small">
            <MessageOutlined style={{ color: '#1890ff' }} />
            <span className={styles.contentLabel}>转发内容</span>
          </Space>
        </div>
        
        <div className={`${styles.contentBody} ${compact ? styles.compact : ''}`}>
          {message.text && (
            <div className={styles.textContent}>
              {message.text.length > 200 && compact
                ? `${message.text.substring(0, 200)}...`
                : message.text}
            </div>
          )}
          
          {message.media_type && (
            <div className={styles.mediaInfo}>
              <Tag color="green">
                {message.media_type.toUpperCase()}
              </Tag>
              {message.media_filename && (
                <span className={styles.filename}>
                  {message.media_filename}
                </span>
              )}
            </div>
          )}
          
          {message.sender_name && (
            <div className={styles.senderInfo}>
              <UserOutlined style={{ marginRight: 4 }} />
              原发送者：{message.sender_name}
            </div>
          )}
        </div>
      </div>
    );
  };

  if (!message.is_forwarded) {
    return null;
  }

  if (compact) {
    return (
      <div className={`${styles.forwardedPreview} ${styles.compact} ${className}`}>
        <div className={styles.forwardHeader}>
          {renderForwardBadge()}
          {renderForwardSource()}
        </div>
        {showOriginalContent && renderForwardedContent()}
      </div>
    );
  }

  return (
    <div className={`${styles.forwardedPreview} ${className}`}>
      <div className={styles.forwardHeader}>
        {renderForwardBadge()}
        {renderForwardSource()}
      </div>
      
      {showOriginalContent && (
        <div className={styles.contentContainer}>
          {renderForwardedContent()}
        </div>
      )}
    </div>
  );
};

export default ForwardedMessagePreview;