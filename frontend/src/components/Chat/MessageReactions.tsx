import React from 'react';
import { Space, Typography } from 'antd';
import { ReactionEmoji } from '../../types';
import './MessageReactions.css';

const { Text } = Typography;

interface MessageReactionsProps {
  reactions: Record<string, number> | ReactionEmoji[];
  isMobile?: boolean;
}

const MessageReactions: React.FC<MessageReactionsProps> = ({
  reactions,
  isMobile = false
}) => {
  // 如果没有反应，不渲染组件
  if (!reactions || (Array.isArray(reactions) && reactions.length === 0) || 
      (!Array.isArray(reactions) && Object.keys(reactions).length === 0)) {
    return null;
  }

  // 统一处理反应数据
  const processReactions = () => {
    if (Array.isArray(reactions)) {
      // 处理 ReactionEmoji[] 格式
      const reactionMap: Record<string, number> = {};
      reactions.forEach(reaction => {
        if (reaction.emoticon) {
          reactionMap[reaction.emoticon] = (reactionMap[reaction.emoticon] || 0) + (reaction.count || 1);
        }
      });
      return Object.entries(reactionMap);
    } else {
      // 处理 Record<string, number> 格式
      return Object.entries(reactions);
    }
  };

  // 按反应数量排序
  const sortedReactions = processReactions()
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