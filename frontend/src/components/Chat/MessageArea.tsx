import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Space, Button, Empty, Spin, Typography, Badge, message as antMessage, notification } from 'antd';
import {
  ReloadOutlined,
  SyncOutlined,
  SettingOutlined,
  ArrowDownOutlined,
  DownOutlined
} from '@ant-design/icons';
import { TelegramGroup, TelegramMessage } from '../../types';
import MessageBubble from './MessageBubble';
import VirtualizedMessageList from './VirtualizedMessageList';
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
  onJumpToMessage?: (messageId: number) => void;
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
  jumpToMessageId: propJumpToMessageId,
  onJumpComplete,
  onJumpToMessage
}) => {
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [buttonVisible, setButtonVisible] = useState(true);
  const [highlightedMessageId, setHighlightedMessageId] = useState<number | null>(null);
  const [jumpToMessageId, setJumpToMessageId] = useState<number | null>(null);
  const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(true);
  const scrollTimeoutRef = useRef<NodeJS.Timeout>();
  const previousMessageCount = useRef(0); // 添加回引用，用于跟踪消息数量变化

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

  // 高度由CSS flex布局自动处理

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
    if (propJumpToMessageId) {
      // 延迟执行，确保消息已渲染
      const timer = setTimeout(() => {
        jumpToMessage(propJumpToMessageId);
        setJumpToMessageId(propJumpToMessageId); // 同步到内部状态
      }, 100);

      return () => clearTimeout(timer);
    }
  }, [propJumpToMessageId, jumpToMessage]);

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    console.log('MessageArea - 执行滚动到底部');
    try {
      if (messagesContainerRef.current) {
        const container = messagesContainerRef.current;
        console.log('开始滚动前容器状态:', {
          scrollHeight: container.scrollHeight,
          clientHeight: container.clientHeight,
          scrollTop: container.scrollTop
        });

        // 确保DOM已完全渲染
        setTimeout(() => {
          try {
            if (!messagesContainerRef.current) return;

            // 使用多种方法滚动到底部
            const container = messagesContainerRef.current;

            // 方法1: 设置scrollTop
            container.scrollTop = container.scrollHeight * 2; // 确保值足够大

            // 方法2: 使用scrollTo
            try {
              container.scrollTo({
                top: container.scrollHeight * 2,
                behavior: 'instant' // 使用即时行为
              });
            } catch (e) {
              console.warn('scrollTo方法失败:', e);
              // 回退方法
              container.scrollTop = container.scrollHeight * 2;
            }

            // 方法3: 使用scrollIntoView
            if (messagesEndRef.current) {
              try {
                messagesEndRef.current.scrollIntoView({ block: 'end', behavior: 'instant' });
              } catch (e) {
                console.warn('scrollIntoView方法失败:', e);
              }
            }

            // 检查滚动效果
            console.log('滚动后容器状态:', {
              scrollHeight: container.scrollHeight,
              clientHeight: container.clientHeight,
              scrollTop: container.scrollTop
            });

            // 更新状态
            setShowScrollToBottom(false);
            setUnreadCount(0);
          } catch (error) {
            console.error('延迟滚动失败:', error);
          }
        }, 10); // 极短延迟确保DOM已更新
      } else {
        console.error('消息容器引用为空');
      }
    } catch (error) {
      console.error('滚动到底部失败:', error);
    }
  }, []);

  // 更新滚动位置处理函数
  const handleScrollPositionChange = useCallback((isNearBottom: boolean, containerInfo?: {
    scrollTop: number;
    clientHeight: number;
    scrollHeight: number;
    hasScrollableContent: boolean;
  }) => {
    console.log('MessageArea - 收到滚动位置变化通知:', {
      isNearBottom,
      containerExists: !!messagesContainerRef.current,
      containerStats: messagesContainerRef.current ? {
        scrollHeight: messagesContainerRef.current.scrollHeight,
        clientHeight: messagesContainerRef.current.clientHeight,
        scrollTop: messagesContainerRef.current.scrollTop
      } : 'N/A',
      containerInfo // 记录传递的容器信息
    });

    // 使用传递过来的容器信息而不是messagesContainerRef
    const hasScrollableContent = containerInfo ? containerInfo.hasScrollableContent : false;

    console.log('检查是否应显示按钮:', {
      isNearBottom,
      hasScrollableContent,
      shouldShow: !isNearBottom && hasScrollableContent
    });

    setShowScrollToBottom(!isNearBottom && hasScrollableContent);
  }, []);

  // 单击事件处理 - 确保只有一个点击处理器
  const handleScrollButtonClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation(); // 阻止事件冒泡
    console.log('点击滚动按钮');
    scrollToBottom();
    return false; // 确保不会继续冒泡
  }, [scrollToBottom]);

  // 滚动到底部按钮渲染
  const renderScrollToBottomButton = () => {
    if (!showScrollToBottom) return null;

    return (
      <div
        className={`scroll-to-bottom`}
        onClick={handleScrollButtonClick}
      >
        <Badge count={unreadCount > 0 ? unreadCount : 0} overflowCount={99}>
          <Button
            type="primary"
            shape="circle"
            icon={<DownOutlined />}
            onMouseDown={(e) => e.stopPropagation()}
            onTouchStart={(e) => e.stopPropagation()}
            onClick={handleScrollButtonClick}
          />
        </Badge>
      </div>
    );
  };

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

    // 如果目标消息不在过滤后的列表中，但它有媒体类型，强制添加它
    const targetInFilteredList = mediaMessages.some(msg => msg.id === targetMessage.id);
    if (!targetInFilteredList && targetMessage.media_type) {
      console.log('MessageArea - Target message not in filtered list, adding it', {
        targetMessageId: targetMessage.id,
        mediaType: targetMessage.media_type,
        mediaPath: targetMessage.media_path,
        downloadState: downloadStates[targetMessage.id || targetMessage.message_id]
      });

      // 如果目标消息有更新的媒体路径，使用更新后的版本
      const updatedTargetMessage = targetMessage.media_path ? targetMessage : {
        ...targetMessage,
        media_path: downloadStates[targetMessage.id || targetMessage.message_id]?.downloadUrl || targetMessage.media_path,
        media_downloaded: true
      };

      // 将目标消息插入到列表开头，确保它是第一个（索引0）
      mediaMessages.unshift(updatedTargetMessage);
    } else {
      // 如果目标消息已经在列表中，确保它的媒体路径是最新的
      const targetIndex = mediaMessages.findIndex(msg => msg.id === targetMessage.id);
      if (targetIndex >= 0 && targetMessage.media_path) {
        mediaMessages[targetIndex] = {
          ...mediaMessages[targetIndex],
          media_path: targetMessage.media_path,
          media_downloaded: true
        };
      }
    }

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

    console.log('MessageArea - target index', {
      targetIndex,
      targetMessageId: targetMessage.id,
      mediaMessagesIds: mediaMessages.map(msg => msg.id),
      targetMessage: {
        id: targetMessage.id,
        mediaPath: targetMessage.media_path,
        mediaType: targetMessage.media_type
      },
      firstMessage: mediaMessages[0] ? {
        id: mediaMessages[0].id,
        mediaPath: mediaMessages[0].media_path,
        mediaType: mediaMessages[0].media_type
      } : null
    });

    if (targetIndex >= 0) {
      console.log('MessageArea - opening gallery', {
        galleryIndex: targetIndex,
        galleryMessagesCount: mediaMessages.length,
        targetMessageAtIndex: mediaMessages[targetIndex] ? {
          id: mediaMessages[targetIndex].id,
          mediaPath: mediaMessages[targetIndex].media_path
        } : null
      });
      setGalleryMessages(mediaMessages);
      setGalleryIndex(targetIndex);
      setGalleryVisible(true);
    } else {
      console.warn('MessageArea - target message not found in media messages', {
        targetMessageId: targetMessage.id,
        availableMessageIds: mediaMessages.map(msg => msg.id)
      });
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
      console.log('MessageArea - message not found in current list, delegating to parent handler');
      // 如果消息不在当前列表中，调用上级的跳转处理器
      if (onJumpToMessage) {
        console.log('MessageArea - calling parent onJumpToMessage handler');
        onJumpToMessage(messageId);
      } else {
        console.log('MessageArea - no parent handler available');
        // 显示提示信息
        notification.info({
          message: '目标消息不在当前页面，正在尝试定位...'
        });
      }
    }
  }, [displayMessages, messagesContainerRef, messageRefs, onJumpToMessage]);

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

      // 打印响应数据，便于调试
      console.log('MessageArea - fetchMessages 响应数据', {
        groupId,
        pageNum,
        append,
        responseLength: response.length,
        pageSize: PAGE_SIZE,
        hasOlderMessages: response.length === PAGE_SIZE
      });

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

      // 检查是否还有更多消息 - 除非明确获取到少于PAGE_SIZE的消息，否则总是假设还有更多
      // 这样可以确保用户可以一直上拉尝试加载，直到确认没有更多数据
      const mightHaveMore = response.length >= PAGE_SIZE;
      console.log('MessageArea - 更新hasMore状态', {
        mightHaveMore,
        responseLength: response.length,
        pageSize: PAGE_SIZE,
        currentPage: pageNum
      });
      setHasMore(mightHaveMore);

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
    if (!selectedGroup) return;

    // 移除loadingMore和hasMore条件，在这里打印日志
    console.log('MessageArea - loadMoreMessages 被调用', {
      groupId: selectedGroup.id,
      page,
      loadingMore,
      hasMore,
      searchFilter
    });

    // 即使loadingMore为true或hasMore为false也尝试加载，因为这些状态可能不准确
    if (loadingMore) {
      console.log('MessageArea - 已经在加载中，忽略重复请求');
      return;
    }

    await fetchMessages(selectedGroup.id, page + 1, searchFilter, true);
  }, [selectedGroup, loadingMore, page, searchFilter]); // 移除hasMore依赖

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
      console.log('MessageArea - 群组改变，重置状态', {
        groupId: selectedGroup.id,
        group: selectedGroup
      });
      setPage(1);
      // 始终设置为true，让用户可以尝试加载历史数据
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

  // 添加滚动监听 - 仍然保留这部分以保持兼容性，但主要逻辑通过VirtualizedMessageList组件实现
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container) {
      // 初始检查滚动位置
      setTimeout(() => {
        // 删除冗余的handleScroll函数，我们使用VirtualizedMessageList中的滚动检测
      }, 300);
    }
  }, []);

  // 初始化时确保滚动到底部
  useEffect(() => {
    // 当消息加载完成且有消息时，确保滚动到底部
    if (displayMessages.length > 0 && !loading && !isLoadingMore) {
      console.log('MessageArea - 初始滚动到底部，消息数量:', displayMessages.length);
      // 使用延时，确保DOM已经更新
      setTimeout(scrollToBottom, 100);
    }
  }, [selectedGroup, loading]); // 仅在群组变化或加载状态变化时触发

  // 监听新消息并自动滚动（如果在底部）
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container && displayMessages.length > previousMessageCount.current) {
      // 检查是否在底部或接近底部
      const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight <= 100;

      if (isNearBottom) {
        // 如果在底部，自动滚动到新消息
        console.log('MessageArea - 新消息自动滚动到底部');
        setTimeout(scrollToBottom, 50);
      } else {
        // 如果不在底部，增加未读计数
        const newCount = displayMessages.length - previousMessageCount.current;
        setUnreadCount(prev => prev + newCount);
        // 确保显示滚动按钮
        setShowScrollToBottom(true);
        setButtonVisible(true);
      }
    }

    previousMessageCount.current = displayMessages.length;
  }, [displayMessages.length, scrollToBottom]);

  // 组件卸载时清理定时器
  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

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
        messages={displayMessages}
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

            {/* 更新使用虚拟化消息列表组件，添加滚动位置变化通知 */}
            <VirtualizedMessageList
              messages={displayMessages}
              currentTelegramUser={currentTelegramUser}
              user={user}
              onReply={onReply}
              onCreateRule={onCreateRule}
              onDelete={handleDeleteMessage}
              onJumpToGroup={onJumpToGroup}
              onJumpToMessage={handleJumpToMessage}
              onOpenGallery={openMediaGallery}
              onUpdateDownloadState={updateDownloadState}
              isMobile={isMobile}
              highlightedMessageId={highlightedMessageId}
              jumpToMessageId={jumpToMessageId}
              onJumpComplete={onJumpComplete}
              onScrollToTop={loadMoreMessages}
              onScrollPositionChange={handleScrollPositionChange} // 添加滚动位置变化处理
              hasMore={hasMoreMessages}
              isLoadingMore={isLoadingMore}
            />
          </>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 滚动到底部按钮 - 仅当需要显示时才渲染 */}
      {renderScrollToBottomButton()}

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