import React, { useRef, useEffect, useCallback, useMemo, useState, forwardRef, useImperativeHandle } from 'react';
import { TelegramMessage } from '../../types';
import MessageBubble from './MessageBubble';
import MessageGroupBubble from './MessageGroupBubble';
// import { useVirtualScroll } from '../../hooks/useVirtualScroll';
import { Typography } from 'antd';
import './VirtualizedMessageList.css';

const { Text } = Typography;

// 向外部暴露的方法接口
export interface VirtualizedMessageListRef {
  scrollToBottom: () => void;
}

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
  onScrollPositionChange?: (isNearBottom: boolean, containerInfo?: {
    scrollTop: number;
    clientHeight: number;
    scrollHeight: number;
    hasScrollableContent: boolean;
  }) => void;
  hasMore?: boolean;
  isLoadingMore?: boolean;
  // 🔥 新增：批量下载相关属性
  selectionMode?: boolean;
  selectedMessages?: Set<number>;
  onMessageSelect?: (messageId: number) => void;
}

// const ESTIMATED_MESSAGE_HEIGHT = 120; // 估计的消息高度

// 消息分组接口
interface MessageGroup {
  id: string; // 分组ID
  messages: TelegramMessage[]; // 分组中的消息
  primaryMessage: TelegramMessage; // 主消息（用于显示发送者信息等）
  timestamp: string; // 分组时间戳
}

// 将消息按照相同的原始消息进行分组
const groupMessages = (messages: TelegramMessage[]): MessageGroup[] => {
  if (messages.length === 0) return [];
  
  const groups = new Map<string, TelegramMessage[]>();
  
  messages.forEach(message => {
    let groupKey: string;
    
    // 根据Telegram官方的分组标识来分组：
    // 1. 如果有media_group_id，使用media_group_id作为分组键（Telegram官方的多媒体消息分组）
    // 2. 如果没有media_group_id，每条消息单独成组
    if (message.media_group_id) {
      groupKey = `media_group_${message.media_group_id}`;
    } else {
      // 每条消息单独成组
      groupKey = `single_${message.id}_${message.message_id}`;
    }
    
    if (!groups.has(groupKey)) {
      groups.set(groupKey, []);
    }
    groups.get(groupKey)!.push(message);
  });
  
  // 将分组转换为MessageGroup对象
  return Array.from(groups.entries()).map(([groupId, groupMessages]) => {
    // 按时间排序，第一条作为主消息
    const sortedMessages = groupMessages.sort((a, b) => 
      new Date(a.date).getTime() - new Date(b.date).getTime()
    );
    
    return {
      id: groupId,
      messages: sortedMessages,
      primaryMessage: sortedMessages[0],
      timestamp: sortedMessages[0].date
    };
  }).sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
};

const VirtualizedMessageList = forwardRef<VirtualizedMessageListRef, VirtualizedMessageListProps>((
  {
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
    onScrollPositionChange,
    hasMore = false,
    isLoadingMore = false,
    // 🔥 新增：批量下载相关props
    selectionMode = false,
    selectedMessages = new Set<number>(),
    onMessageSelect
  },
  ref
) => {
  const messageRefs = useRef<{ [key: number]: HTMLDivElement }>({});
  const lastScrollTopRef = useRef<number>(0);
  const [scrollDirection, setScrollDirection] = useState<'up' | 'down'>('down');
  const [isScrolledFromBottom, setIsScrolledFromBottom] = useState<boolean>(false);
  const [hasInitialized, setHasInitialized] = useState<boolean>(false); // 添加初始化状态标记
  const lastNotifiedBottomState = useRef<boolean>(true); // 跟踪上次通知的底部状态

  // 缓存消息分组数据，避免重复计算
  const messageGroups = useMemo(() => {
    return groupMessages(messages);
  }, [messages]);

  // 缓存消息渲染数据，避免重复计算
  const messagesWithMetadata = useMemo(() => {
    return messageGroups.map((group, index) => {
      const prevGroup = index > 0 ? messageGroups[index - 1] : null;

      // 计算是否显示头像
      const showAvatar = !prevGroup ||
        prevGroup.primaryMessage.sender_id !== group.primaryMessage.sender_id ||
        (new Date(group.timestamp).getTime() - new Date(prevGroup.timestamp).getTime()) > 180000;

      // 计算是否为自己的消息
      const isOwn = currentTelegramUser ?
        group.primaryMessage.sender_id === currentTelegramUser.id :
        user ? group.primaryMessage.sender_id === user.id : group.primaryMessage.is_own_message === true;

      return {
        ...group,
        showAvatar,
        isOwn,
        index
      };
    });
  }, [messageGroups, currentTelegramUser, user]);

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
    if (jumpToMessageId && containerRef.current) {
      console.log('尝试跳转到消息ID:', jumpToMessageId);

      // 查找消息在数组中的索引
      const messageIndex = messages.findIndex(msg => msg.id === jumpToMessageId);

      if (messageIndex !== -1) {
        // 如果找到消息引用
        const messageElement = messageRefs.current[messageIndex];

        if (messageElement) {
          console.log('找到消息元素，准备滚动到视图中');
          // 滚动到目标消息
          messageElement.scrollIntoView({ behavior: 'smooth', block: 'center' });

          // 添加高亮效果
          messageElement.classList.add('message-highlight-animation');

          // 移除高亮效果
          setTimeout(() => {
            messageElement.classList.remove('message-highlight-animation');
            // 通知跳转完成
            if (onJumpComplete) {
              onJumpComplete();
            }
          }, 2000);
        } else {
          console.error('消息元素不存在，无法跳转');
          if (onJumpComplete) {
            onJumpComplete();
          }
        }
      } else {
        console.error('未找到目标消息ID:', jumpToMessageId);
        if (onJumpComplete) {
          onJumpComplete();
        }
      }
    }
  }, [jumpToMessageId, messages, onJumpComplete]);

  // 消息容器引用
  const containerRef = useRef<HTMLDivElement>(null);

  // 向外暴露方法
  useImperativeHandle(ref, () => ({
    scrollToBottom: () => {
      if (containerRef.current) {
        const container = containerRef.current;

        try {
          // 方法1: 设置scrollTop
          container.scrollTop = container.scrollHeight * 2;

          // 方法2: 使用scrollTo
          container.scrollTo({
            top: container.scrollHeight * 2,
            behavior: 'auto'
          });
        } catch (error) {
          console.error('滚动失败:', error);
        }
      }
    }
  }));

  // 自动滚动到底部（仅在初始加载时）
  useEffect(() => {
    // 只在首次渲染且消息加载后执行一次
    if (!hasInitialized && containerRef.current && messages.length > 0) {
      const container = containerRef.current;

      // 使用requestAnimationFrame确保DOM已更新
      requestAnimationFrame(() => {
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
  }, [messages, hasInitialized, onScrollPositionChange]);

  // 检测滚动位置是否在底部
  const checkIfNearBottom = useCallback(() => {
    if (!containerRef.current) return true;

    const container = containerRef.current;
    const threshold = 100; // 增大阈值到100px

    // 计算是否位于底部
    const scrollDistance = container.scrollHeight - container.scrollTop - container.clientHeight;
    const isNearBottom = scrollDistance <= threshold;

    return isNearBottom;
  }, []);

  // 修复的滚动事件处理 - 防止无限循环
  const lastScrollToTopTrigger = useRef<number>(0);
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;

    const target = e.target as HTMLDivElement;
    const { scrollTop, scrollHeight, clientHeight } = target;

    // 确定滚动方向
    const direction = scrollTop > lastScrollTopRef.current ? 'down' : 'up';
    lastScrollTopRef.current = scrollTop;
    setScrollDirection(direction);

    // 检查是否在底部
    const scrollDistance = scrollHeight - scrollTop - clientHeight;
    const isNearBottom = scrollDistance <= 100;
    const hasScrollableContent = scrollHeight > clientHeight + 20;

    // 如果滚动位置变化，更新内部状态
    const newScrolledFromBottom = !isNearBottom && hasScrollableContent;
    if (isScrolledFromBottom !== newScrolledFromBottom) {
      setIsScrolledFromBottom(newScrolledFromBottom);
    }

    // 通知父组件滚动位置变化 - 传递完整的容器信息
    if (onScrollPositionChange) {
      // 向上滚动且不在底部，确保通知
      if ((direction === 'up' && !isNearBottom) ||
        // 或者状态变化时通知
        lastNotifiedBottomState.current !== isNearBottom) {

        onScrollPositionChange(isNearBottom, {
          scrollTop,
          clientHeight,
          scrollHeight,
          hasScrollableContent
        });
        lastNotifiedBottomState.current = isNearBottom;
      }
    }

    // 检查是否滚动到顶部，触发加载更多 - 修复无限循环
    const now = Date.now();
    const timeSinceLastTrigger = now - lastScrollToTopTrigger.current;
    
    if (scrollTop <= 30 && // 减小触发范围
        direction === 'up' && // 只在向上滚动时触发
        !isLoadingMore && 
        onScrollToTop && 
        timeSinceLastTrigger > 2000 && // 增加防抖时间
        hasScrollableContent) { // 确保有滚动内容
      
      console.log('[VirtualizedMessageList] 触发加载更多', {
        scrollTop,
        direction,
        timeSinceLastTrigger,
        hasScrollableContent
      });
      
      lastScrollToTopTrigger.current = now;
      onScrollToTop();
    }
  }, [isLoadingMore, onScrollToTop, onScrollPositionChange, isScrolledFromBottom]);

  // 处理消息列表变化时的滚动 - 修复历史消息加载后不应跳到底部
  const previousMessageCount = useRef(0);
  const lastMessageId = useRef<number | null>(null);
  
  useEffect(() => {
    // 只有在已初始化后才处理后续消息变化
    if (hasInitialized && containerRef.current && messages.length > 0) {
      const container = containerRef.current;
      const currentCount = messages.length;
      const currentLastMessage = messages[messages.length - 1];
      const currentLastMessageId = currentLastMessage?.id || currentLastMessage?.message_id;
      
      // 检查是否是新消息（最后一条消息变化）还是历史消息（只是数量增加）
      const isNewMessage = currentLastMessageId !== lastMessageId.current && 
                           currentCount > previousMessageCount.current;
      
      // 检查是否在底部或接近底部
      const isNearBottom = checkIfNearBottom();
      
      // 只在有新消息且用户在底部时才自动滚动到底部
      if (isNewMessage && isNearBottom) {
        console.log('[VirtualizedMessageList] 检测到新消息且用户在底部，自动滚动', {
          isNewMessage,
          isNearBottom,
          currentLastMessageId,
          lastMessageId: lastMessageId.current
        });
        
        // 使用requestAnimationFrame确保在渲染后执行
        requestAnimationFrame(() => {
          container.scrollTop = container.scrollHeight;
          // 确保父组件知道我们在底部
          if (onScrollPositionChange) {
            onScrollPositionChange(true);
            lastNotifiedBottomState.current = true;
          }
        });
      } else if (currentCount > previousMessageCount.current && !isNewMessage) {
        console.log('[VirtualizedMessageList] 检测到历史消息加载，不滚动到底部', {
          currentCount,
          previousCount: previousMessageCount.current,
          isNewMessage,
          currentLastMessageId,
          lastMessageId: lastMessageId.current
        });
      }
      
      // 更新状态
      previousMessageCount.current = currentCount;
      lastMessageId.current = currentLastMessageId;
    }
  }, [messages, hasInitialized, checkIfNearBottom, onScrollPositionChange]);

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
      {/* "没有更多消息了"提示 - 只有当消息不为空且没有更多消息时显示 */}
      {!hasMore && messages.length > 0 && (
        <div className="no-more-messages" style={{
          textAlign: 'center',
          padding: '16px',
          position: 'relative',
          borderBottom: '1px solid #f0f0f0',
          background: '#f9f9f9'
        }}>
          <Text type="secondary">没有更多消息了</Text>
        </div>
      )}

      {/* 渲染消息组 */}
      {messagesWithMetadata.map((groupData, index) => {
        const isHighlighted = highlightedMessageId === groupData.primaryMessage.id;

        return (
          <div
            key={`message-group-${groupData.id}`}
            ref={(el) => setMessageRef(index, el)}
            className={`simple-message-item ${isHighlighted ? 'highlighted' : ''}`}
            style={{ width: '100%', padding: '4px 0' }}
          >
            {groupData.messages.length === 1 ? (
              // 单条消息，使用原来的MessageBubble
              <MessageBubble
                message={groupData.primaryMessage}
                showAvatar={groupData.showAvatar}
                isOwn={groupData.isOwn}
                onReply={onReply}
                onCreateRule={onCreateRule}
                onDelete={onDelete}
                onJumpToGroup={onJumpToGroup}
                onJumpToMessage={onJumpToMessage}
                onOpenGallery={onOpenGallery}
                onUpdateDownloadState={onUpdateDownloadState}
                isMobile={isMobile}
                // 🔥 新增：批量下载相关props
                selectionMode={selectionMode}
                selectedMessages={selectedMessages}
                onMessageSelect={onMessageSelect}
              />
            ) : (
              // 多条消息，使用新的MessageGroupBubble
              <MessageGroupBubble
                messages={groupData.messages}
                primaryMessage={groupData.primaryMessage}
                showAvatar={groupData.showAvatar}
                isOwn={groupData.isOwn}
                onReply={onReply}
                onCreateRule={onCreateRule}
                onDelete={onDelete}
                onJumpToGroup={onJumpToGroup}
                onJumpToMessage={onJumpToMessage}
                onOpenGallery={onOpenGallery}
                onUpdateDownloadState={onUpdateDownloadState}
                isMobile={isMobile}
                // 🔥 新增：批量下载相关props
                selectionMode={selectionMode}
                selectedMessages={selectedMessages}
                onMessageSelect={onMessageSelect}
              />
            )}
          </div>
        );
      })}
    </div>
  );
});

// 导出组件
export default VirtualizedMessageList;