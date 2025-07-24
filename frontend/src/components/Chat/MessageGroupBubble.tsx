import React, { useCallback } from 'react';
import {
  Avatar,
  Space,
  Typography,
  Tag,
  Button,
  Tooltip,
  Popconfirm,
  Card,
  Image,
  Row,
  Col
} from 'antd';
import {
  UserOutlined,
  MessageOutlined,
  DeleteOutlined,
  PlusOutlined,
  ShareAltOutlined,
  PushpinOutlined,
  FileImageOutlined,
  FileTextOutlined,
  VideoCameraOutlined,
  AudioOutlined,
  EyeOutlined
} from '@ant-design/icons';
import { TelegramMessage } from '../../types';
import { MessageBubbleProps } from '../../types/chat';
import MediaDownloadPreview from './MediaDownloadPreview';
import MessageReactions from './MessageReactions';
import EnhancedMessageText from './EnhancedMessageText';
import LinkPreview, { parseLinks } from './LinkPreview';
import MarkdownRenderer, { isMarkdownContent } from './MarkdownRenderer';
import ForwardedMessagePreview from './ForwardedMessagePreview';
import ReplyMessagePreview from './ReplyMessagePreview';
import './MessageBubble.css';

const { Text, Paragraph } = Typography;

interface MessageGroupBubbleProps extends Omit<MessageBubbleProps, 'message'> {
  messages: TelegramMessage[]; // 消息组中的所有消息
  primaryMessage: TelegramMessage; // 主消息（用于显示发送者信息等）
  showAvatar: boolean;
  isOwn: boolean;
  isMobile?: boolean;
  onOpenGallery?: (message: TelegramMessage) => void;
  onUpdateDownloadState?: (messageId: number, state: any) => void;
}

const MessageGroupBubble: React.FC<MessageGroupBubbleProps> = ({
  messages,
  primaryMessage,
  showAvatar,
  isOwn,
  onReply,
  onCreateRule,
  onDelete,
  onJumpToGroup,
  onJumpToMessage,
  onOpenGallery,
  onUpdateDownloadState,
  isMobile = false
}) => {

  // 清理文本中的表情反应字符串
  const removeReactionEmojisFromText = (text: string): string => {
    if (!text) return '';
    return text.replace(/ReactionEmoji\s*\(\s*emoticon\s*=\s*['"][^'"]+['"]\s*\)\s*\d+/g, '')
      .replace(/\n\s*\n/g, '\n')
      .trim();
  };

  // 获取发送者头像
  const getSenderAvatar = () => {
    if (primaryMessage.sender_name) {
      const colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2'];
      let hash = 0;
      for (let i = 0; i < primaryMessage.sender_name.length; i++) {
        hash = primaryMessage.sender_name.charCodeAt(i) + ((hash << 5) - hash);
      }
      return colors[Math.abs(hash) % colors.length];
    }

    return (
      <Avatar
        size={isMobile ? 32 : 36}
        style={{
          backgroundColor: '#1890ff',
          fontSize: isMobile ? 12 : 14
        }}
        icon={<UserOutlined />}
      />
    );
  };

  // 格式化时间
  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    
    if (date.toDateString() === now.toDateString()) {
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
      });
    } else {
      return date.toLocaleString('zh-CN', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    }
  };

  // 处理消息点击
  const handleMessageClick = useCallback((e: React.MouseEvent) => {
    // 阻止事件冒泡，避免触发父组件的点击事件
    e.stopPropagation();
  }, []);

  // 渲染消息内容
  const renderMessageContent = () => {
    // 找出有文本内容的消息（通常是第一条）
    const textMessage = messages.find(msg => msg.text && msg.text.trim()) || primaryMessage;
    // 找出所有有媒体的消息
    const mediaMessages = messages.filter(msg => msg.media_type);

    return (
      <div className="message-content">
        {/* 转发消息预览 */}
        {primaryMessage.is_forwarded && (
          <ForwardedMessagePreview
            message={primaryMessage}
            onJumpToOriginal={(messageId) => {
              console.log('Jump to original message:', messageId);
            }}
            onJumpToGroup={onJumpToGroup}
            onJumpToMessage={onJumpToMessage}
            compact={isMobile}
            isMobile={isMobile}
          />
        )}

        {/* 回复信息 */}
        {primaryMessage.reply_to_message_id && !primaryMessage.is_forwarded && (
          <ReplyMessagePreview
            replyToMessageId={primaryMessage.reply_to_message_id}
            groupId={primaryMessage.group_id}
            onJumpToMessage={onJumpToMessage}
            compact={isMobile}
            className="message-reply-preview"
          />
        )}

        {/* 消息文本 */}
        {textMessage.text && (
          <div className="message-text">
            {(() => {
              const containsEmojiString = textMessage.text!.includes('ReactionEmoji');
              const processedText = containsEmojiString
                ? removeReactionEmojisFromText(textMessage.text!)
                : textMessage.text!;

              if (!processedText.trim()) {
                return null;
              }

              if (isMarkdownContent(processedText)) {
                return (
                  <MarkdownRenderer
                    content={processedText}
                    isOwn={isOwn}
                    className="message-markdown"
                  />
                );
              } else {
                return (
                  <>
                    <EnhancedMessageText
                      text={processedText}
                      onJumpToGroup={onJumpToGroup}
                      className="message-enhanced-text"
                    />

                    {parseLinks(processedText).filter(link => !link.includes('t.me')).map((link, index) => (
                      <LinkPreview
                        key={index}
                        url={link}
                        className="message-link-preview"
                      />
                    ))}
                  </>
                );
              }
            })()}
          </div>
        )}

        {/* 媒体内容组 - 多个媒体文件网格显示 */}
        {mediaMessages.length > 0 && (
          <div className="message-media-group" style={{ marginTop: textMessage.text ? 8 : 0 }}>
            {mediaMessages.length === 1 ? (
              // 单个媒体文件，正常大小显示
              <div onClick={(e) => e.stopPropagation()}>
                <MediaDownloadPreview
                  message={mediaMessages[0]}
                  className="message-media-preview"
                  onPreview={(mediaPath) => {
                    if (onOpenGallery) {
                      const updatedMessage = {
                        ...mediaMessages[0],
                        media_path: mediaPath,
                        media_downloaded: true
                      };
                      onOpenGallery(updatedMessage);
                    }
                  }}
                  onUpdateDownloadState={onUpdateDownloadState}
                />
              </div>
            ) : (
              // 多个媒体文件，网格布局
              <Row gutter={[4, 4]}>
                {mediaMessages.map((message, index) => (
                  <Col 
                    key={message.id}
                    span={mediaMessages.length === 2 ? 12 : 8}
                    style={{ minHeight: 120 }}
                  >
                    <div 
                      onClick={(e) => e.stopPropagation()}
                      style={{ height: '100%' }}
                    >
                      <MediaDownloadPreview
                        message={message}
                        className="message-media-preview compact"
                        compact={true} // 紧凑模式
                        onPreview={(mediaPath) => {
                          if (onOpenGallery) {
                            const updatedMessage = {
                              ...message,
                              media_path: mediaPath,
                              media_downloaded: true
                            };
                            onOpenGallery(updatedMessage);
                          }
                        }}
                        onUpdateDownloadState={onUpdateDownloadState}
                      />
                    </div>
                  </Col>
                ))}
              </Row>
            )}
          </div>
        )}

        {/* 消息标签 */}
        <div className="message-tags">
          <Space size={4} wrap>
            {primaryMessage.is_pinned && (
              <Tag color="red">
                <PushpinOutlined /> 置顶
              </Tag>
            )}

            {primaryMessage.edit_date && (
              <Tag color="blue">
                已编辑
              </Tag>
            )}
          </Space>
        </div>

        {/* 消息反应 */}
        {primaryMessage.reactions && (
          <MessageReactions
            reactions={primaryMessage.reactions}
            isMobile={isMobile}
          />
        )}

        {/* 提及和标签 */}
        {((primaryMessage.mentions && primaryMessage.mentions.length > 0) ||
          (primaryMessage.hashtags && primaryMessage.hashtags.length > 0)) && (
            <div className="message-meta-tags">
              <Space size={4} wrap>
                {primaryMessage.mentions?.map(mention => (
                  <Tag key={mention} color="purple">
                    @{mention}
                  </Tag>
                ))}
                {primaryMessage.hashtags?.map(hashtag => (
                  <Tag key={hashtag} color="green">
                    #{hashtag}
                  </Tag>
                ))}
              </Space>
            </div>
          )}
      </div>
    );
  };

  return (
    <div
      className={`message-bubble ${isOwn ? 'own' : 'other'}`}
      onClick={handleMessageClick}
      style={{ cursor: 'pointer' }}
    >
      {/* 发送者头像 */}
      {!isOwn && (
        <div className="message-avatar">
          {showAvatar ? getSenderAvatar() : (
            <div className="avatar-placeholder">
              <div className="avatar-indicator" />
            </div>
          )}
        </div>
      )}

      {/* 消息主体 */}
      <div className="message-body">
        {/* 发送者信息 */}
        {!isOwn && showAvatar && (
          <div className="message-sender-info">
            <Space>
              <Text strong style={{ color: '#1890ff' }}>
                {primaryMessage.sender_name || primaryMessage.sender_username || '未知用户'}
              </Text>
              {primaryMessage.sender_username && primaryMessage.sender_name && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  @{primaryMessage.sender_username}
                </Text>
              )}
            </Space>
          </div>
        )}

        {/* 消息气泡 */}
        <div className={`message-bubble-content ${isOwn ? 'own-bubble' : 'other-bubble'}`}>
          {renderMessageContent()}

          {/* 时间和操作 */}
          <div className="message-footer">
            <div className="message-time">
              <Text type="secondary" style={{ fontSize: 11 }}>
                {formatTime(primaryMessage.date)}
              </Text>
            </div>

            {/* 操作按钮 */}
            <div className="message-actions">
              <Space size={4}>
                <Tooltip title="回复">
                  <Button
                    type="text"
                    size="small"
                    icon={<MessageOutlined />}
                    onClick={(e) => {
                      e.stopPropagation();
                      onReply(primaryMessage);
                    }}
                    style={{ fontSize: 11, padding: '2px 4px' }}
                  />
                </Tooltip>

                <Tooltip title="创建规则">
                  <Button
                    type="text"
                    size="small"
                    icon={<PlusOutlined />}
                    onClick={(e) => {
                      e.stopPropagation();
                      onCreateRule(primaryMessage);
                    }}
                    style={{ fontSize: 11, padding: '2px 4px' }}
                  />
                </Tooltip>

                <Popconfirm
                  title="确定删除这条消息吗？"
                  onConfirm={(e) => {
                    e?.stopPropagation();
                    // 删除消息组中的所有消息
                    messages.forEach(msg => onDelete(msg.id));
                  }}
                  okText="删除"
                  cancelText="取消"
                >
                  <Tooltip title="删除">
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={(e) => e.stopPropagation()}
                      style={{ fontSize: 11, padding: '2px 4px' }}
                    />
                  </Tooltip>
                </Popconfirm>
              </Space>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default React.memo(MessageGroupBubble);