import React from 'react';
import { Typography } from 'antd';
import TelegramLinkPreview from './TelegramLinkPreview';
import { detectTelegramLinks, isTelegramLink } from '../../utils/telegramLinkUtils';
import './EnhancedMessageText.css';

const { Text } = Typography;

interface EnhancedMessageTextProps {
  text: string;
  onJumpToGroup?: (groupId: number) => void;
  className?: string;
}

const EnhancedMessageText: React.FC<EnhancedMessageTextProps> = ({
  text,
  onJumpToGroup,
  className = ''
}) => {
  // 检测文本中的Telegram链接
  const telegramLinks = detectTelegramLinks(text);
  
  // 如果没有Telegram链接，直接渲染普通文本
  if (telegramLinks.length === 0) {
    return (
      <div className={`enhanced-message-text ${className}`}>
        <Text>{text}</Text>
      </div>
    );
  }

  // 渲染带链接预览的文本
  const renderTextWithPreviews = () => {
    const elements: React.ReactNode[] = [];
    let lastIndex = 0;
    
    telegramLinks.forEach((link, index) => {
      const linkIndex = text.indexOf(link.url, lastIndex);
      
      // 添加链接前的文本
      if (linkIndex > lastIndex) {
        const beforeText = text.substring(lastIndex, linkIndex);
        if (beforeText.trim()) {
          elements.push(
            <Text key={`text-${index}-before`}>
              {beforeText}
            </Text>
          );
        }
      }
      
      // 添加链接文本（作为普通文本，不可点击，因为我们有预览卡片）
      elements.push(
        <Text 
          key={`link-${index}`}
          style={{ 
            color: '#1890ff', 
            textDecoration: 'underline',
            fontWeight: 500 
          }}
        >
          {link.url}
        </Text>
      );
      
      lastIndex = linkIndex + link.url.length;
    });
    
    // 添加最后剩余的文本
    if (lastIndex < text.length) {
      const remainingText = text.substring(lastIndex);
      if (remainingText.trim()) {
        elements.push(
          <Text key="text-end">
            {remainingText}
          </Text>
        );
      }
    }
    
    return elements;
  };

  return (
    <div className={`enhanced-message-text ${className}`}>
      {/* 渲染文本内容 */}
      <div className="message-text-content">
        {renderTextWithPreviews()}
      </div>
      
      {/* 渲染Telegram链接预览卡片 */}
      <div className="telegram-link-previews">
        {telegramLinks.map((link, index) => (
          <TelegramLinkPreview
            key={`preview-${index}`}
            url={link.url}
            onJumpToGroup={onJumpToGroup}
          />
        ))}
      </div>
    </div>
  );
};

export default EnhancedMessageText;