import { useEffect, useCallback, useRef, useState } from 'react';
import { TelegramMessage, TelegramGroup } from '../types';
import { MessageFilter } from '../types/chat';
import { convertFilterToAPIParams } from '../utils/filterUtils';
import { messageApi } from '../services/apiService';

export interface InfiniteScrollOptions {
  threshold?: number;
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
  options: InfiniteScrollOptions = {},
  currentFilter: MessageFilter = {} // 新增筛选条件参数
): InfiniteScrollResult => {
  const {
    threshold = 50, // 减少触发距离，提升响应
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

  // 重置状态 - 简化版本，不依赖selectedGroup
  const reset = useCallback(() => {
    setCurrentPage(1);
    setHasMore(true);
    setIsLoadingMore(false);
    setTotalLoaded(0);
    isLoadingRef.current = false;
    lastRequestRef.current = ''; // 重置请求去重标识符
  }, []);

  // 当群组变化时重置 - 使用ref避免频繁重置
  useEffect(() => {
    const currentGroupId = selectedGroup?.id;
    
    // 如果群组ID没有变化，跳过处理
    if (currentGroupId === lastGroupId.current) {
      return;
    }
    
    console.log('[InfiniteScroll] 群组变更，重置滚动状态', {
      newGroupId: currentGroupId,
      oldGroupId: lastGroupId.current
    });
    
    // 调用重置函数
    reset();
    
    // 清理所有相关的全局状态
    (window as any)._lastLoadTrigger = 0;
    (window as any)._lastScrollAdjust = 0;
    (window as any)._lastInitialLoadTime = 0;
    
    // 如果存在容器引用，清理容器上的绑定标记
    if (containerRef.current) {
      const oldKey = `scroll_bound_${lastGroupId.current || 'unknown'}`;
      delete (containerRef.current as any)[oldKey];
      
      const newKey = `scroll_bound_${currentGroupId || 'unknown'}`;
      delete (containerRef.current as any)[newKey];
    }
    
    // 更新群组ID记录
    lastGroupId.current = currentGroupId || null;
    
    console.log('[InfiniteScroll] 滚动状态重置完成，等待消息数据加载');
  }, [selectedGroup?.id, reset, containerRef]);
  
  // 移除初始检查函数，简化逻辑，让正常的滚动事件处理即可

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

  // 增强的请求去重机制
  const lastRequestRef = useRef<string>('');
  const loadingStartTimeRef = useRef<number>(0);

  // 加载更多消息 - 增强防止循环加载
  const loadMore = useCallback(async () => {
    const now = Date.now();
    
    // 根本条件检查
    if (!selectedGroup || isLoadingRef.current || !hasMore || currentPage >= maxPages) {
      console.log('[InfiniteScroll] 跳过加载', { 
        selectedGroup: !!selectedGroup, 
        isLoading: isLoadingRef.current, 
        hasMore, 
        currentPage, 
        maxPages,
        messagesCount: messages.length 
      });
      return;
    }

    // 确保有现有消息才允许加载更多（防止与初始加载冲突）
    if (messages.length === 0) {
      console.log('[InfiniteScroll] 等待初始消息加载完成');
      return;
    }

    // 防止在短时间内重复触发加载
    if (loadingStartTimeRef.current > 0 && now - loadingStartTimeRef.current < 3000) {
      console.log('[InfiniteScroll] 防止频繁加载，距离上次加载', now - loadingStartTimeRef.current, 'ms');
      return;
    }

    // 生成请求标识符，防止重复请求
    const requestKey = `${selectedGroup.id}_${currentPage}_${pageSize}_${messages.length}`;
    if (lastRequestRef.current === requestKey) {
      console.log('[InfiniteScroll] 防止重复请求:', requestKey);
      return;
    }
    
    lastRequestRef.current = requestKey;
    isLoadingRef.current = true;
    loadingStartTimeRef.current = now;
    setIsLoadingMore(true);

    try {
      // 使用消息数量作为skip，确保不会重复获取已有消息
      const skipCount = messages.length;
      console.log(`[InfiniteScroll] 加载更多历史消息 (skip=${skipCount}, limit=${pageSize})`);
      
      // 保存当前滚动位置和高度
      const container = containerRef.current;
      const previousScrollHeight = container?.scrollHeight || 0;
      const previousScrollTop = container?.scrollTop || 0;
      
      console.log(`[InfiniteScroll] 加载前状态: scrollTop=${previousScrollTop}, scrollHeight=${previousScrollHeight}`);

      // 使用筛选条件构建API参数
      const apiParams = convertFilterToAPIParams(currentFilter, {
        skip: skipCount,
        limit: pageSize
      });

      // 调用API获取历史消息 - 使用实际消息数量作为skip
      console.log(`[InfiniteScroll] API参数:`, apiParams);
      const response = await messageApi.getGroupMessages(selectedGroup.id, apiParams);

      if (response && Array.isArray(response)) {
        const newMessages = response;
        
        console.log(`[InfiniteScroll] 成功加载 ${newMessages.length} 条历史消息`);

        if (newMessages.length > 0) {
          // 使用新的prependMessages方法，自动去重和排序
          onMessagesUpdate([...newMessages.reverse(), ...messages]);
          
          // 等待DOM更新后再调整滚动位置
          setTimeout(() => {
            maintainScrollPosition(previousScrollHeight, previousScrollTop);
          }, 50);
          
          setCurrentPage(prev => prev + 1);
          setTotalLoaded(prev => prev + newMessages.length);

          // 检查是否还有更多消息
          setHasMore(newMessages.length === pageSize);
        } else {
          // 没有更多消息了
          console.log('[InfiniteScroll] 没有更多历史消息');
          setHasMore(false);
        }
      } else {
        console.warn('[InfiniteScroll] 加载历史消息失败: 响应格式错误');
        setHasMore(false);
      }
    } catch (error) {
      console.error('[InfiniteScroll] 加载历史消息出错:', error);
      setHasMore(false);
    } finally {
      setIsLoadingMore(false);
      isLoadingRef.current = false;
      loadingStartTimeRef.current = 0;
      // 请求完成后清除标识符
      setTimeout(() => {
        if (lastRequestRef.current === requestKey) {
          lastRequestRef.current = '';
        }
      }, 2000); // 增加清除延迟
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
    maintainScrollPosition,
    currentFilter
  ]);

  // 存储 loadMore 的 ref，避免在 useEffect 中直接依赖
  const loadMoreRef = useRef(loadMore);
  loadMoreRef.current = loadMore;

  // 初始滚动检查 - 修复版本，避免循环触发
  useEffect(() => {
    if (!selectedGroup?.id || messages.length === 0 || isLoadingRef.current) return;

    const timer = setTimeout(() => {
      if (containerRef.current && selectedGroup?.id && !isLoadingRef.current) {
        const scrollTop = containerRef.current.scrollTop;
        const timeSinceLastLoad = Date.now() - ((window as any)._lastLoadTrigger || 0);

        console.log('[InfiniteScroll] 初始滚动位置检查', {
          scrollTop,
          timeSinceLastLoad,
          hasMore,
          messagesLength: messages.length
        });

        // 严格条件：只在用户明确滚动到顶部且距离上次加载超过2秒时触发
        if (scrollTop < 50 && hasMore && timeSinceLastLoad > 2000 && messages.length > 10) {
          console.log('[InfiniteScroll] 初始检查触发历史消息加载');
          (window as any)._lastLoadTrigger = Date.now();
          loadMoreRef.current();
        }
      }
    }, 1000); // 增加延迟避免初始化冲突

    return () => clearTimeout(timer);
  }, [selectedGroup?.id, hasMore, messages.length, containerRef]); // 添加必要的依赖

  // 使用ref存储当前状态避免频繁回调重建
  const scrollStateRef = useRef({
    selectedGroup,
    hasMore,
    currentPage
  });
  
  useEffect(() => {
    scrollStateRef.current = { selectedGroup, hasMore, currentPage };
  }, [selectedGroup, hasMore, currentPage]);

  // 统一的滚动事件处理器 - 修复无限循环版本
  const handleScroll = useCallback(() => {
    const container = containerRef.current;
    const { selectedGroup, hasMore, currentPage } = scrollStateRef.current;
    
    if (!container || !selectedGroup || isLoadingRef.current || !hasMore) {
      return;
    }

    const scrollTop = container.scrollTop;
    const scrollHeight = container.scrollHeight;
    const clientHeight = container.clientHeight;
    const timeSinceLastLoad = Date.now() - ((window as any)._lastLoadTrigger || 0);
    
    // 增加更严格的防抖机制
    if (timeSinceLastLoad < 2000) {
      return;
    }
    
    // 确保内容高度大于容器高度，有实际滚动空间
    if (scrollHeight <= clientHeight + 50) {
      return;
    }
    
    const topThreshold = Math.min(threshold, 30); // 减小触发区域
    
    // 更严格的触发条件：必须真正滚动到顶部
    if (scrollTop <= topThreshold && scrollTop >= 0 && currentPage < maxPages) {
      console.log(`[InfiniteScroll] 触发向上加载`, {
        scrollTop,
        topThreshold,
        currentPage,
        maxPages,
        timeSinceLastLoad,
        scrollHeight,
        clientHeight
      });
      
      // 记录触发时间
      (window as any)._lastLoadTrigger = Date.now();
      
      // 执行加载
      loadMoreRef.current();
    }
  }, [threshold, maxPages, containerRef]);

  // 绑定滚动事件 - 修复无限循环问题
  useEffect(() => {
    const container = containerRef.current;
    const groupId = selectedGroup?.id;
    
    // 如果没有容器或群组，直接返回
    if (!container || !groupId) {
      return;
    }

    // 使用更严格的重复绑定检查
    const containerKey = `scroll_bound_${groupId}`;
    if ((container as any)[containerKey]) {
      return;
    }
    
    // 标记容器已绑定事件
    (container as any)[containerKey] = true;

    // 使用节流减少触发频率
    let ticking = false;
    const scrollHandler = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          handleScroll();
          ticking = false;
        });
        ticking = true;
      }
    };

    console.log(`[InfiniteScroll] 绑定滚动事件到容器:`, container);
    container.addEventListener('scroll', scrollHandler, { passive: true });

    return () => {
      console.log('[InfiniteScroll] 移除滚动事件监听器');
      container.removeEventListener('scroll', scrollHandler);
      // 移除绑定标记
      delete (container as any)[containerKey];
      
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
        debounceTimer.current = null;
      }
    };
  }, [selectedGroup?.id, handleScroll, containerRef]);

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