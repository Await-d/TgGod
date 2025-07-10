import React, { useState } from 'react';
import { Modal, Button, Select, Input, Space, message as antMessage, Card } from 'antd';
import { 
  ShareAltOutlined, 
  MessageOutlined, 
  SendOutlined,
  UserOutlined,
  GroupOutlined 
} from '@ant-design/icons';
import { TelegramMessage } from '../../types';
import './MessageQuoteForward.css';

const { Option } = Select;
const { TextArea } = Input;

interface Contact {
  id: string;
  name: string;
  type: 'user' | 'group';
  avatar?: string;
}

interface MessageQuoteForwardProps {
  message: TelegramMessage;
  contacts: Contact[];
  onQuote: (message: TelegramMessage) => void;
  onForward: (message: TelegramMessage, targets: string[], comment?: string) => void;
  className?: string;
}

const MessageQuoteForward: React.FC<MessageQuoteForwardProps> = ({
  message,
  contacts,
  onQuote,
  onForward,
  className
}) => {
  const [forwardVisible, setForwardVisible] = useState(false);
  const [selectedTargets, setSelectedTargets] = useState<string[]>([]);
  const [forwardComment, setForwardComment] = useState('');

  const handleQuote = () => {
    onQuote(message);
  };

  const handleForwardClick = () => {
    setForwardVisible(true);
    setSelectedTargets([]);
    setForwardComment('');
  };

  const handleForwardConfirm = () => {
    if (selectedTargets.length === 0) {
      antMessage.warning('请选择转发目标');
      return;
    }

    onForward(message, selectedTargets, forwardComment);
    setForwardVisible(false);
    antMessage.success('消息转发成功');
  };

  const handleForwardCancel = () => {
    setForwardVisible(false);
    setSelectedTargets([]);
    setForwardComment('');
  };

  const getContactIcon = (type: string) => {
    return type === 'group' ? <GroupOutlined /> : <UserOutlined />;
  };

  const formatMessagePreview = (msg: TelegramMessage) => {
    const preview = (msg.text || '').length > 50 
      ? (msg.text || '').substring(0, 50) + '...' 
      : (msg.text || '');
    
    if (msg.media_type === 'photo') {
      return '[图片] ' + preview;
    } else if (msg.media_type === 'video') {
      return '[视频] ' + preview;
    } else if (msg.media_type === 'voice') {
      return '[语音] ' + preview;
    } else {
      return preview;
    }
  };

  return (
    <div className={`message-quote-forward ${className || ''}`}>
      <Space>
        <Button
          type="text"
          icon={<MessageOutlined />}
          size="small"
          onClick={handleQuote}
          className="quote-button"
        >
          引用
        </Button>
        <Button
          type="text"
          icon={<ShareAltOutlined />}
          size="small"
          onClick={handleForwardClick}
          className="forward-button"
        >
          转发
        </Button>
      </Space>

      <Modal
        title="转发消息"
        visible={forwardVisible}
        onOk={handleForwardConfirm}
        onCancel={handleForwardCancel}
        width={500}
        okText="转发"
        cancelText="取消"
        okButtonProps={{
          icon: <SendOutlined />,
          disabled: selectedTargets.length === 0
        }}
      >
        <div className="forward-content">
          <Card size="small" className="message-preview">
            <div className="preview-header">
              <span className="preview-sender">{message.sender_name || message.sender_username || 'Unknown'}</span>
              <span className="preview-time">{new Date(message.date).toLocaleString()}</span>
            </div>
            <div className="preview-content">
              {formatMessagePreview(message)}
            </div>
          </Card>

          <div className="target-selection">
            <label>选择转发目标：</label>
            <Select
              mode="multiple"
              placeholder="选择联系人或群组"
              value={selectedTargets}
              onChange={setSelectedTargets}
              style={{ width: '100%', marginTop: 8 }}
              optionFilterProp="children"
              showSearch
            >
              {contacts.map(contact => (
                <Option key={contact.id} value={contact.id}>
                  <Space>
                    {getContactIcon(contact.type)}
                    {contact.name}
                  </Space>
                </Option>
              ))}
            </Select>
          </div>

          <div className="forward-comment">
            <label>添加评论（可选）：</label>
            <TextArea
              value={forwardComment}
              onChange={(e) => setForwardComment(e.target.value)}
              placeholder="添加转发评论..."
              rows={3}
              maxLength={200}
              style={{ marginTop: 8 }}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

// 引用消息显示组件
interface QuotedMessageProps {
  message: TelegramMessage;
  onRemove?: () => void;
  className?: string;
}

export const QuotedMessage: React.FC<QuotedMessageProps> = ({
  message,
  onRemove,
  className
}) => {
  return (
    <div className={`quoted-message ${className || ''}`}>
      <div className="quoted-content">
        <div className="quoted-header">
          <MessageOutlined style={{ marginRight: 4 }} />
          <span className="quoted-sender">{message.sender_name || message.sender_username || 'Unknown'}</span>
          {onRemove && (
            <Button 
              type="text" 
              size="small" 
              onClick={onRemove}
              className="remove-quote"
            >
              ×
            </Button>
          )}
        </div>
        <div className="quoted-text">
          {((message.text || '').length > 100 
            ? (message.text || '').substring(0, 100) + '...' 
            : (message.text || ''))}
        </div>
      </div>
    </div>
  );
};

export default MessageQuoteForward;