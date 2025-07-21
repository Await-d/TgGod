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
    console.log('原始反应字符串:', reactionStr);
    const reactionArray: ReactionEmoji[] = [];

    try {
      // 首先处理类似 "ReactionEmoji(emoticon='❤') 294" 格式
      // 将字符串分割成多行，每行单独处理
      const lines = reactionStr.split('\n');
      for (const line of lines) {
        if (!line.trim()) continue;

        // 匹配 ReactionEmoji(emoticon='❤') 294 格式
        const match = line.match(/ReactionEmoji\s*\(\s*emoticon\s*=\s*['"]([^'"]+)['"]\s*\)\s*(\d+)/);
        if (match) {
          const emoticon = match[1];
          const count = parseInt(match[2]);
          console.log('匹配到表情和数量:', { emoticon, count });
          reactionArray.push({ emoticon, count });
          continue;
        }
      }

      // 如果没有匹配到标准格式，尝试更宽松的匹配
      if (reactionArray.length === 0) {
        console.log('尝试宽松匹配...');

        // 匹配 ReactionEmoji(emoticon='❤') 格式（不带数字）
        const loosePattern = /ReactionEmoji\s*\(\s*emoticon\s*=\s*['"]([^'"]+)['"]\s*\)/g;
        const numberPattern = /(\d+)/g;

        // 先提取所有表情
        const emojis: string[] = [];
        let emojiMatch;
        while ((emojiMatch = loosePattern.exec(reactionStr)) !== null) {
          emojis.push(emojiMatch[1]);
        }

        // 再提取所有数字
        const numbers: number[] = [];
        const numberMatches = reactionStr.match(/\b(\d+)\b/g);
        if (numberMatches) {
          numbers.push(...numberMatches.map(n => parseInt(n)));
        }

        console.log('提取的表情:', emojis);
        console.log('提取的数字:', numbers);

        // 配对表情和数字
        emojis.forEach((emoji, index) => {
          const count = index < numbers.length ? numbers[index] : 1;
          reactionArray.push({ emoticon: emoji, count });
        });
      }

      // 如果还是没有匹配到，尝试直接提取表情符号
      if (reactionArray.length === 0) {
        console.log('尝试直接提取表情符号...');

        // 匹配表情符号和数字的简单格式
        const simplePattern = /([^\s\d\w()='",]+)\s*(\d+)?/g;
        let simpleMatch;
        while ((simpleMatch = simplePattern.exec(reactionStr)) !== null) {
          const emoticon = simpleMatch[1];
          const count = simpleMatch[2] ? parseInt(simpleMatch[2]) : 1;

          // 验证是否是表情符号
          if (emoticon && /[^\w\d\s]/.test(emoticon)) {
            console.log('匹配到表情符号:', { emoticon, count });
            reactionArray.push({ emoticon, count });
          }
        }
      }
    } catch (error) {
      console.error('解析表情反应时出错:', error);
    }

    console.log('最终解析结果:', reactionArray);
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