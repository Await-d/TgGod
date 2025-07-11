import React from 'react';
import { Space, Typography } from 'antd';
import './MessageReactions.css';

const { Text } = Typography;

interface MessageReactionsProps {
  reactions: Record<string, number>;
  isMobile?: boolean;
}

const MessageReactions: React.FC<MessageReactionsProps> = ({
  reactions,
  isMobile = false
}) => {
  // 如果没有反应，不渲染组件
  if (!reactions || Object.keys(reactions).length === 0) {
    return null;
  }

  // 按反应数量排序
  const sortedReactions = Object.entries(reactions)
    .filter(([emoji, count]) => count > 0)
    .sort(([, a], [, b]) => b - a);

  if (sortedReactions.length === 0) {
    return null;
  }

  return (
    <div className={`message-reactions ${isMobile ? 'mobile' : ''}`}>
      <Space wrap size={isMobile ? 4 : 6}>
        {sortedReactions.map(([emoji, count]) => (
          <div key={emoji} className="reaction-item">
            <span className="reaction-emoji">{emoji}</span>
            <Text className="reaction-count">{count}</Text>
          </div>
        ))}
      </Space>
    </div>
  );
};

export default MessageReactions;