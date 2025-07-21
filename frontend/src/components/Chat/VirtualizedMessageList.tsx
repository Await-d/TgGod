import React, { useRef, useEffect, useCallback, useMemo, useState } from 'react';
import { TelegramMessage } from '../../types';
import MessageBubble from './MessageBubble';
import { useVirtualScroll } from '../../hooks/useVirtualScroll';
import './VirtualizedMessageList.css';

interface VirtualizedMessageListProps {
  messages: TelegramMessage[];
  currentTelegramUser?: any;
  user?: any;
  onReply: (message: TelegramMessage) => void;
  onCreateRule: (message: TelegramMessage) => void;
  onDelete: (messageId: number) => void;
  onJumpToGroup?: (groupId: number) => void;
  onJumpToMessage?: (messageId: number) => void;
  onOpenGallery?: (message: TelegramMessage) => void;
  onUpdateDownloadState?: (messageId: number, state: any) => void;
  isMobile?: boolean;
  highlightedMessageId?: number | null;
  jumpToMessageId?: number | null;
  onJumpComplete?: () => void;
  // 新增滚动相关回调
  onScrollToTop?: () => void;
  hasMore?: boolean;
  isLoadingMore?: boolean;
}

const ESTIMATED_MESSAGE_HEIGHT = 120; // 估计的消息高度

const VirtualizedMessageList: React.FC<VirtualizedMessageListProps> = ({
  messages,
  currentTelegramUser,
  user,
  onReply,
  onCreateRule,
  onDelete,
  onJumpToGroup,
  onJumpToMessage,
  onOpenGallery,
  onUpdateDownloadState,
  isMobile = false,
  highlightedMessageId,
  jumpToMessageId,
  onJumpComplete,
  onScrollToTop,
  hasMore = false,
  isLoadingMore = false
}) => {
  const itemHeightCache = useRef<Map<number, number>>(new Map());
  const messageRefs = useRef<{ [key: number]: HTMLDivElement }>({});

  // 暂时移除虚拟滚动逻辑，使用简化实现

  // 缓存消息渲染数据，避免重复计算
  const messagesWithMetadata = useMemo(() => {
    return messages.map((message, index) => {
      const prevMessage = index > 0 ? messages[index - 1] : null;

      // 计算是否显示头像
      const showAvatar = !prevMessage ||
        prevMessage.sender_id !== message.sender_id ||
        (new Date(message.date).getTime() - new Date(prevMessage.date).getTime()) > 180000;

      // 计算是否为自己的消息
      const isOwn = currentTelegramUser ?
        message.sender_id === currentTelegramUser.id :
        user ? message.sender_id === user.id : message.is_own_message === true;

      return {
        ...message,
        showAvatar,
        isOwn,
        index
      };
    });
  }, [messages, currentTelegramUser, user]);

  // 暂时移除高度变化处理

  // 消息元素引用回调
  const setMessageRef = useCallback((index: number, element: HTMLDivElement | null) => {
    if (element) {
      messageRefs.current[index] = element;
    } else {
      delete messageRefs.current[index];
    }
  }, []);

  // 跳转到特定消息（简化实现）
  useEffect(() => {
    if (jumpToMessageId && onJumpComplete && containerRef.current) {
      const messageElement = messageRefs.current[messages.findIndex(msg => msg.id === jumpToMessageId)];
      if (messageElement) {
        messageElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => {
          onJumpComplete();
        }, 300);
      }
    }
  }, [jumpToMessageId, messages, onJumpComplete]);

  // 移除虚拟滚动相关的渲染函数

  // 消息容器引用，用于滚动控制
  const containerRef = useRef<HTMLDivElement>(null);

  // 保存滚动位置状态
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);

  // 检测滚动位置是否在底部
  const checkIfAtBottom = useCallback(() => {
    if (containerRef.current) {
      const container = containerRef.current;
      const threshold = 50; // 50px阈值
      const atBottom = container.scrollHeight - container.scrollTop - container.clientHeight <= threshold;
      setIsAtBottom(atBottom);
      setShouldAutoScroll(atBottom);
    }
  }, []);

  // 滚动事件处理
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement;
    const { scrollTop } = target;

    // 检测是否在底部
    checkIfAtBottom();

    // 检查是否滚动到顶部，触发加载更多
    if (scrollTop <= 50 && hasMore && !isLoadingMore && onScrollToTop) {
      onScrollToTop();
    }
  }, [hasMore, isLoadingMore, onScrollToTop, checkIfAtBottom]);

  // 自动滚动到底部（只在初始加载或用户在底部时）
  useEffect(() => {
    if (containerRef.current && messages.length > 0 && shouldAutoScroll) {
      const container = containerRef.current;
      // 延迟滚动，确保DOM更新完成
      setTimeout(() => {
        container.scrollTop = container.scrollHeight;
      }, 100);
    }
  }, [messages.length, shouldAutoScroll]);

  // 临时简化实现：直接渲染所有消息，避免虚拟滚动复杂性导致的布局问题
  return (
    <div
      ref={containerRef}
      className="virtualized-message-container"
      style={{
        flex: 1,
        overflow: 'auto',
        position: 'relative',
        minHeight: 0 // 重要：允许flex子元素收缩
      }}
      onScroll={handleScroll}
    >
      {/* 直接渲染所有消息 */}
      {messagesWithMetadata.map((messageData, index) => {
        const isHighlighted = highlightedMessageId === messageData.id;

        return (
          <div
            key={`message-${messageData.id}`}
            ref={(el) => setMessageRef(index, el)}
            className={`simple-message-item ${isHighlighted ? 'highlighted' : ''}`}
            style={{ width: '100%', padding: '4px 0' }}
          >
            <MessageBubble
              message={messageData}
              showAvatar={messageData.showAvatar}
              isOwn={messageData.isOwn}
              onReply={onReply}
              onCreateRule={onCreateRule}
              onDelete={onDelete}
              onJumpToGroup={onJumpToGroup}
              onJumpToMessage={onJumpToMessage}
              onOpenGallery={onOpenGallery}
              onUpdateDownloadState={onUpdateDownloadState}
              isMobile={isMobile}
            />
          </div>
        );
      })}
    </div>
  );
};

// 使用 React.memo 优化重新渲染
export default React.memo(VirtualizedMessageList);