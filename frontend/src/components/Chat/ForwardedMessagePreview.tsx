import React, { useState, useCallback } from 'react';
import { Space, Button, Tag, Tooltip, message as antMessage, Spin } from 'antd';
import {
  ShareAltOutlined,
  MessageOutlined,
  UserOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  RightOutlined
} from '@ant-design/icons';
import { TelegramMessage } from '../../types';
import { messageApi } from '../../services/apiService';
import styles from './ForwardedMessagePreview.module.css';

interface ForwardedMessagePreviewProps {
  message: TelegramMessage;
  onJumpToOriginal?: (messageId: number) => void;
  className?: string;
  compact?: boolean;
}

const ForwardedMessagePreview: React.FC<ForwardedMessagePreviewProps> = ({
  message,
  onJumpToOriginal,
  className = '',
  compact = false
}) => {
  const [originalMessage, setOriginalMessage] = useState<TelegramMessage | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 获取原始消息详情
  const fetchOriginalMessage = useCallback(async () => {
    if (!message.reply_to_message_id || originalMessage || loading) return;

    setLoading(true);
    setError(null);

    try {
      // 假设有API可以根据消息ID获取原始消息
      const response = await messageApi.getMessageById(message.group_id, message.reply_to_message_id);
      setOriginalMessage(response);
      setExpanded(true);
    } catch (error: any) {
      console.error('获取原始消息失败:', error);
      setError('原始消息不可用');
      antMessage.error('无法获取原始消息');
    } finally {
      setLoading(false);
    }
  }, [message.reply_to_message_id, message.group_id, originalMessage, loading]);

  // 跳转到原始消息
  const handleJumpToOriginal = useCallback(() => {
    if (message.reply_to_message_id && onJumpToOriginal) {
      onJumpToOriginal(message.reply_to_message_id);
    } else if (originalMessage) {
      // 如果有原始消息数据，也可以跳转
      onJumpToOriginal?.(originalMessage.message_id);
    } else {
      antMessage.warning('无法跳转到原始消息');
    }
  }, [message.reply_to_message_id, originalMessage, onJumpToOriginal]);

  // 切换展开/收起
  const toggleExpanded = useCallback(async () => {
    if (!expanded && !originalMessage && !error) {
      await fetchOriginalMessage();
    } else {
      setExpanded(!expanded);
    }
  }, [expanded, originalMessage, error, fetchOriginalMessage]);

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
        <UserOutlined style={{ color: '#8c8c8c' }} />
        <span>
          转发自：{message.forwarded_from || '未知来源'}
        </span>
        {message.reply_to_message_id && (
          <Tag color="blue">
            原消息 #{message.reply_to_message_id}
          </Tag>
        )}
      </Space>
    </div>
  );

  // 渲染原始消息预览
  const renderOriginalPreview = () => {
    if (loading) {
      return (
        <div className={styles.loading}>
          <Spin size="small" />
          <span>加载原始消息...</span>
        </div>
      );
    }

    if (error) {
      return (
        <div className={styles.error}>
          <span>{error}</span>
        </div>
      );
    }

    if (!originalMessage || !expanded) {
      return null;
    }

    return (
      <div className={styles.originalMessage}>
        <div className={styles.originalHeader}>
          <Space size="small">
            <MessageOutlined style={{ color: '#1890ff' }} />
            <span className={styles.originalSender}>原始消息</span>
            <ClockCircleOutlined style={{ color: '#8c8c8c' }} />
            <span className={styles.originalTime}>{formatTime(originalMessage.date)}</span>
          </Space>
        </div>
        
        <div className={`${styles.originalContent} ${compact ? styles.compact : ''}`}>
          {originalMessage.text && (
            <div>
              {originalMessage.text.length > 200 && !compact
                ? `${originalMessage.text.substring(0, 200)}...`
                : originalMessage.text}
            </div>
          )}
          
          {originalMessage.media_type && (
            <div style={{ marginTop: '8px' }}>
              <Tag color="green">
                {originalMessage.media_type.toUpperCase()}
              </Tag>
              {originalMessage.media_filename && (
                <span style={{ marginLeft: '8px', fontSize: '12px', color: '#666' }}>
                  {originalMessage.media_filename}
                </span>
              )}
            </div>
          )}
          
          {originalMessage.sender_name && (
            <div style={{ marginTop: '4px', fontSize: '12px', color: '#666' }}>
              <UserOutlined style={{ marginRight: 4 }} />
              {originalMessage.sender_name}
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
          {message.reply_to_message_id && (
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={handleJumpToOriginal}
              className={styles.jumpButton}
            >
              查看原消息
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.forwardedPreview} ${className}`}>
      <div className={styles.forwardHeader}>
        {renderForwardBadge()}
        {renderForwardSource()}
        
        <div className={styles.forwardActions}>
          <Space size="small">
            {message.reply_to_message_id && (
              <>
                <Tooltip title={expanded ? "收起预览" : "展开预览"}>
                  <Button
                    type="text"
                    size="small"
                    icon={<MessageOutlined />}
                    onClick={toggleExpanded}
                    loading={loading}
                    className={styles.expandButton}
                  >
                    {expanded ? '收起' : '预览'}
                  </Button>
                </Tooltip>
                
                <Tooltip title="跳转到原消息">
                  <Button
                    type="text"
                    size="small"
                    icon={<RightOutlined />}
                    onClick={handleJumpToOriginal}
                    className={styles.jumpButton}
                  >
                    跳转
                  </Button>
                </Tooltip>
              </>
            )}
          </Space>
        </div>
      </div>
      
      {expanded && (
        <div className={`${styles.previewContent} ${compact ? styles.compact : ''}`}>
          {renderOriginalPreview()}
        </div>
      )}
    </div>
  );
};

export default ForwardedMessagePreview;