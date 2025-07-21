import React, { useRef, useEffect, useCallback, useMemo } from 'react';
import { TelegramMessage } from '../../types';
import MessageBubble from './MessageBubble';
import { useVirtualScroll } from '../../hooks/useVirtualScroll';
import './VirtualizedMessageList.css';

interface VirtualizedMessageListProps {
  messages: TelegramMessage[];
  containerHeight: number;
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
}

const ESTIMATED_MESSAGE_HEIGHT = 120; // 估计的消息高度

const VirtualizedMessageList: React.FC<VirtualizedMessageListProps> = ({
  messages,
  containerHeight,
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
  onJumpComplete
}) => {
  const itemHeightCache = useRef<Map<number, number>>(new Map());
  const messageRefs = useRef<{ [key: number]: HTMLDivElement }>({});

  // 虚拟滚动配置
  const virtualScroll = useVirtualScroll({
    itemHeight: ESTIMATED_MESSAGE_HEIGHT,
    containerHeight,
    overscan: 3,
    totalItems: messages.length
  }) as any; // 类型扩展

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

  // 处理消息高度变化
  const handleMessageHeightChange = useCallback((index: number, height: number) => {
    if (itemHeightCache.current.get(index) !== height) {
      itemHeightCache.current.set(index, height);
      virtualScroll.updateItemHeight(index, height);
    }
  }, [virtualScroll]);

  // 消息元素引用回调
  const setMessageRef = useCallback((index: number, element: HTMLDivElement | null) => {
    if (element) {
      messageRefs.current[index] = element;
      
      // 观察元素高度变化
      const resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const height = entry.contentRect.height;
          handleMessageHeightChange(index, height);
        }
      });
      
      resizeObserver.observe(element);
      
      // 初始高度测量
      const rect = element.getBoundingClientRect();
      if (rect.height > 0) {
        handleMessageHeightChange(index, rect.height);
      }
      
      return () => {
        resizeObserver.disconnect();
      };
    } else {
      delete messageRefs.current[index];
    }
  }, [handleMessageHeightChange]);

  // 跳转到特定消息
  useEffect(() => {
    if (jumpToMessageId && onJumpComplete) {
      const messageIndex = messages.findIndex(msg => msg.id === jumpToMessageId);
      if (messageIndex >= 0) {
        virtualScroll.scrollToIndex(messageIndex);
        
        // 延迟调用完成回调，确保滚动完成
        setTimeout(() => {
          onJumpComplete();
        }, 300);
      }
    }
  }, [jumpToMessageId, messages, virtualScroll, onJumpComplete]);

  // 渲染虚拟项目
  const renderVirtualItem = useCallback((index: number) => {
    const messageData = messagesWithMetadata[index];
    if (!messageData) return null;

    const isHighlighted = highlightedMessageId === messageData.id;

    return (
      <div
        key={`message-${messageData.id}`}
        style={virtualScroll.getItemStyle(index)}
        ref={(el) => setMessageRef(index, el)}
        className={`virtual-message-item ${isHighlighted ? 'highlighted' : ''}`}
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
  }, [
    messagesWithMetadata,
    highlightedMessageId,
    virtualScroll,
    setMessageRef,
    currentTelegramUser,
    user,
    onReply,
    onCreateRule,
    onDelete,
    onJumpToGroup,
    onJumpToMessage,
    onOpenGallery,
    onUpdateDownloadState,
    isMobile
  ]);

  // 扩展容器属性以包含虚拟化内容
  const containerProps = {
    ...virtualScroll.containerProps,
    className: 'virtualized-message-container'
  };

  // 临时简化实现：直接渲染所有消息，避免虚拟滚动复杂性导致的布局问题
  return (
    <div 
      className="virtualized-message-container"
      style={{ 
        height: containerHeight,
        overflow: 'auto',
        position: 'relative'
      }}
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