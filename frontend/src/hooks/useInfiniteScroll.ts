import { useEffect, useCallback, useRef, useState } from 'react';
import { TelegramMessage, TelegramGroup } from '../types';
import { messageApi } from '../services/apiService';

export interface InfiniteScrollOptions {
  threshold?: number;
  debounceDelay?: number;
  pageSize?: number;
  preloadThreshold?: number;
  maxPages?: number;
}

export interface InfiniteScrollResult {
  isLoadingMore: boolean;
  hasMore: boolean;
  currentPage: number;
  totalLoaded: number;
  loadMore: () => Promise<void>;
  reset: () => void;
  scrollToTop: () => void;
  scrollToBottom: () => void;
}

/**
 * 无限滚动 Hook
 * 支持向上滚动加载历史消息，智能预加载，滚动位置保持
 */
export const useInfiniteScroll = (
  containerRef: React.RefObject<HTMLElement>,
  selectedGroup: TelegramGroup | null,
  messages: TelegramMessage[],
  onMessagesUpdate: (messages: TelegramMessage[]) => void,
  options: InfiniteScrollOptions = {}
): InfiniteScrollResult => {
  const {
    threshold = 100, // 距离顶部多少像素时开始加载
    debounceDelay = 300, // 防抖延迟
    pageSize = 50, // 每页消息数量
    preloadThreshold = 3, // 预加载阈值（页数）
    maxPages = 50 // 最大页数限制
  } = options;

  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalLoaded, setTotalLoaded] = useState(0);
  const [lastScrollHeight, setLastScrollHeight] = useState(0);
  
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);
  const isLoadingRef = useRef(false);
  const lastGroupId = useRef<string | number | null>(null);

  // 重置状态
  const reset = useCallback(() => {
    setCurrentPage(1);
    setHasMore(true);
    setIsLoadingMore(false);
    setTotalLoaded(0);
    setLastScrollHeight(0);
    isLoadingRef.current = false;
    lastGroupId.current = selectedGroup?.id || null;
  }, [selectedGroup?.id]);

  // 当群组变化时重置
  useEffect(() => {
    if (selectedGroup?.id !== lastGroupId.current) {
      reset();
    }
  }, [selectedGroup?.id, reset]);

  // 滚动到顶部
  const scrollToTop = useCallback(() => {
    if (containerRef.current) {
      containerRef.current.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    }
  }, [containerRef]);

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    if (containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [containerRef]);

  // 保持滚动位置（加载新消息后）
  const maintainScrollPosition = useCallback((previousScrollHeight: number) => {
    if (containerRef.current) {
      const container = containerRef.current;
      const newScrollHeight = container.scrollHeight;
      const scrollDiff = newScrollHeight - previousScrollHeight;
      
      // 调整滚动位置以保持用户当前的查看位置
      container.scrollTop = container.scrollTop + scrollDiff;
    }
  }, [containerRef]);

  // 加载更多消息
  const loadMore = useCallback(async () => {
    if (!selectedGroup || isLoadingRef.current || !hasMore || currentPage >= maxPages) {
      return;
    }

    isLoadingRef.current = true;
    setIsLoadingMore(true);

    try {
      console.log(`加载第 ${currentPage + 1} 页历史消息...`);
      
      // 保存当前滚动高度
      const previousScrollHeight = containerRef.current?.scrollHeight || 0;
      setLastScrollHeight(previousScrollHeight);

      // 调用API获取历史消息
      const response = await messageApi.getGroupMessages(selectedGroup.id, {
        skip: currentPage * pageSize,
        limit: pageSize
      });

      if (response && Array.isArray(response)) {
        const newMessages = response;
        
        console.log(`成功加载 ${newMessages.length} 条历史消息`);

        if (newMessages.length > 0) {
          // 将新消息添加到现有消息的前面（因为是历史消息）
          const updatedMessages = [...newMessages.reverse(), ...messages];
          onMessagesUpdate(updatedMessages);
          
          setCurrentPage(prev => prev + 1);
          setTotalLoaded(prev => prev + newMessages.length);

          // 检查是否还有更多消息
          setHasMore(newMessages.length === pageSize);

          // 维持滚动位置
          setTimeout(() => {
            maintainScrollPosition(previousScrollHeight);
          }, 100);
        } else {
          // 没有更多消息了
          setHasMore(false);
        }
      } else {
        console.warn('加载历史消息失败: 响应格式错误');
        setHasMore(false);
      }
    } catch (error) {
      console.error('加载历史消息出错:', error);
      setHasMore(false);
    } finally {
      setIsLoadingMore(false);
      isLoadingRef.current = false;
    }
  }, [
    selectedGroup, 
    currentPage, 
    hasMore, 
    maxPages, 
    pageSize, 
    messages, 
    onMessagesUpdate, 
    containerRef,
    maintainScrollPosition
  ]);

  // 滚动事件处理器
  const handleScroll = useCallback(() => {
    if (!containerRef.current || !selectedGroup || isLoadingRef.current || !hasMore) {
      return;
    }

    const container = containerRef.current;
    const scrollTop = container.scrollTop;
    
    // 当滚动到接近顶部时，触发加载更多
    if (scrollTop <= threshold) {
      console.log('滚动到顶部，准备加载历史消息...');
      
      // 防抖处理
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
      
      debounceTimer.current = setTimeout(() => {
        loadMore();
      }, debounceDelay);
    }
  }, [containerRef, selectedGroup, hasMore, threshold, debounceDelay, loadMore]);

  // 预加载逻辑
  const handlePreload = useCallback(() => {
    if (!containerRef.current || !hasMore || isLoadingRef.current) {
      return;
    }

    const container = containerRef.current;
    const scrollTop = container.scrollTop;
    const clientHeight = container.clientHeight;
    const scrollHeight = container.scrollHeight;
    
    // 计算预加载触发点
    const preloadTriggerPoint = scrollHeight * (preloadThreshold / 10);
    
    // 当用户滚动到预加载点时，预先加载下一页
    if (scrollTop <= preloadTriggerPoint && currentPage < maxPages) {
      console.log('触发预加载...');
      loadMore();
    }
  }, [containerRef, hasMore, preloadThreshold, maxPages, currentPage, loadMore]);

  // 绑定滚动事件
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scrollHandler = (event: Event) => {
      handleScroll();
      handlePreload();
    };

    container.addEventListener('scroll', scrollHandler, { passive: true });

    return () => {
      container.removeEventListener('scroll', scrollHandler);
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [handleScroll, handlePreload, containerRef]);

  // 当消息数组变化时更新统计
  useEffect(() => {
    setTotalLoaded(messages.length);
  }, [messages.length]);

  return {
    isLoadingMore,
    hasMore,
    currentPage,
    totalLoaded,
    loadMore,
    reset,
    scrollToTop,
    scrollToBottom
  };
};