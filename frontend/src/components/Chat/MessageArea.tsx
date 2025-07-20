import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Space, Button, Empty, Spin, Typography, Badge, message as antMessage } from 'antd';
import { 
  ReloadOutlined, 
  SyncOutlined, 
  SettingOutlined,
  ArrowDownOutlined 
} from '@ant-design/icons';
import { TelegramGroup, TelegramMessage } from '../../types';
import MessageBubble from './MessageBubble';
import MessageHeader from './MessageHeader';
import PinnedMessages from './PinnedMessages';
import MediaGallery from './MediaGallery';
import { messageApi, telegramApi } from '../../services/apiService';
import { useTelegramStore, useAuthStore, useTelegramUserStore } from '../../store';
import './MessageArea.css';

const { Text } = Typography;

interface MessageAreaProps {
  selectedGroup: TelegramGroup | null;
  onReply: (message: TelegramMessage) => void;
  onCreateRule: (message: TelegramMessage) => void;
  onJumpToGroup?: (groupId: number) => void;
  searchFilter?: any;
  isMobile?: boolean;
  isTablet?: boolean;
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
  onJumpToGroup,
  searchFilter = {},
  isMobile = false,
  isTablet = false,
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
  const [unreadCount, setUnreadCount] = useState(0);
  const [buttonVisible, setButtonVisible] = useState(true);
  const [highlightedMessageId, setHighlightedMessageId] = useState<number | null>(null);
  // 移除调试用的强制显示状态
  const scrollTimeoutRef = useRef<NodeJS.Timeout>();
  
  // 媒体画廊状态
  const [galleryVisible, setGalleryVisible] = useState(false);
  const [galleryIndex, setGalleryIndex] = useState(0);
  const [galleryMessages, setGalleryMessages] = useState<TelegramMessage[]>([]);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const internalContainerRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = propContainerRef || internalContainerRef;
  
  // 消息引用映射 - 用于跳转到特定消息
  const messageRefs = useRef<Record<number, HTMLDivElement>>({});
  
  // 使用传入的消息或store中的消息
  const { messages: storeMessages, setMessages, addMessage, removeMessage, mergeMessages } = useTelegramStore();
  const displayMessages = propMessages || storeMessages;
  
  // 使用传入的加载状态或内部状态
  const isLoadingMore = propIsLoadingMore || loadingMore;
  const hasMoreMessages = propHasMore && hasMore;
  const { user } = useAuthStore();
  const { currentTelegramUser, setCurrentTelegramUser } = useTelegramUserStore();
  const PAGE_SIZE = 50;

  // 下载状态管理 - 用于跟踪媒体文件下载进度和URL
  const [downloadStates, setDownloadStates] = useState<Record<number, any>>({});

  // 更新下载状态的函数
  const updateDownloadState = useCallback((messageId: number, state: any) => {
    setDownloadStates(prev => ({
      ...prev,
      [messageId]: state
    }));
  }, []);

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
    setUnreadCount(0);
  }, []);

  // 媒体画廊相关函数
  const openMediaGallery = useCallback((targetMessage: TelegramMessage) => {
    console.log('MessageArea - openMediaGallery called', {
      targetMessage: {
        id: targetMessage.id,
        mediaType: targetMessage.media_type,
        mediaDownloaded: targetMessage.media_downloaded,
        mediaPath: targetMessage.media_path
      },
      totalDisplayMessages: displayMessages.length
    });
    
    // 筛选出所有有媒体的消息（包括正在下载或已下载的）
    const mediaMessages = displayMessages.filter(msg => {
      const hasMediaType = msg.media_type;
      const hasMediaPath = msg.media_path;
      
      // 检查是否有下载状态中的URL（适用于刚下载完成的文件）
      const messageId = msg.id || msg.message_id;
      const downloadState = downloadStates[messageId];
      const hasDownloadUrl = downloadState?.downloadUrl;
      
      return hasMediaType && (hasMediaPath || hasDownloadUrl);
    });
    
    console.log('MessageArea - filtered media messages', {
      totalMediaMessages: mediaMessages.length,
      targetMessageId: targetMessage.id,
      targetMessageHasMediaType: !!targetMessage.media_type,
      targetMessageMediaPath: targetMessage.media_path,
      targetDownloadState: downloadStates[targetMessage.id || targetMessage.message_id],
      mediaMessages: mediaMessages.map(msg => {
        const messageId = msg.id || msg.message_id;
        const downloadState = downloadStates[messageId];
        return {
          id: msg.id,
          mediaType: msg.media_type,
          mediaPath: msg.media_path,
          downloadUrl: downloadState?.downloadUrl,
          hasDownloadState: !!downloadState,
          isTargetMessage: msg.id === targetMessage.id
        };
      })
    });
    
    // 找到目标消息在媒体消息中的索引
    const targetIndex = mediaMessages.findIndex(msg => msg.id === targetMessage.id);
    
    console.log('MessageArea - target index', { targetIndex });
    
    if (targetIndex >= 0) {
      console.log('MessageArea - opening gallery', {
        galleryIndex: targetIndex,
        galleryMessagesCount: mediaMessages.length
      });
      setGalleryMessages(mediaMessages);
      setGalleryIndex(targetIndex);
      setGalleryVisible(true);
    } else {
      console.warn('MessageArea - target message not found in media messages');
    }
  }, [displayMessages, downloadStates]);

  const closeMediaGallery = useCallback(() => {
    setGalleryVisible(false);
  }, []);

  const handleGalleryIndexChange = useCallback((newIndex: number) => {
    setGalleryIndex(newIndex);
  }, []);

  // 处理跳转到消息
  const handleJumpToMessage = useCallback((messageId: number) => {
    console.log('MessageArea - handleJumpToMessage called', { messageId });
    
    // 查找目标消息在当前消息列表中的位置
    const targetMessageIndex = displayMessages.findIndex(msg => msg.id === messageId);
    
    if (targetMessageIndex >= 0) {
      const targetMessage = displayMessages[targetMessageIndex];
      console.log('MessageArea - found message in current list', {
        messageId,
        targetMessageIndex,
        targetMessage
      });
      
      // 滚动到目标消息
      const messageElement = messageRefs.current[messageId];
      if (messageElement && messagesContainerRef.current) {
        messageElement.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'center',
          inline: 'nearest'
        });
        
        // 高亮目标消息
        setHighlightedMessageId(messageId);
        
        // 3秒后移除高亮
        setTimeout(() => {
          setHighlightedMessageId(null);
        }, 3000);
        
        console.log('MessageArea - scrolled to message and highlighted');
      } else {
        console.log('MessageArea - message element not found in DOM');
      }
    } else {
      console.log('MessageArea - message not found in current list, may need to load more messages');
      // TODO: 如果消息不在当前列表中，可能需要向上加载更多消息或者使用API搜索
      // 暂时显示提示信息
      // notification.info('正在查找目标消息...');
    }
  }, [displayMessages, messagesContainerRef, messageRefs]);

  // 检查是否需要显示"滚动到底部"按钮
  const handleScroll = useCallback(() => {
    if (!messagesContainerRef.current) return;
    
    const container = messagesContainerRef.current;
    const isNearBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 100; // 减少阈值到100px
    const shouldShow = !isNearBottom;
    
    // 调试信息 - 只在状态变化时输出
    if (shouldShow !== showScrollToBottom) {
      console.log('MessageArea - scroll state changed', {
        scrollTop: container.scrollTop,
        clientHeight: container.clientHeight,
        scrollHeight: container.scrollHeight,
        threshold: container.scrollHeight - 100,
        isNearBottom,
        shouldShow,
        currentShow: showScrollToBottom
      });
    }
    
    setShowScrollToBottom(shouldShow);
    
    // 如果滚动到底部，清除未读计数
    if (isNearBottom) {
      setUnreadCount(0);
    }

    // 重置按钮可见性和超时计时器
    setButtonVisible(true);
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }
    
    // 5秒后让按钮稍微透明（如果仍不在底部）
    if (!isNearBottom) {
      scrollTimeoutRef.current = setTimeout(() => {
        setButtonVisible(false);
      }, 5000);
    }
  }, [showScrollToBottom]);

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
        // 分页加载：使用智能合并，自动去重和排序
        const currentMessages = displayMessages;
        mergeMessages([...response, ...currentMessages]);
      } else {
        // 首次加载：后端已返回正确顺序（最老消息在前，最新消息在后）
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
  }, [setMessages, scrollToBottom, displayMessages]);

  // 加载更多消息
  const loadMoreMessages = useCallback(async () => {
    if (!selectedGroup || loadingMore || !hasMore) return;
    
    await fetchMessages(selectedGroup.id, page + 1, searchFilter, true);
  }, [selectedGroup, loadingMore, hasMore, page, searchFilter]); // 移除fetchMessages依赖

  // 刷新消息
  const refreshMessages = useCallback(async () => {
    if (!selectedGroup) return;
    
    setPage(1);
    setHasMore(true);
    await fetchMessages(selectedGroup.id, 1, searchFilter);
  }, [selectedGroup, searchFilter]); // 移除fetchMessages依赖

  // 同步消息
  const syncMessages = useCallback(async () => {
    if (!selectedGroup) return;
    
    try {
      await telegramApi.syncGroupMessages(selectedGroup.id, 100);
      antMessage.success('消息同步成功！');
      // 直接调用fetchMessages而不依赖refreshMessages
      setPage(1);
      setHasMore(true);
      await fetchMessages(selectedGroup.id, 1, searchFilter);
    } catch (error: any) {
      antMessage.error('同步消息失败: ' + error.message);
      console.error('同步消息失败:', error);
    }
  }, [selectedGroup, searchFilter]); // 移除refreshMessages依赖

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

  // 当选择群组变化时重新加载消息（只依赖selectedGroup）
  useEffect(() => {
    if (selectedGroup) {
      setPage(1);
      setHasMore(true);
      fetchMessages(selectedGroup.id, 1, searchFilter);
    } else {
      setMessages([]);
    }
  }, [selectedGroup]); // 只依赖selectedGroup，避免重复触发

  // 当搜索过滤条件变化时重新加载消息（防抖处理）
  useEffect(() => {
    if (selectedGroup) {
      const timeoutId = setTimeout(() => {
        setPage(1);
        setHasMore(true);
        fetchMessages(selectedGroup.id, 1, searchFilter);
      }, 300); // 300ms防抖

      return () => clearTimeout(timeoutId);
    }
  }, [searchFilter]); // 只依赖searchFilter，防抖处理

  // 获取当前 Telegram 用户信息
  useEffect(() => {
    fetchCurrentTelegramUser();
  }, [fetchCurrentTelegramUser]);

  // 添加滚动监听
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      
      // 初始检查滚动位置
      setTimeout(() => {
        console.log('MessageArea - initial scroll check');
        handleScroll();
      }, 100);
      
      return () => {
        container.removeEventListener('scroll', handleScroll);
        // 清理定时器
        if (scrollTimeoutRef.current) {
          clearTimeout(scrollTimeoutRef.current);
        }
      };
    }
  }, [handleScroll]);

  // 组件卸载时清理定时器
  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

  // 监听新消息并更新未读计数
  const previousMessageCount = useRef(displayMessages.length);
  useEffect(() => {
    if (displayMessages.length > previousMessageCount.current) {
      // 有新消息
      const newMessageCount = displayMessages.length - previousMessageCount.current;
      if (showScrollToBottom && messagesContainerRef.current) {
        // 只有在用户不在底部时才增加未读计数
        const container = messagesContainerRef.current;
        const isNearBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 200;
        if (!isNearBottom) {
          setUnreadCount(prev => prev + newMessageCount);
        }
      }
    }
    previousMessageCount.current = displayMessages.length;
  }, [displayMessages.length, showScrollToBottom]);

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

      {/* 置顶消息 */}
      <PinnedMessages
        selectedGroup={selectedGroup}
        onJumpToMessage={jumpToMessage}
        visible={true}
        isMobile={isMobile}
        isTablet={isTablet}
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
              // 简化头像显示逻辑：相同发送者的连续消息只在第一条显示头像
              const showAvatar = !prevMessage || 
                prevMessage.sender_id !== message.sender_id ||
                (new Date(message.date).getTime() - new Date(prevMessage.date).getTime()) > 180000; // 减少到3分钟
              
              // 判断消息是否为当前用户发送的
              // 优先使用 sender_id 进行判断，这是最可靠的方式
              const isOwn = currentTelegramUser ? (
                // 使用当前 Telegram 用户的 ID 进行判断
                message.sender_id === currentTelegramUser.id
              ) : user ? (
                // 回退到系统用户信息进行判断
                message.sender_id === user.id
              ) : (
                // 如果都没有用户信息，检查后端标记的字段
                message.is_own_message === true
              );
              
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
                    isOwn={isOwn}
                    showAvatar={showAvatar}
                    onReply={onReply}
                    onCreateRule={onCreateRule}
                    onDelete={handleDeleteMessage}
                    onJumpToGroup={onJumpToGroup}
                    onJumpToMessage={handleJumpToMessage}
                    isMobile={isMobile}
                    onOpenGallery={openMediaGallery}
                    onUpdateDownloadState={updateDownloadState}
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
        <div 
          className={`scroll-to-bottom ${!buttonVisible ? 'auto-hidden' : ''}`}
          onMouseEnter={() => setButtonVisible(true)}
          style={{
            // 移除调试背景色
          }}
        >
          <Badge count={unreadCount} size="small" offset={[-5, 5]}>
            <Button
              type="primary"
              shape="circle"
              icon={<ArrowDownOutlined />}
              onClick={scrollToBottom}
              size="large"
              title={unreadCount > 0 ? `${unreadCount} 条新消息` : '回到底部'}
            />
          </Badge>
        </div>
      )}
      
      {/* 媒体画廊模态框 */}
      <MediaGallery
        messages={galleryMessages}
        currentIndex={galleryIndex}
        visible={galleryVisible}
        onClose={closeMediaGallery}
        onIndexChange={handleGalleryIndexChange}
        downloadStates={downloadStates}
      />
    </div>
  );
};

export default MessageArea;