import React, { useState, useRef, useEffect } from 'react';
import { 
  Input, 
  Button, 
  Space, 
  Tooltip, 
  Card, 
  Typography,
  message as antMessage,
  Popover 
} from 'antd';
import { 
  SendOutlined,
  SmileOutlined,
  PaperClipOutlined,
  CloseOutlined,
  MessageOutlined 
} from '@ant-design/icons';
import { MessageInputProps } from '../../types/chat';
import './MessageInput.css';

const { TextArea } = Input;
const { Text } = Typography;

interface ExtendedMessageInputProps extends MessageInputProps {
  isMobile?: boolean;
  loading?: boolean;
}

const MessageInput: React.FC<ExtendedMessageInputProps> = ({
  selectedGroup,
  replyTo,
  onSend,
  onClearReply,
  isMobile = false,
  loading = false
}) => {
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const inputRef = useRef<any>(null);

  // 聚焦输入框
  const focusInput = () => {
    inputRef.current?.focus();
  };

  // 处理键盘事件
  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // 发送消息
  const handleSendMessage = async () => {
    if (!selectedGroup || !inputValue.trim() || sending) return;

    setSending(true);
    try {
      await onSend(inputValue.trim());
      setInputValue('');
      antMessage.success('消息发送成功！');
    } catch (error: any) {
      antMessage.error('发送消息失败: ' + error.message);
      console.error('发送消息失败:', error);
    } finally {
      setSending(false);
    }
  };

  // 插入表情
  const insertEmoji = (emoji: string) => {
    const newValue = inputValue + emoji;
    setInputValue(newValue);
    setShowEmojiPicker(false);
    focusInput();
  };

  // 常用表情列表
  const commonEmojis = [
    '😀', '😃', '😄', '😁', '😆', '😅', '😂', '🤣',
    '😊', '😇', '🙂', '🙃', '😉', '😌', '😍', '🥰',
    '😘', '😗', '😙', '😚', '😋', '😛', '😝', '😜',
    '🤪', '🤨', '🧐', '🤓', '😎', '🤩', '🥳', '😏',
    '😒', '😞', '😔', '😟', '😕', '🙁', '☹️', '😣',
    '😖', '😫', '😩', '🥺', '😢', '😭', '😤', '😠',
    '😡', '🤬', '🤯', '😳', '🥵', '🥶', '😱', '😨',
    '😰', '😥', '😓', '🤗', '🤔', '🤭', '🤫', '🤥',
    '😶', '😐', '😑', '😬', '🙄', '😯', '😦', '😧',
    '😮', '😲', '🥱', '😴', '🤤', '😪', '😵', '🤐'
  ];

  // 表情选择器内容
  const emojiPickerContent = (
    <div className="emoji-picker">
      <div className="emoji-grid">
        {commonEmojis.map((emoji, index) => (
          <button
            key={index}
            className="emoji-button"
            onClick={() => insertEmoji(emoji)}
          >
            {emoji}
          </button>
        ))}
      </div>
    </div>
  );

  // 当有回复时自动聚焦
  useEffect(() => {
    if (replyTo) {
      focusInput();
    }
  }, [replyTo]);

  // 检查群组是否允许发送消息
  const canSendMessages = selectedGroup?.can_send_messages !== false && 
                         selectedGroup?.permissions?.can_send_messages !== false;

  // 如果没有选择群组，显示提示
  if (!selectedGroup) {
    return (
      <div className="message-input-disabled">
        <div className="disabled-content">
          <MessageOutlined style={{ fontSize: 24, color: '#d9d9d9' }} />
          <Text type="secondary">请选择一个群组开始聊天</Text>
        </div>
      </div>
    );
  }

  // 如果群组不允许发送消息，显示禁用提示
  if (!canSendMessages) {
    return (
      <div className="message-input-disabled">
        <div className="disabled-content">
          <MessageOutlined style={{ fontSize: 24, color: '#d9d9d9' }} />
          <Text type="secondary">此群组不允许发送消息</Text>
        </div>
      </div>
    );
  }

  return (
    <div className="message-input-container">
      {/* 回复预览 */}
      {replyTo && (
        <div className="reply-preview">
          <Card size="small" className="reply-card">
            <div className="reply-content">
              <div className="reply-header">
                <Text strong style={{ color: '#1890ff' }}>
                  回复 {replyTo.sender_name || replyTo.sender_username || '未知用户'}
                </Text>
                <Button
                  type="text"
                  size="small"
                  icon={<CloseOutlined />}
                  onClick={onClearReply}
                  className="reply-close-btn"
                />
              </div>
              <div className="reply-message">
                <Text type="secondary" ellipsis>
                  {replyTo.text || '(媒体消息)'}
                </Text>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* 输入区域 */}
      <div className="input-area">
        <div className="input-wrapper">
          {/* 附件按钮 */}
          {!isMobile && (
            <Tooltip title="附件">
              <Button
                type="text"
                icon={<PaperClipOutlined />}
                className="attachment-btn"
                disabled
              />
            </Tooltip>
          )}

          {/* 文本输入框 */}
          <div className="text-input-wrapper">
            <TextArea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder={isMobile ? "输入消息..." : "输入消息，按Enter发送，Shift+Enter换行"}
              autoSize={{ 
                minRows: 1, 
                maxRows: isMobile ? 3 : 4 
              }}
              className="message-textarea"
              disabled={loading}
            />
            
            {/* 表情按钮 */}
            <Popover
              content={emojiPickerContent}
              trigger="click"
              open={showEmojiPicker}
              onOpenChange={setShowEmojiPicker}
              placement="topRight"
              overlayClassName="emoji-popover"
            >
              <Button
                type="text"
                icon={<SmileOutlined />}
                className="emoji-btn"
                size="small"
              />
            </Popover>
          </div>

          {/* 发送按钮 */}
          <div className="send-button-wrapper">
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSendMessage}
              loading={sending}
              disabled={!inputValue.trim() || loading}
              className="send-btn"
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '' : '发送'}
            </Button>
          </div>
        </div>

        {/* 输入提示 */}
        {!isMobile && (
          <div className="input-hint">
            <Space size={16}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                按 Enter 发送，Shift+Enter 换行
              </Text>
              {inputValue.length > 0 && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {inputValue.length} / 4000 字符
                </Text>
              )}
            </Space>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageInput;