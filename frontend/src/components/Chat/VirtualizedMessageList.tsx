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
  // 滚动相关回调
  onScrollToTop?: () => void;
  onScrollPositionChange?: (isNearBottom: boolean) => void; // 新增：通知父组件滚动位置变化
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
  onScrollPositionChange, // 新增属性
  hasMore = false,
  isLoadingMore = false
}) => {
  const itemHeightCache = useRef<Map<number, number>>(new Map());
  const messageRefs = useRef<{ [key: number]: HTMLDivElement }>({});
  const lastScrollTopRef = useRef<number>(0);
  const [scrollDirection, setScrollDirection] = useState<'up' | 'down'>('down');
  const [isScrolledFromBottom, setIsScrolledFromBottom] = useState<boolean>(false);
  const [hasInitialized, setHasInitialized] = useState<boolean>(false); // 添加初始化状态标记
  const lastNotifiedBottomState = useRef<boolean>(true); // 跟踪上次通知的底部状态

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

  // 消息元素引用回调
  const setMessageRef = useCallback((index: number, element: HTMLDivElement | null) => {
    if (element) {
      messageRefs.current[index] = element;
    } else {
      delete messageRefs.current[index];
    }
  }, []);

  // 跳转到特定消息
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

  // 消息容器引用
  const containerRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部（仅在初始加载时）
  useEffect(() => {
    // 只在首次渲染且消息加载后执行一次
    if (!hasInitialized && containerRef.current && messages.length > 0) {
      const container = containerRef.current;

      // 使用requestAnimationFrame确保DOM已更新
      requestAnimationFrame(() => {
        console.log('VirtualizedMessageList - 初始自动滚动到底部');
        container.scrollTop = container.scrollHeight;
        // 标记为已初始化
        setHasInitialized(true);
        // 通知父组件我们在底部
        if (onScrollPositionChange) {
          onScrollPositionChange(true);
          lastNotifiedBottomState.current = true;
        }
      });
    }
  }, [messages.length, hasInitialized, onScrollPositionChange]);

  // 检测滚动位置是否在底部 - 避免在检测函数中调用状态更新
  const checkIfNearBottom = useCallback(() => {
    if (containerRef.current) {
      const container = containerRef.current;
      const threshold = 100; // 增大阈值到100px
      const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight <= threshold;

      // 调试信息
      console.log('检测滚动位置:', {
        scrollTop: container.scrollTop,
        clientHeight: container.clientHeight,
        scrollHeight: container.scrollHeight,
        isNearBottom,
        diff: container.scrollHeight - container.scrollTop - container.clientHeight
      });

      return isNearBottom;
    }
    return true;
  }, []);

  // 滚动事件处理 - 移除debounce，直接处理滚动事件
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement;
    const { scrollTop, scrollHeight, clientHeight } = target;

    // 确定滚动方向
    const direction = scrollTop > lastScrollTopRef.current ? 'down' : 'up';
    lastScrollTopRef.current = scrollTop;
    setScrollDirection(direction);

    // 检查是否在底部
    const isNearBottom = scrollHeight - scrollTop - clientHeight <= 100;

    // 如果滚动位置变化，立即更新内部状态
    if (isScrolledFromBottom !== !isNearBottom) {
      setIsScrolledFromBottom(!isNearBottom);
    }

    // 通知父组件滚动位置变化
    if (onScrollPositionChange) {
      // 特别是向上滚动时，确保通知父组件
      if (direction === 'up' && !isNearBottom) {
        console.log('向上滚动，通知不在底部');
        onScrollPositionChange(false);
        lastNotifiedBottomState.current = false;
      }
      // 向下滚动且接近底部，通知已在底部
      else if (direction === 'down' && isNearBottom && !lastNotifiedBottomState.current) {
        console.log('向下滚动到底部，通知在底部');
        onScrollPositionChange(true);
        lastNotifiedBottomState.current = true;
      }
    }

    // 检查是否滚动到顶部，触发加载更多
    if (scrollTop <= 50 && !isLoadingMore && onScrollToTop) {
      console.log('触发加载更多历史消息!');
      onScrollToTop();
    }
  }, [isLoadingMore, onScrollToTop, onScrollPositionChange, isScrolledFromBottom]);

  // 处理消息列表变化时的滚动
  useEffect(() => {
    // 只有在已初始化后才处理后续消息变化
    if (hasInitialized && containerRef.current && messages.length > 0) {
      const container = containerRef.current;

      // 检查是否在底部或接近底部
      const isNearBottom = checkIfNearBottom();

      // 如果在底部，随着新消息自动滚动
      if (isNearBottom) {
        // 使用requestAnimationFrame确保在渲染后执行
        requestAnimationFrame(() => {
          container.scrollTop = container.scrollHeight;
          // 确保父组件知道我们在底部
          if (onScrollPositionChange) {
            onScrollPositionChange(true);
            lastNotifiedBottomState.current = true;
          }
        });
      }
    }
  }, [messages.length, hasInitialized, checkIfNearBottom, onScrollPositionChange]);

  return (
    <div
      ref={containerRef}
      className="virtualized-message-container"
      style={{
        flex: 1,
        overflow: 'auto',
        position: 'relative',
        minHeight: 0, // 允许flex子元素收缩
        height: '100%', // 确保容器高度为100%
        display: 'flex',
        flexDirection: 'column',
        WebkitOverflowScrolling: 'touch' // iOS滚动流畅度
      }}
      onScroll={handleScroll}
      data-has-more={hasMore ? 'true' : 'false'}
      data-loading={isLoadingMore ? 'true' : 'false'}
      data-scroll-direction={scrollDirection} // 添加滚动方向属性
      data-near-bottom={checkIfNearBottom() ? 'true' : 'false'} // 添加是否靠近底部属性
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