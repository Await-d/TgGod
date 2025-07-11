import React, { useState, useEffect, useCallback } from 'react';
import { Card, Typography, Button, Space, Spin, Empty, message as antMessage } from 'antd';
import { 
  PushpinOutlined, 
  CloseOutlined, 
  LeftOutlined, 
  RightOutlined,
  ArrowDownOutlined 
} from '@ant-design/icons';
import { TelegramMessage, TelegramGroup } from '../../types';
import { messageApi } from '../../services/apiService';
import './PinnedMessages.css';

const { Text, Paragraph } = Typography;

interface PinnedMessagesProps {
  selectedGroup: TelegramGroup | null;
  onJumpToMessage: (messageId: number) => void;
  onClose?: () => void;
  visible?: boolean;
  isMobile?: boolean;
}

const PinnedMessages: React.FC<PinnedMessagesProps> = ({
  selectedGroup,
  onJumpToMessage,
  onClose,
  visible = true,
  isMobile = false
}) => {
  const [pinnedMessages, setPinnedMessages] = useState<TelegramMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);

  // 获取置顶消息
  const fetchPinnedMessages = useCallback(async () => {
    if (!selectedGroup) return;
    
    setLoading(true);
    try {
      const messages = await messageApi.getPinnedMessages(selectedGroup.id);
      setPinnedMessages(messages);
      setCurrentIndex(0);
    } catch (error: any) {
      console.error('获取置顶消息失败:', error);
      antMessage.error('获取置顶消息失败');
    } finally {
      setLoading(false);
    }
  }, [selectedGroup]);

  // 当群组变化时获取置顶消息
  useEffect(() => {
    if (selectedGroup && visible) {
      fetchPinnedMessages();
    }
  }, [selectedGroup, visible, fetchPinnedMessages]);

  // 切换到上一条置顶消息
  const handlePrevious = useCallback(() => {
    setCurrentIndex(prev => prev > 0 ? prev - 1 : pinnedMessages.length - 1);
  }, [pinnedMessages.length]);

  // 切换到下一条置顶消息
  const handleNext = useCallback(() => {
    setCurrentIndex(prev => prev < pinnedMessages.length - 1 ? prev + 1 : 0);
  }, [pinnedMessages.length]);

  // 跳转到消息位置
  const handleJumpToMessage = useCallback((messageId: number) => {
    try {
      onJumpToMessage(messageId);
      if (isMobile) {
        setIsExpanded(false);
      }
    } catch (error) {
      console.error('跳转到消息失败:', error);
      // 降级处理：至少关闭移动端展开状态
      if (isMobile) {
        setIsExpanded(false);
      }
    }
  }, [onJumpToMessage, isMobile]);

  // 格式化消息文本
  const formatMessageText = (text: string | undefined, maxLength: number = 100) => {
    if (!text) return '暂无文本内容';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  };

  // 格式化日期
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (!visible || !selectedGroup) return null;

  if (loading) {
    return (
      <div className="pinned-messages-container">
        <Card className="pinned-messages-card loading">
          <Spin size="small" />
          <Text type="secondary">加载置顶消息中...</Text>
        </Card>
      </div>
    );
  }

  if (pinnedMessages.length === 0) {
    return null; // 没有置顶消息时不显示
  }

  const currentMessage = pinnedMessages[currentIndex];

  return (
    <div className={`pinned-messages-container ${isMobile ? 'mobile' : ''}`}>
      <Card 
        className={`pinned-messages-card ${isExpanded ? 'expanded' : ''}`}
        size="small"
      >
        {/* 头部信息 */}
        <div className="pinned-header">
          <div className="pinned-icon">
            <PushpinOutlined />
          </div>
          <div className="pinned-info">
            <Text strong>置顶消息</Text>
            {pinnedMessages.length > 1 && (
              <Text type="secondary" className="pinned-count">
                {currentIndex + 1} / {pinnedMessages.length}
              </Text>
            )}
          </div>
          <div className="pinned-actions">
            {/* 展开/收起按钮 (移动端) */}
            {isMobile && (
              <Button
                type="text"
                size="small"
                icon={<ArrowDownOutlined rotate={isExpanded ? 180 : 0} />}
                onClick={() => setIsExpanded(!isExpanded)}
              />
            )}
            {/* 导航按钮 */}
            {pinnedMessages.length > 1 && (
              <Space size="small">
                <Button
                  type="text"
                  size="small"
                  icon={<LeftOutlined />}
                  onClick={handlePrevious}
                />
                <Button
                  type="text"
                  size="small"
                  icon={<RightOutlined />}
                  onClick={handleNext}
                />
              </Space>
            )}
            {/* 关闭按钮 */}
            {onClose && (
              <Button
                type="text"
                size="small"
                icon={<CloseOutlined />}
                onClick={onClose}
              />
            )}
          </div>
        </div>

        {/* 消息内容 */}
        <div className={`pinned-content ${isExpanded || !isMobile ? 'visible' : 'hidden'}`}>
          <div className="pinned-message-content">
            {/* 发送者信息 */}
            <div className="pinned-sender">
              <Text strong>{currentMessage.sender_name || '未知用户'}</Text>
              <Text type="secondary" className="pinned-date">
                {formatDate(currentMessage.date)}
              </Text>
            </div>
            
            {/* 消息文本 */}
            <div className="pinned-text">
              <Paragraph 
                ellipsis={{ rows: isMobile ? 2 : 3, expandable: false }}
                style={{ margin: 0 }}
              >
                {formatMessageText(currentMessage.text, isMobile ? 80 : 150)}
              </Paragraph>
            </div>

            {/* 媒体信息 */}
            {currentMessage.media_type && (
              <div className="pinned-media">
                <Text type="secondary">
                  📎 {currentMessage.media_type === 'photo' ? '图片' : 
                       currentMessage.media_type === 'video' ? '视频' : 
                       currentMessage.media_type === 'document' ? '文档' : 
                       currentMessage.media_type === 'audio' ? '音频' : 
                       currentMessage.media_type === 'voice' ? '语音' : 
                       '媒体文件'}
                </Text>
              </div>
            )}

            {/* 跳转按钮 */}
            <div className="pinned-jump">
              <Button
                type="primary"
                size="small"
                onClick={() => handleJumpToMessage(currentMessage.message_id)}
              >
                跳转到消息
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default PinnedMessages;