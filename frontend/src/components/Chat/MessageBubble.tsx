import React from 'react';
import { 
  Avatar, 
  Space, 
  Typography, 
  Tag, 
  Button, 
  Tooltip, 
  Popconfirm,
  Card,
  Image 
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
import EnhancedMediaPreview from './EnhancedMediaPreview';
import EnhancedVoiceMessage from './EnhancedVoiceMessage';
import MessageReactions from './MessageReactions';
import LinkPreview, { parseLinks, renderTextWithLinks } from './LinkPreview';
import MarkdownRenderer, { isMarkdownContent } from './MarkdownRenderer';
import './EnhancedMediaPreview.css';
import './EnhancedVoiceMessage.css';
import './MessageReactions.css';
import './LinkPreview.css';
import './MarkdownRenderer.css';
import './MessageBubble.css';
// 引入 highlight.js 样式
import 'highlight.js/styles/github.css';

const { Text, Paragraph } = Typography;

interface ExtendedMessageBubbleProps extends MessageBubbleProps {
  isMobile?: boolean;
}

const MessageBubble: React.FC<ExtendedMessageBubbleProps> = ({
  message,
  isOwn,
  showAvatar,
  onReply,
  onCreateRule,
  onDelete,
  isMobile = false
}) => {
  
  // 获取媒体类型图标
  const getMediaIcon = (mediaType: string) => {
    switch (mediaType) {
      case 'photo': return <FileImageOutlined style={{ color: '#52c41a' }} />;
      case 'video': return <VideoCameraOutlined style={{ color: '#1890ff' }} />;
      case 'document': return <FileTextOutlined style={{ color: '#faad14' }} />;
      case 'audio': return <AudioOutlined style={{ color: '#722ed1' }} />;
      case 'voice': return <AudioOutlined style={{ color: '#eb2f96' }} />;
      case 'sticker': return <FileImageOutlined style={{ color: '#13c2c2' }} />;
      default: return <FileTextOutlined />;
    }
  };

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

  // 渲染消息内容
  const renderMessageContent = () => {
    return (
      <div className="message-content">
        {/* 回复信息 */}
        {message.reply_to_message_id && (
          <div className="reply-info">
            <MessageOutlined style={{ marginRight: 4 }} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              回复消息 #{message.reply_to_message_id}
            </Text>
          </div>
        )}

        {/* 消息文本 */}
        {message.text && (
          <div className="message-text">
            {isMarkdownContent(message.text) ? (
              <MarkdownRenderer 
                content={message.text} 
                isOwn={isOwn}
                className="message-markdown"
              />
            ) : (
              <>
                <Paragraph style={{ margin: 0, wordBreak: 'break-word' }}>
                  {renderTextWithLinks(message.text)}
                </Paragraph>
                
                {/* 链接预览 */}
                {parseLinks(message.text).map((link, index) => (
                  <LinkPreview
                    key={index}
                    url={link}
                    className="message-link-preview"
                  />
                ))}
              </>
            )}
          </div>
        )}

        {/* 媒体内容 - 使用增强组件 */}
        {message.media_type && message.media_path && (
          <div className="message-media">
            {/* 语音和音频消息 */}
            {(message.media_type === 'voice' || message.media_type === 'audio') && (
              <EnhancedVoiceMessage
                url={message.media_path}
                duration={0} // duration not available in the type
                filename={message.media_filename}
                size={message.media_size}
                className="message-voice"
                compact={isMobile}
              />
            )}
            
            {/* 所有其他媒体类型使用增强预览组件 */}
            {!['voice', 'audio'].includes(message.media_type) && (
              <EnhancedMediaPreview
                mediaType={message.media_type}
                mediaPath={message.media_path}
                filename={message.media_filename}
                size={message.media_size}
                className="message-media-preview"
                thumbnail={true}
                onGalleryOpen={(mediaPath) => {
                  // TODO: 打开画廊模式
                  console.log('Open gallery for:', mediaPath);
                }}
              />
            )}
          </div>
        )}

        {/* 消息标签 */}
        <div className="message-tags">
          <Space size={4} wrap>
            {message.is_forwarded && (
              <Tag color="orange">
                <ShareAltOutlined /> 转发
              </Tag>
            )}
            
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
    <div className={`message-bubble ${isOwn ? 'own' : 'other'}`}>
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
            <div className="message-actions">
              <Space size={4}>
                <Tooltip title="回复">
                  <Button
                    type="text"
                    size="small"
                    icon={<MessageOutlined />}
                    onClick={() => onReply(message)}
                    className="action-btn"
                  />
                </Tooltip>
                
                <Tooltip title="创建规则">
                  <Button
                    type="text"
                    size="small"
                    icon={<PlusOutlined />}
                    onClick={() => onCreateRule(message)}
                    className="action-btn"
                  />
                </Tooltip>
                
                {!isMobile && (
                  <Popconfirm
                    title="确认删除这条消息吗？"
                    onConfirm={() => onDelete(message.message_id)}
                    placement="topRight"
                  >
                    <Tooltip title="删除">
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
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

export default MessageBubble;