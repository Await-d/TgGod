import React, { useCallback } from 'react';
import {
  Avatar,
  Space,
  Typography,
  Tag,
  Button,
  Tooltip,
  Popconfirm
} from 'antd';
import {
  UserOutlined,
  MessageOutlined,
  DeleteOutlined,
  PlusOutlined,
  PushpinOutlined,
  EyeOutlined
} from '@ant-design/icons';
import { TelegramMessage } from '../../types';
import { MessageBubbleProps } from '../../types/chat';
import MediaDownloadPreview from './MediaDownloadPreview';
import AutoDownloadImagePreview from './AutoDownloadImagePreview';
import EnhancedVoiceMessage from './EnhancedVoiceMessage';
import MessageReactions from './MessageReactions';
import EnhancedMessageText from './EnhancedMessageText';
import LinkPreview, { parseLinks } from './LinkPreview';
import MarkdownRenderer, { isMarkdownContent } from './MarkdownRenderer';
import ForwardedMessagePreview from './ForwardedMessagePreview';
import ReplyMessagePreview from './ReplyMessagePreview';
import './EnhancedMediaPreview.css';
import './EnhancedVoiceMessage.css';
import './MessageReactions.css';
import './LinkPreview.css';
import './MarkdownRenderer.css';
import './MessageBubble.css';
// 引入 highlight.js 样式
import 'highlight.js/styles/github.css';

const { Text } = Typography;

interface ExtendedMessageBubbleProps extends MessageBubbleProps {
  isMobile?: boolean;
  onOpenGallery?: (message: TelegramMessage) => void;
}

const MessageBubble: React.FC<ExtendedMessageBubbleProps> = ({
  message,
  isOwn,
  showAvatar,
  onReply,
  onCreateRule,
  onDelete,
  onJumpToGroup,
  onJumpToMessage,
  onUpdateDownloadState,
  isMobile = false,
  onOpenGallery
}) => {
  const [isActive, setIsActive] = React.useState(false);

  // 处理消息点击，激活操作按钮
  const handleMessageClick = useCallback(() => {
    setIsActive(prev => !prev);
  }, []);


  // 获取发送者头像 - 简化逻辑，总是显示头像
  const getSenderAvatar = () => {
    const senderName = message.sender_name || message.sender_username || '未知用户';
    const firstChar = senderName.charAt(0).toUpperCase();

    // 生成随机颜色基于用户名
    const getAvatarColor = (name: string) => {
      const colors = [
        '#f56a00', '#7265e6', '#ffbf00', '#00a2ae',
        '#87d068', '#1890ff', '#722ed1', '#eb2f96',
        '#52c41a', '#faad14', '#13c2c2', '#f5222d'
      ];
      let hash = 0;
      for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
      }
      return colors[Math.abs(hash) % colors.length];
    };

    return (
      <Avatar
        size={isMobile ? 32 : 36}
        style={{
          backgroundColor: getAvatarColor(senderName),
          color: 'white',
          fontWeight: 'bold',
          fontSize: isMobile ? 14 : 16
        }}
        icon={!senderName || senderName === '未知用户' ? <UserOutlined /> : undefined}
      >
        {senderName !== '未知用户' ? firstChar : undefined}
      </Avatar>
    );
  };

  // 格式化时间
  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();

    if (isToday) {
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

  // 添加一个辅助方法来过滤掉文本中的表情反应字符串
  const removeReactionEmojisFromText = (text: string): string => {
    if (!text) return '';

    // 过滤掉所有类似 ReactionEmoji(emoticon='❤') 30 的字符串
    return text.replace(/ReactionEmoji\s*\(\s*emoticon\s*=\s*['"][^'"]+['"]\s*\)\s*\d+/g, '')
      .replace(/\n\s*\n/g, '\n') // 清理多余的空行
      .trim();
  };

  // 渲染消息内容
  const renderMessageContent = () => {
    return (
      <div className="message-content">
        {/* 转发消息预览 */}
        {message.is_forwarded && (
          <ForwardedMessagePreview
            message={message}
            onJumpToGroup={onJumpToGroup}
            onJumpToMessage={onJumpToMessage}
            compact={isMobile}
            isMobile={isMobile}
          />
        )}

        {/* 回复信息 */}
        {message.reply_to_message_id && !message.is_forwarded && (
          <>
            {console.log('MessageBubble - rendering ReplyMessagePreview', {
              messageId: message.id,
              replyToMessageId: message.reply_to_message_id,
              groupId: message.group_id,
              hasOnJumpToMessage: !!onJumpToMessage,
              isForwarded: message.is_forwarded
            })}
            <ReplyMessagePreview
              replyToMessageId={message.reply_to_message_id}
              groupId={message.group_id}
              onJumpToMessage={onJumpToMessage}
              compact={isMobile}
              className="message-reply-preview"
            />
          </>
        )}

        {/* 消息文本 */}
        {message.text && (
          <div className="message-text">
            {/* 处理文本中可能存在的表情反应字符串 */}
            {(() => {
              // 检查文本中是否包含"ReactionEmoji"字符串
              const containsEmojiString = message.text.includes('ReactionEmoji');

              // 处理文本，移除表情反应字符串
              const processedText = containsEmojiString
                ? removeReactionEmojisFromText(message.text)
                : message.text;

              // 如果处理后的文本为空，不显示任何内容
              if (!processedText.trim()) {
                return null;
              }

              // 使用处理后的文本
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

        {/* 媒体内容 - 智能选择组件 */}
        {message.media_type && (
          <div className="message-media">
            {/* 语音和音频消息 - 如果已下载则使用现有组件 */}
            {(message.media_type === 'voice' || message.media_type === 'audio') && message.media_downloaded && message.media_path ? (
              <EnhancedVoiceMessage
                url={message.media_path}
                duration={0} // duration not available in the type
                filename={message.media_filename}
                size={message.media_size}
                className="message-voice"
                compact={isMobile}
              />
            ) : message.media_type === 'photo' ? (
              /* 图片类型：使用自动下载组件（小于2MB自动下载） */
              <div onClick={(e) => e.stopPropagation()}>
                <AutoDownloadImagePreview
                  message={message}
                  className="message-image-preview"
                  maxAutoDownloadSize={2 * 1024 * 1024} // 2MB
                  onPreview={(imageUrl) => {
                    console.log('MessageBubble - Auto download image preview called', {
                      messageId: message.id,
                      imageUrl,
                      hasOnOpenGallery: !!onOpenGallery
                    });
                    if (onOpenGallery) {
                      // 创建一个更新的消息对象，包含当前的媒体路径
                      const updatedMessage = {
                        ...message,
                        media_path: imageUrl,
                        media_downloaded: true
                      };
                      onOpenGallery(updatedMessage);
                    }
                  }}
                  compact={isMobile}
                />
              </div>
            ) : (
              /* 其他媒体类型：使用按需下载预览组件 */
              <div onClick={(e) => e.stopPropagation()}>
                <MediaDownloadPreview
                  message={message}
                  className="message-media-preview"
                  onPreview={(mediaPath) => {
                    console.log('MessageBubble - onPreview called', {
                      messageId: message.id,
                      mediaPath,
                      hasOnOpenGallery: !!onOpenGallery
                    });
                    if (onOpenGallery) {
                      console.log('MessageBubble - calling onOpenGallery');
                      // 创建一个更新的消息对象，包含当前的媒体路径
                      const updatedMessage = {
                        ...message,
                        media_path: mediaPath,
                        media_downloaded: true
                      };
                      console.log('MessageBubble - calling onOpenGallery with updated message', {
                        originalMediaPath: message.media_path,
                        updatedMediaPath: mediaPath,
                        messageId: message.id
                      });
                      onOpenGallery(updatedMessage);
                    } else {
                      console.log('MessageBubble - no onOpenGallery prop, using fallback');
                      console.log('Open gallery for:', mediaPath);
                    }
                  }}
                  onUpdateDownloadState={onUpdateDownloadState}
                />
              </div>
            )}
          </div>
        )}

        {/* 消息标签 */}
        <div className="message-tags">
          <Space size={4} wrap>
            {message.is_pinned && (
              <Tag color="red">
                <PushpinOutlined /> 置顶
              </Tag>
            )}

            {message.edit_date && (
              <Tag color="blue">
                已编辑
              </Tag>
            )}
          </Space>
        </div>

        {/* 消息反应 */}
        {message.reactions && Object.keys(message.reactions).length > 0 && (
          <div className="message-reactions">
            <Space size={4} wrap>
              {Object.entries(message.reactions).map(([emoji, count]) => (
                <Tag key={emoji} color="pink">
                  {emoji} {count}
                </Tag>
              ))}
            </Space>
          </div>
        )}

        {/* 提及和标签 */}
        {((message.mentions && message.mentions.length > 0) ||
          (message.hashtags && message.hashtags.length > 0)) && (
            <div className="message-meta-tags">
              <Space size={4} wrap>
                {message.mentions?.map(mention => (
                  <Tag key={mention} color="purple">
                    @{mention}
                  </Tag>
                ))}
                {message.hashtags?.map(hashtag => (
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
      className={`message-bubble ${isOwn ? 'own' : 'other'} ${isActive ? 'active' : ''}`}
      onClick={handleMessageClick}
      style={{ cursor: 'pointer' }}
    >
      {/* 发送者头像 */}
      {!isOwn && (
        <div className="message-avatar">
          {showAvatar ? getSenderAvatar() : (
            <div className="avatar-placeholder">
              {/* 在连续消息中显示一个更小的指示器 */}
              <div className="avatar-indicator" />
            </div>
          )}
        </div>
      )}

      {/* 消息主体 */}
      <div className="message-body">
        {/* 发送者信息 - 只在显示头像时显示用户名 */}
        {!isOwn && showAvatar && (
          <div className="message-sender-info">
            <Space>
              <Text strong style={{ color: '#1890ff' }}>
                {message.sender_name || message.sender_username || '未知用户'}
              </Text>
              {message.sender_username && message.sender_name && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  @{message.sender_username}
                </Text>
              )}
            </Space>
          </div>
        )}

        {/* 消息气泡 */}
        <div className={`message-bubble-content ${isOwn ? 'own-bubble' : 'other-bubble'}`}>
          {renderMessageContent()}

          {/* 表情反应 */}
          {message.reactions && (
            <MessageReactions
              reactions={message.reactions}
              isMobile={isMobile}
            />
          )}

          {/* 消息时间和操作 */}
          <div className="message-footer">
            <div className="message-time">
              <Space size={8}>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {formatTime(message.date)}
                </Text>

                {message.view_count !== undefined && (
                  <div className="view-count">
                    <EyeOutlined style={{ fontSize: 11, marginRight: 2 }} />
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {message.view_count}
                    </Text>
                  </div>
                )}
              </Space>
            </div>

            {/* 操作按钮 */}
            <div className="message-actions" onClick={(e) => e.stopPropagation()}>
              <Space size={4}>
                <Tooltip title="回复">
                  <Button
                    type="text"
                    size="small"
                    icon={<MessageOutlined />}
                    onClick={(e) => {
                      e.stopPropagation();
                      onReply(message);
                    }}
                    className="action-btn"
                  />
                </Tooltip>

                <Tooltip title="创建规则">
                  <Button
                    type="text"
                    size="small"
                    icon={<PlusOutlined />}
                    onClick={(e) => {
                      e.stopPropagation();
                      onCreateRule(message);
                    }}
                    className="action-btn"
                  />
                </Tooltip>

                {!isMobile && (
                  <Popconfirm
                    title="确认删除这条消息吗？"
                    onConfirm={(e) => {
                      if (e) e.stopPropagation();
                      onDelete(message.message_id);
                    }}
                    placement="topRight"
                  >
                    <Tooltip title="删除">
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={(e) => e.stopPropagation()}
                        className="action-btn"
                      />
                    </Tooltip>
                  </Popconfirm>
                )}
              </Space>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// 使用 React.memo 优化性能，避免不必要的重新渲染
export default React.memo(MessageBubble, (prevProps, nextProps) => {
  // 自定义比较函数，只在关键属性变化时重新渲染
  return (
    prevProps.message.id === nextProps.message.id &&
    prevProps.message.text === nextProps.message.text &&
    prevProps.message.media_downloaded === nextProps.message.media_downloaded &&
    prevProps.message.media_path === nextProps.message.media_path &&
    prevProps.showAvatar === nextProps.showAvatar &&
    prevProps.isOwn === nextProps.isOwn &&
    prevProps.isMobile === nextProps.isMobile &&
    JSON.stringify(prevProps.message.reactions) === JSON.stringify(nextProps.message.reactions)
  );
});