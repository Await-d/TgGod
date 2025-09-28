import React from 'react';
import { Typography } from 'antd';
import TelegramLinkPreview from './TelegramLinkPreview';
import GroupMentionPreview from './GroupMentionPreview';
import { detectTelegramLinks, detectGroupMentions } from '../../utils/telegramLinkUtils';
import './EnhancedMessageText.css';

const { Text } = Typography;

interface EnhancedMessageTextProps {
  text: string;
  onJumpToGroup?: (groupId: number) => void;
  className?: string;
  compact?: boolean;
}

const EnhancedMessageText: React.FC<EnhancedMessageTextProps> = ({
  text,
  onJumpToGroup,
  className = '',
  compact = false
}) => {
  // 检测所有群组信息（包括链接和非链接格式）
  const groupMentions = detectGroupMentions(text);
  const telegramLinks = detectTelegramLinks(text);
  
  // 如果没有任何群组相关信息，直接渲染普通文本
  if (groupMentions.length === 0 && telegramLinks.length === 0) {
    return (
      <div className={`enhanced-message-text ${className}`}>
        <Text>{text}</Text>
      </div>
    );
  }

  // 渲染带群组信息的文本
  const renderTextWithMentions = () => {
    const elements: React.ReactNode[] = [];
    let elementIndex = 0;
    
    // 按文本位置排序所有群组信息
    const allMentions = groupMentions
      .map(mention => ({
        ...mention,
        startIndex: text.indexOf(mention.text),
        endIndex: text.indexOf(mention.text) + mention.text.length
      }))
      .filter(mention => mention.startIndex >= 0)
      .sort((a, b) => a.startIndex - b.startIndex);

    let lastIndex = 0;
    
    allMentions.forEach((mention, index) => {
      // 添加提及前的文本
      if (mention.startIndex > lastIndex) {
        const beforeText = text.substring(lastIndex, mention.startIndex);
        if (beforeText.trim()) {
          elements.push(
            <span key={`text-${elementIndex++}`}>
              {beforeText}
            </span>
          );
        }
      }
      
      // 添加群组提及组件
      if (mention.type === 'link') {
        // 链接格式的保持原样显示
        elements.push(
          <Text 
            key={`mention-${elementIndex++}`}
            style={{ 
              color: '#1890ff', 
              textDecoration: 'underline',
              fontWeight: 500 
            }}
          >
            {mention.text}
          </Text>
        );
      } else {
        // 非链接格式的使用 GroupMentionPreview 组件
        elements.push(
          <GroupMentionPreview
            key={`mention-${elementIndex++}`}
            type={mention.type as 'username' | 'id' | 'name'}
            value={mention.value}
            text={mention.text}
            onJumpToGroup={onJumpToGroup}
            compact={compact}
          />
        );
      }
      
      lastIndex = mention.endIndex;
    });
    
    // 添加最后剩余的文本
    if (lastIndex < text.length) {
      const remainingText = text.substring(lastIndex);
      if (remainingText.trim()) {
        elements.push(
          <span key={`text-${elementIndex++}`}>
            {remainingText}
          </span>
        );
      }
    }
    
    return elements;
  };

  return (
    <div className={`enhanced-message-text ${className}`}>
      {/* 渲染文本内容 */}
      <div className="message-text-content">
        {renderTextWithMentions()}
      </div>
      
      {/* 渲染Telegram链接预览卡片（只对完整链接显示） */}
      {telegramLinks.length > 0 && (
        <div className="telegram-link-previews">
          {telegramLinks.map((link, index) => (
            <TelegramLinkPreview
              key={`preview-${index}`}
              url={link.url}
              onJumpToGroup={onJumpToGroup}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default EnhancedMessageText;