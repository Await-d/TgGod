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
import './MessageBubble.css';

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

  // 获取发送者头像
  const getSenderAvatar = () => {
    if (!showAvatar) return null;
    
    const firstChar = (message.sender_name || message.sender_username || 'U').charAt(0).toUpperCase();
    return (
      <Avatar 
        size={isMobile ? 32 : 36} 
        style={{ 
          backgroundColor: '#87d068',
          color: 'white',
          fontWeight: 'bold'
        }}
        icon={!message.sender_name && !message.sender_username ? <UserOutlined /> : undefined}
      >
        {(message.sender_name || message.sender_username) ? firstChar : undefined}
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
            <Paragraph style={{ margin: 0, wordBreak: 'break-word' }}>
              {message.text}
            </Paragraph>
          </div>
        )}

        {/* 媒体内容 */}
        {message.media_type && (
          <div className="message-media">
            <Card size="small" style={{ margin: '8px 0' }}>
              <Space>
                {getMediaIcon(message.media_type)}
                <div className="media-info">
                  <div>
                    <Text strong>{message.media_type.toUpperCase()}</Text>
                    {message.media_size && (
                      <Text type="secondary" style={{ marginLeft: 8 }}>
                        {(message.media_size / (1024 * 1024)).toFixed(2)} MB
                      </Text>
                    )}
                  </div>
                  {message.media_filename && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {message.media_filename}
                    </Text>
                  )}
                </div>
              </Space>
            </Card>
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
          {getSenderAvatar()}
        </div>
      )}

      {/* 消息主体 */}
      <div className="message-body">
        {/* 发送者信息 */}
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