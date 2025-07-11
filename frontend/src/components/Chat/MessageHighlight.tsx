import React from 'react';
import { Typography } from 'antd';

const { Text } = Typography;

interface MessageHighlightProps {
  content?: string;
  text?: string;
  searchTerm?: string;
  searchQuery?: string;
  className?: string;
}

const MessageHighlight: React.FC<MessageHighlightProps> = ({ 
  content, 
  text,
  searchTerm, 
  searchQuery,
  className 
}) => {
  const textContent = content || text || '';
  const searchPattern = searchTerm || searchQuery || '';
  
  if (!searchPattern) {
    return <span className={className}>{textContent}</span>;
  }

  const parts = textContent.split(new RegExp(`(${searchPattern})`, 'gi'));
  
  return (
    <span className={className}>
      {parts.map((part, index) => 
        part.toLowerCase() === searchPattern.toLowerCase() ? (
          <Text key={index} mark style={{ backgroundColor: '#faad14', padding: '0 2px' }}>
            {part}
          </Text>
        ) : (
          part
        )
      )}
    </span>
  );
};

export default MessageHighlight;