import React, { useState, useEffect, useCallback } from 'react';
import { Card, Typography, Avatar, Space, Spin, message as notification } from 'antd';
import { MessageOutlined, UserOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { TelegramMessage } from '../../types';
import { telegramApi } from '../../services/apiService';
import './ReplyMessagePreview.css';

const { Text } = Typography;

interface ReplyMessagePreviewProps {
  replyToMessageId: number;
  groupId: number;
  onJumpToMessage?: (messageId: number) => void;
  className?: string;
  compact?: boolean;
}

const ReplyMessagePreview: React.FC<ReplyMessagePreviewProps> = ({
  replyToMessageId,
  groupId,
  onJumpToMessage,
  className = '',
  compact = false
}) => {
  const [replyMessage, setReplyMessage] = useState<TelegramMessage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 获取回复消息详情
  const fetchReplyMessage = useCallback(async () => {
    if (!replyToMessageId || !groupId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      console.log('ReplyMessagePreview - fetching reply message:', {
        replyToMessageId,
        groupId
      });
      
      const message = await telegramApi.getMessageById(groupId, replyToMessageId);
      console.log('ReplyMessagePreview - fetched message:', message);
      setReplyMessage(message);
    } catch (error: any) {
      console.error('Failed to fetch reply message:', error);
      setError('无法加载回复消息');
      
      // 创建模拟数据用于测试UI
      const mockMessage: TelegramMessage = {
        id: replyToMessageId,
        message_id: replyToMessageId,
        group_id: groupId,
        text: '这是被回复的消息内容 (模拟数据)',
        sender_name: '测试用户',
        sender_username: 'testuser',
        sender_id: 123,
        date: new Date().toISOString(),
        created_at: new Date().toISOString(),
        is_forwarded: false,
        is_pinned: false
      };
      setReplyMessage(mockMessage);
      console.log('ReplyMessagePreview - using mock data for testing');
    } finally {
      setLoading(false);
    }
  }, [replyToMessageId, groupId]);

  useEffect(() => {
    fetchReplyMessage();
  }, [fetchReplyMessage]);

  // 处理跳转到消息
  const handleJumpToMessage = useCallback(() => {
    if (onJumpToMessage && replyMessage) {
      console.log('ReplyMessagePreview - jumping to message:', replyMessage.id);
      onJumpToMessage(replyMessage.id);
    } else {
      console.log('ReplyMessagePreview - no jump handler or message');
    }
  }, [onJumpToMessage, replyMessage]);

  // 格式化时间
  const formatMessageTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return '刚刚';
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays === 1) return '昨天';
    if (diffDays < 7) return `${diffDays}天前`;
    
    return date.toLocaleDateString('zh-CN', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // 截断文本
  const truncateText = (text: string, maxLength: number = 50) => {
    if (!text) return '...';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  // 获取发送者头像
  const getSenderAvatar = () => {
    if (replyMessage?.sender_name) {
      const firstChar = replyMessage.sender_name.charAt(0).toUpperCase();
      return (
        <Avatar 
          size={compact ? 24 : 32} 
          style={{ 
            backgroundColor: '#1890ff',
            fontSize: compact ? '12px' : '14px',
            lineHeight: compact ? '24px' : '32px'
          }}
        >
          {firstChar}
        </Avatar>
      );
    }
    return (
      <Avatar 
        size={compact ? 24 : 32} 
        icon={<UserOutlined />} 
        style={{ backgroundColor: '#8c8c8c' }}
      />
    );
  };

  if (loading) {
    return (
      <div className={`reply-message-preview loading ${className}`}>
        <div className="reply-content">
          <MessageOutlined style={{ marginRight: 6, color: '#1890ff' }} />
          <Spin size="small" />
          <Text type="secondary" style={{ marginLeft: 8, fontSize: compact ? 11 : 12 }}>
            加载回复消息...
          </Text>
        </div>
      </div>
    );
  }

  if (error && !replyMessage) {
    return (
      <div className={`reply-message-preview error ${className}`}>
        <div className="reply-content">
          <MessageOutlined style={{ marginRight: 6, color: '#ff4d4f' }} />
          <Text type="danger" style={{ fontSize: compact ? 11 : 12 }}>
            {error}
          </Text>
        </div>
      </div>
    );
  }

  if (!replyMessage) {
    return null;
  }

  return (
    <div 
      className={`reply-message-preview ${compact ? 'compact' : ''} ${className}`}
      onClick={handleJumpToMessage}
      style={{ cursor: onJumpToMessage ? 'pointer' : 'default' }}
    >
      <div className="reply-content">
        {/* 回复指示图标 */}
        <div className="reply-indicator">
          <MessageOutlined style={{ color: '#1890ff', fontSize: compact ? 12 : 14 }} />
        </div>
        
        {/* 发送者头像 */}
        <div className="sender-avatar">
          {getSenderAvatar()}
        </div>
        
        {/* 消息信息 */}
        <div className="message-info">
          <div className="sender-info">
            <Text 
              strong 
              style={{ 
                color: '#1890ff', 
                fontSize: compact ? 11 : 12,
                marginRight: 8
              }}
            >
              {replyMessage.sender_name || replyMessage.sender_username || '未知用户'}
            </Text>
            <Space size={4}>
              <ClockCircleOutlined style={{ 
                color: '#8c8c8c', 
                fontSize: compact ? 10 : 11 
              }} />
              <Text 
                type="secondary" 
                style={{ fontSize: compact ? 10 : 11 }}
              >
                {formatMessageTime(replyMessage.date)}
              </Text>
            </Space>
          </div>
          
          <div className="message-content">
            <Text 
              style={{ 
                fontSize: compact ? 11 : 12,
                color: '#595959',
                lineHeight: '1.4'
              }}
            >
              {replyMessage.text ? 
                truncateText(replyMessage.text, compact ? 30 : 60) : 
                replyMessage.media_type ? 
                  `[${replyMessage.media_type}]` : 
                  '消息内容'
              }
            </Text>
          </div>
        </div>
        
        {/* 跳转提示 */}
        {onJumpToMessage && (
          <div className="jump-hint">
            <Text 
              type="secondary" 
              style={{ 
                fontSize: compact ? 10 : 11,
                opacity: 0.8
              }}
            >
              点击跳转
            </Text>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReplyMessagePreview;