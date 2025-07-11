import React from 'react';
import { Space, Typography } from 'antd';
import { ReactionEmoji } from '../../types';
import './MessageReactions.css';

const { Text } = Typography;

interface MessageReactionsProps {
  reactions: Record<string, number> | ReactionEmoji[] | string;
  isMobile?: boolean;
}

const MessageReactions: React.FC<MessageReactionsProps> = ({
  reactions,
  isMobile = false
}) => {
  // 如果没有反应，不渲染组件
  if (!reactions) {
    return null;
  }

  // 解析字符串格式的 ReactionEmoji
  const parseReactionString = (reactionStr: string): ReactionEmoji[] => {
    const reactionArray: ReactionEmoji[] = [];
    
    // 匹配 ReactionEmoji(emoticon='❤') 格式
    const reactionPattern = /ReactionEmoji\(emoticon='([^']+)'\)(?:\s+(\d+))?/g;
    let match;
    
    while ((match = reactionPattern.exec(reactionStr)) !== null) {
      const emoticon = match[1];
      const count = match[2] ? parseInt(match[2]) : 1;
      reactionArray.push({ emoticon, count });
    }
    
    // 如果没有匹配到标准格式，尝试直接提取表情符号
    if (reactionArray.length === 0) {
      // 匹配单独的表情符号和数字
      const simplePattern = /([^\s\d]+)\s*(\d+)?/g;
      while ((match = simplePattern.exec(reactionStr)) !== null) {
        const emoticon = match[1];
        const count = match[2] ? parseInt(match[2]) : 1;
        
        // 简单验证是否是表情符号（Unicode表情符号范围）
        if (/[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|❤|💕|💖|💗|💙|💚|💛|💜|🧡|🖤|🤍|🤎|💯|👍|👎/u.test(emoticon)) {
          reactionArray.push({ emoticon, count });
        }
      }
    }
    
    return reactionArray;
  };

  // 统一处理反应数据
  const processReactions = () => {
    let reactionData: ReactionEmoji[] = [];

    if (typeof reactions === 'string') {
      // 处理字符串格式
      reactionData = parseReactionString(reactions);
    } else if (Array.isArray(reactions)) {
      // 处理 ReactionEmoji[] 格式
      reactionData = reactions;
    } else if (typeof reactions === 'object') {
      // 处理 Record<string, number> 格式
      reactionData = Object.entries(reactions).map(([emoticon, count]) => ({
        emoticon,
        count: typeof count === 'number' ? count : 1
      }));
    }

    // 合并相同表情符号
    const reactionMap: Record<string, number> = {};
    reactionData.forEach(reaction => {
      if (reaction.emoticon) {
        reactionMap[reaction.emoticon] = (reactionMap[reaction.emoticon] || 0) + (reaction.count || 1);
      }
    });

    return Object.entries(reactionMap);
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