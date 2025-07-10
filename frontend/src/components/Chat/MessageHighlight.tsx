import React from 'react';
import { Typography } from 'antd';

const { Text } = Typography;

interface MessageHighlightProps {
  content: string;
  searchTerm: string;
  className?: string;
}

const MessageHighlight: React.FC<MessageHighlightProps> = ({ 
  content, 
  searchTerm, 
  className 
}) => {
  if (!searchTerm) {
    return <span className={className}>{content}</span>;
  }

  const parts = content.split(new RegExp(`(${searchTerm})`, 'gi'));
  
  return (
    <span className={className}>
      {parts.map((part, index) => 
        part.toLowerCase() === searchTerm.toLowerCase() ? (
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