import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Space, Button, Empty, Spin, Typography, message as antMessage } from 'antd';
import { 
  ReloadOutlined, 
  SyncOutlined, 
  SettingOutlined,
  ArrowDownOutlined 
} from '@ant-design/icons';
import { TelegramGroup, TelegramMessage } from '../../types';
import MessageBubble from './MessageBubble';
import MessageHeader from './MessageHeader';
import { messageApi, telegramApi } from '../../services/apiService';
import { useTelegramStore, useAuthStore, useTelegramUserStore } from '../../store';
import './MessageArea.css';

const { Text } = Typography;

interface MessageAreaProps {
  selectedGroup: TelegramGroup | null;
  onReply: (message: TelegramMessage) => void;
  onCreateRule: (message: TelegramMessage) => void;
  searchFilter?: any;
  isMobile?: boolean;
  searchQuery?: string;
  onQuote?: (message: TelegramMessage) => void;
  onForward?: (message: TelegramMessage, targets: string[], comment?: string) => void;
  contacts?: any[];
  // 新增：无限滚动相关属性
  messages?: TelegramMessage[];
  isLoadingMore?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  containerRef?: React.RefObject<HTMLDivElement>;
  // 新增：跳转到消息功能
  jumpToMessageId?: number | null;
  onJumpComplete?: () => void;
}

const MessageArea: React.FC<MessageAreaProps> = ({
  selectedGroup,
  onReply,
  onCreateRule,
  searchFilter = {},
  isMobile = false,
  searchQuery = '',
  onQuote,
  onForward,
  contacts = [],
  // 新增属性
  messages: propMessages,
  isLoadingMore: propIsLoadingMore = false,
  hasMore: propHasMore = true,
  onLoadMore,
  containerRef: propContainerRef,
  // 跳转功能
  jumpToMessageId,
  onJumpComplete
}) => {
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const [highlightedMessageId, setHighlightedMessageId] = useState<number | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const internalContainerRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = propContainerRef || internalContainerRef;
  
  // 消息引用映射 - 用于跳转到特定消息
  const messageRefs = useRef<Record<number, HTMLDivElement>>({});
  
  // 使用传入的消息或store中的消息
  const { messages: storeMessages, setMessages, addMessage, removeMessage } = useTelegramStore();
  const displayMessages = propMessages || storeMessages;
  
  // 使用传入的加载状态或内部状态
  const isLoadingMore = propIsLoadingMore || loadingMore;
  const hasMoreMessages = propHasMore && hasMore;
  const { user } = useAuthStore();
  const { currentTelegramUser, setCurrentTelegramUser } = useTelegramUserStore();
  const PAGE_SIZE = 50;

  // 获取当前 Telegram 用户信息
  const fetchCurrentTelegramUser = useCallback(async () => {
    if (currentTelegramUser) return; // 如果已经有了，就不重复获取
    
    try {
      const telegramUser = await telegramApi.getCurrentTelegramUser();
      setCurrentTelegramUser(telegramUser);
    } catch (error: any) {
      console.error('获取当前 Telegram 用户信息失败:', error);
      // 如果获取失败，我们继续使用原有的逻辑（基于系统用户信息判断）
    }
  }, [currentTelegramUser, setCurrentTelegramUser]);

  // 组件初始化时获取当前 Telegram 用户信息
  useEffect(() => {
    fetchCurrentTelegramUser();
  }, [fetchCurrentTelegramUser]);

  // 跳转到特定消息
  const jumpToMessage = useCallback((messageId: number) => {
    try {
      const messageElement = messageRefs.current[messageId];
      if (messageElement && messagesContainerRef.current) {
        // 使用更安全的滚动方法
        const container = messagesContainerRef.current;
        const elementRect = messageElement.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        
        // 计算目标滚动位置
        const targetScrollTop = container.scrollTop + elementRect.top - containerRect.top - (containerRect.height / 2) + (elementRect.height / 2);
        
        // 平滑滚动
        container.scrollTo({
          top: Math.max(0, targetScrollTop),
          behavior: 'smooth'
        });
        
        // 高亮显示消息
        setHighlightedMessageId(messageId);
        
        // 3秒后取消高亮
        const highlightTimer = setTimeout(() => {
          setHighlightedMessageId(null);
        }, 3000);
        
        // 调用完成回调
        if (onJumpComplete) {
          try {
            onJumpComplete();
          } catch (error) {
            console.warn('跳转完成回调执行失败:', error);
          }
        }
        
        // 清理定时器的引用
        return () => clearTimeout(highlightTimer);
      }
    } catch (error) {
      console.error('消息跳转失败:', error);
      // 降级方案：直接调用完成回调
      if (onJumpComplete) {
        try {
          onJumpComplete();
        } catch (callbackError) {
          console.warn('跳转完成回调执行失败:', callbackError);
        }
      }
    }
  }, [messagesContainerRef, onJumpComplete]);

  // 监听跳转请求
  useEffect(() => {
    if (jumpToMessageId) {
      // 延迟执行，确保消息已渲染
      const timer = setTimeout(() => {
        jumpToMessage(jumpToMessageId);
      }, 100);
      
      return () => clearTimeout(timer);
    }
  }, [jumpToMessageId, jumpToMessage]);

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    setShowScrollToBottom(false);
  }, []);

  // 检查是否需要显示"滚动到底部"按钮
  const handleScroll = useCallback(() => {
    if (!messagesContainerRef.current) return;
    
    const container = messagesContainerRef.current;
    const isNearBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 200;
    setShowScrollToBottom(!isNearBottom);
  }, []);

  // 获取消息列表
  const fetchMessages = useCallback(async (
    groupId: number, 
    pageNum: number = 1, 
    filters: any = {},
    append: boolean = false
  ) => {
    if (!groupId) return;
    
    const loadingState = pageNum === 1 ? setLoading : setLoadingMore;
    loadingState(true);
    
    try {
      const skip = (pageNum - 1) * PAGE_SIZE;
      const params = {
        skip,
        limit: PAGE_SIZE,
        ...filters,
      };
      
      const response = await messageApi.getGroupMessages(groupId, params);
      
      if (append && pageNum > 1) {
        // 如果是追加模式，需要将新消息添加到现有消息列表
        const currentMessages = displayMessages;
        setMessages([...currentMessages, ...response]);
      } else {
        setMessages(response);
        // 新消息加载后滚动到底部
        setTimeout(scrollToBottom, 100);
      }
      
      // 检查是否还有更多消息
      if (response.length < PAGE_SIZE) {
        setHasMore(false);
      } else {
        setHasMore(true);
      }
      
      setPage(pageNum);
    } catch (error: any) {
      antMessage.error('获取消息失败: ' + error.message);
      console.error('获取消息失败:', error);
    } finally {
      loadingState(false);
    }
  }, [setMessages, PAGE_SIZE, scrollToBottom]);

  // 加载更多消息
  const loadMoreMessages = useCallback(async () => {
    if (!selectedGroup || loadingMore || !hasMore) return;
    
    await fetchMessages(selectedGroup.id, page + 1, searchFilter, true);
  }, [selectedGroup, loadingMore, hasMore, page, searchFilter, fetchMessages]);

  // 刷新消息
  const refreshMessages = useCallback(async () => {
    if (!selectedGroup) return;
    
    setPage(1);
    setHasMore(true);
    await fetchMessages(selectedGroup.id, 1, searchFilter);
  }, [selectedGroup, searchFilter, fetchMessages]);

  // 同步消息
  const syncMessages = useCallback(async () => {
    if (!selectedGroup) return;
    
    try {
      await telegramApi.syncGroupMessages(selectedGroup.id, 100);
      antMessage.success('消息同步成功！');
      await refreshMessages();
    } catch (error: any) {
      antMessage.error('同步消息失败: ' + error.message);
      console.error('同步消息失败:', error);
    }
  }, [selectedGroup, refreshMessages]);

  // 删除消息
  const handleDeleteMessage = useCallback(async (messageId: number) => {
    if (!selectedGroup) return;
    
    try {
      await messageApi.deleteMessage(selectedGroup.id, messageId);
      antMessage.success('消息删除成功！');
      removeMessage(messageId);
    } catch (error: any) {
      antMessage.error('删除消息失败: ' + error.message);
      console.error('删除消息失败:', error);
    }
  }, [selectedGroup, removeMessage]);

  // 当选择群组变化时重新加载消息
  useEffect(() => {
    if (selectedGroup) {
      setPage(1);
      setHasMore(true);
      fetchMessages(selectedGroup.id, 1, searchFilter);
    } else {
      setMessages([]);
    }
  }, [selectedGroup, fetchMessages, searchFilter, setMessages]);

  // 获取当前 Telegram 用户信息
  useEffect(() => {
    fetchCurrentTelegramUser();
  }, [fetchCurrentTelegramUser]);

  // 添加滚动监听
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);

  // 处理滚动加载更多
  const handleScrollToTop = useCallback(() => {
    if (!messagesContainerRef.current) return;
    
    const container = messagesContainerRef.current;
    if (container.scrollTop <= 100 && hasMore && !loadingMore) {
      loadMoreMessages();
    }
  }, [hasMore, loadingMore, loadMoreMessages]);

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScrollToTop);
      return () => container.removeEventListener('scroll', handleScrollToTop);
    }
  }, [handleScrollToTop]);

  // 渲染空状态
  if (!selectedGroup) {
    return (
      <div className="message-area-empty">
        <Empty
          description="请选择一个群组开始查看消息"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </div>
    );
  }

  return (
    <div className="message-area">
      {/* 消息头部 */}
      <MessageHeader
        group={selectedGroup}
        onRefresh={refreshMessages}
        onSync={syncMessages}
        onJumpToMessage={jumpToMessage}
        loading={loading}
        isMobile={isMobile}
      />

      {/* 消息列表 */}
      <div 
        className="message-list" 
        ref={messagesContainerRef}
      >
        {/* 加载更多指示器 - 显示在顶部，优化版本 */}
        {isLoadingMore && (
          <div className="load-more-indicator">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Spin size="small" />
              <Text type="secondary">正在加载历史消息...</Text>
            </div>
            {/* 骨架屏效果 */}
            <div className="loading-skeleton">
              <div className="loading-skeleton-item"></div>
              <div className="loading-skeleton-item"></div>
              <div className="loading-skeleton-item"></div>
            </div>
          </div>
        )}
        
        {/* 消息列表 */}
        {loading && displayMessages.length === 0 ? (
          <div className="message-loading">
            <Spin size="large" />
            <Text type="secondary">加载消息中...</Text>
          </div>
        ) : displayMessages.length === 0 ? (
          <div className="message-empty">
            <Empty
              description="暂无消息"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
              <Button 
                type="primary" 
                icon={<SyncOutlined />}
                onClick={syncMessages}
              >
                同步消息
              </Button>
            </Empty>
          </div>
        ) : (
          <>
            {!hasMoreMessages && displayMessages.length > 0 && (
              <div className="no-more-messages">
                <Text type="secondary">没有更多消息了</Text>
              </div>
            )}
            
            {displayMessages.map((message, index) => {
              const prevMessage = index > 0 ? displayMessages[index - 1] : null;
              const showAvatar = !prevMessage || 
                prevMessage.sender_id !== message.sender_id ||
                (new Date(message.date).getTime() - new Date(prevMessage.date).getTime()) > 300000; // 5分钟
              
              // 判断消息是否为当前用户发送的
              // 优先使用 Telegram 用户信息，如果没有则回退到系统用户信息
              const isOwn = currentTelegramUser ? (
                // 使用 Telegram 用户信息进行判断
                (message.sender_id && message.sender_id === currentTelegramUser.id) ||
                (message.sender_username && currentTelegramUser.username && 
                 message.sender_username.toLowerCase() === currentTelegramUser.username.toLowerCase()) ||
                (message.sender_name && currentTelegramUser.full_name && 
                 message.sender_name === currentTelegramUser.full_name)
              ) : user ? (
                // 回退到系统用户信息进行判断
                (message.sender_username && message.sender_username === user.username) ||
                (message.sender_id && message.sender_id === user.id) ||
                (message.sender_name && user.full_name && message.sender_name === user.full_name) ||
                (message.sender_username && user.username && 
                 message.sender_username.toLowerCase() === user.username.toLowerCase())
              ) : (
                // 如果都没有，临时通过消息特征判断（比如消息是否标记为"已发送"等）
                false // 暂时设为false，确保不会错误显示
              );
              
              // 调试用：每隔几条消息显示一条作为"自己的"消息，用于测试样式
              const debugIsOwn = isOwn || (index % 5 === 0); // 每5条消息中有1条显示为自己的
              
              // 检查是否为高亮消息
              const isHighlighted = highlightedMessageId === message.message_id;
              
              return (
                <div
                  key={message.id}
                  ref={el => {
                    if (el) {
                      messageRefs.current[message.message_id] = el;
                    }
                  }}
                  className={`message-wrapper ${isHighlighted ? 'highlighted' : ''}`}
                >
                  <MessageBubble
                    message={message}
                    isOwn={debugIsOwn}
                    showAvatar={showAvatar}
                    onReply={onReply}
                    onCreateRule={onCreateRule}
                    onDelete={handleDeleteMessage}
                    isMobile={isMobile}
                  />
                </div>
              );
            })}
          </>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 滚动到底部按钮 */}
      {showScrollToBottom && (
        <div className="scroll-to-bottom">
          <Button
            type="primary"
            shape="circle"
            icon={<ArrowDownOutlined />}
            onClick={scrollToBottom}
            size="large"
          />
        </div>
      )}
    </div>
  );
};

export default MessageArea;