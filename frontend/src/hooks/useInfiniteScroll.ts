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
  autoScrollToBottom: () => void;
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
    threshold = 50, // 减少触发距离，提升响应
    debounceDelay = 500, // 增加防抖延迟，减少频繁触发
    pageSize = 30, // 减少每页数量，加快加载速度
    maxPages = 20 // 减少最大页数，避免过多内存占用
  } = options;

  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalLoaded, setTotalLoaded] = useState(0);
  
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);
  const isLoadingRef = useRef(false);
  const lastGroupId = useRef<string | number | null>(null);

  // 重置状态
  const reset = useCallback(() => {
    setCurrentPage(1);
    setHasMore(true);
    setIsLoadingMore(false);
    setTotalLoaded(0);
    isLoadingRef.current = false;
    lastGroupId.current = selectedGroup?.id || null;
  }, [selectedGroup?.id]);

  // 当群组变化时重置 - 增加延迟避免与MessageArea冲突
  useEffect(() => {
    if (selectedGroup?.id !== lastGroupId.current) {
      reset();
      // 新群组时，延迟更长时间再开始监听滚动，让MessageArea先完成初始消息加载
      const timer = setTimeout(() => {
        (window as any)._scrollReady = true;
      }, 2000); // 增加到2秒，确保MessageArea完成初始加载
      
      return () => clearTimeout(timer);
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

  // 保持滚动位置（加载新消息后）- 优化版本
  const maintainScrollPosition = useCallback((previousScrollHeight: number, previousScrollTop: number) => {
    if (containerRef.current) {
      const container = containerRef.current;
      const newScrollHeight = container.scrollHeight;
      const scrollDiff = newScrollHeight - previousScrollHeight;
      
      // 更精确的滚动位置计算，确保不会出现负数
      const newScrollTop = Math.max(0, previousScrollTop + scrollDiff);
      
      // 禁用滚动平滑，避免影响用户体验
      container.style.scrollBehavior = 'auto';
      container.scrollTop = newScrollTop;
      
      // 标记滚动调整时间，防止触发额外的加载
      (window as any)._lastScrollAdjust = Date.now();
      
      // 恢复滚动平滑
      setTimeout(() => {
        container.style.scrollBehavior = '';
      }, 0);
      
      console.log(`滚动位置调整: ${previousScrollTop} → ${newScrollTop} (差值: ${scrollDiff})`);
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
      
      // 保存当前滚动位置和高度
      const container = containerRef.current;
      const previousScrollHeight = container?.scrollHeight || 0;
      const previousScrollTop = container?.scrollTop || 0;
      
      console.log(`加载前状态: scrollTop=${previousScrollTop}, scrollHeight=${previousScrollHeight}`);

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
          
          // 先更新消息列表
          onMessagesUpdate(updatedMessages);
          
          // 等待DOM更新后再调整滚动位置
          setTimeout(() => {
            maintainScrollPosition(previousScrollHeight, previousScrollTop);
          }, 50); // 减少延迟，提升响应速度
          
          setCurrentPage(prev => prev + 1);
          setTotalLoaded(prev => prev + newMessages.length);

          // 检查是否还有更多消息
          setHasMore(newMessages.length === pageSize);
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

  // 滚动事件处理器 - 优化版本
  const handleScroll = useCallback(() => {
    if (!containerRef.current || !selectedGroup || isLoadingRef.current || !hasMore) {
      return;
    }

    // 检查是否已经准备好处理滚动事件
    if (!(window as any)._scrollReady) {
      return;
    }

    const container = containerRef.current;
    const scrollTop = container.scrollTop;
    
    // 防止在滚动调整期间触发加载
    if (Date.now() - ((window as any)._lastScrollAdjust || 0) < 1000) {
      return;
    }
    
    // 当滚动到接近顶部时，触发加载更多
    if (scrollTop <= threshold) {
      console.log('滚动到顶部，准备加载历史消息...', { scrollTop, threshold });
      
      // 防抖处理
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
      
      debounceTimer.current = setTimeout(() => {
        // 再次检查条件，避免重复触发
        if (containerRef.current && containerRef.current.scrollTop <= threshold && !isLoadingRef.current) {
          loadMore();
        }
      }, debounceDelay);
    }
  }, [containerRef, selectedGroup, hasMore, threshold, debounceDelay, loadMore]);

  // 预加载逻辑
  const handlePreload = useCallback(() => {
    if (!containerRef.current || !hasMore || isLoadingRef.current) {
      return;
    }

    // 检查是否已经准备好处理滚动事件
    if (!(window as any)._scrollReady) {
      return;
    }

    const container = containerRef.current;
    const scrollTop = container.scrollTop;
    const scrollHeight = container.scrollHeight;
    
    // 提高预加载触发点，避免过度触发
    const preloadTriggerPoint = Math.min(scrollHeight * 0.1, 300); // 最多300px或10%的高度
    
    // 当用户滚动到预加载点时，预先加载下一页
    if (scrollTop <= preloadTriggerPoint && currentPage < maxPages) {
      // 增加额外的防抖检查
      if (Date.now() - ((window as any)._lastPreload || 0) < 2000) {
        return;
      }
      
      console.log('触发预加载...', { scrollTop, preloadTriggerPoint, currentPage });
      (window as any)._lastPreload = Date.now();
      loadMore();
    }
  }, [containerRef, hasMore, maxPages, currentPage, loadMore]);

  // 绑定滚动事件
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scrollHandler = () => {
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
    scrollToBottom,
    // 新增：自动滚动到底部方法
    autoScrollToBottom: useCallback(() => {
      if (containerRef.current) {
        setTimeout(() => {
          containerRef.current!.scrollTop = containerRef.current!.scrollHeight;
        }, 100);
      }
    }, [containerRef])
  };
};