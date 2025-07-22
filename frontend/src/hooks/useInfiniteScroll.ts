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

  // 重置状态 - 简化版本，不依赖selectedGroup
  const reset = useCallback(() => {
    setCurrentPage(1);
    setHasMore(true);
    setIsLoadingMore(false);
    setTotalLoaded(0);
    isLoadingRef.current = false;
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
    
    // 如果存在新群组，清除初始加载标记
    if (currentGroupId) {
      const initialLoadKey = `initial_load_${currentGroupId}`;
      sessionStorage.removeItem(initialLoadKey);
      console.log('[InfiniteScroll] 清除群组初始加载标记:', initialLoadKey);
    }
    
    console.log('[InfiniteScroll] 立即启用滚动检测');
  }, [selectedGroup?.id, reset]);
  
  // 创建一个初始检查函数
  const checkInitialScroll = useCallback(() => {
    if (containerRef.current && selectedGroup?.id) {
      const scrollTop = containerRef.current.scrollTop;
      console.log('[InfiniteScroll] 初始滚动位置检查', { scrollTop });
      
      // 检查是否已经加载过，以及是否应该加载
      const shouldLoad = scrollTop < 200 && hasMore && !isLoadingRef.current;
      
      // 添加基于时间的检查，确保短时间内不会重复触发
      const now = Date.now();
      const lastLoadTime = (window as any)._lastInitialLoadTime || 0;
      const timeSinceLastLoad = now - lastLoadTime;
      
      // 如果一开始就在顶部附近，且满足其他条件，主动加载一次历史数据
      if (shouldLoad && timeSinceLastLoad > 2000) {
        console.log('[InfiniteScroll] 初始化时接近顶部，主动加载历史数据');
        
        // 记录本次加载时间
        (window as any)._lastInitialLoadTime = now;
        
        // 使用已定义的API直接获取历史消息
        isLoadingRef.current = true;
        setIsLoadingMore(true);
        
        // 调用API获取历史消息
        messageApi.getGroupMessages(selectedGroup.id, {
          skip: currentPage * pageSize,
          limit: pageSize
        }).then(response => {
          if (response && Array.isArray(response)) {
            console.log(`[InfiniteScroll] 初始化时成功加载 ${response.length} 条历史消息`);
            if (response.length > 0) {
              // 将新消息添加到现有消息前面
              onMessagesUpdate([...response.reverse(), ...messages]);
              setCurrentPage(prev => prev + 1);
              setTotalLoaded(prev => prev + response.length);
              setHasMore(response.length === pageSize);
            } else {
              setHasMore(false);
            }
          }
        }).catch(error => {
          console.error('[InfiniteScroll] 初始化加载历史消息出错:', error);
          setHasMore(false);
        }).finally(() => {
          isLoadingRef.current = false;
          setIsLoadingMore(false);
        });
      }
    }
  }, [containerRef, selectedGroup, hasMore, currentPage, pageSize, messages, onMessagesUpdate, setIsLoadingMore]);
  
  // 分离初始加载检查，避免循环依赖
  useEffect(() => {
    if (!selectedGroup?.id) return;
    
    // 使用一个临时标记来防止循环加载
    const initialLoadKey = `initial_load_${selectedGroup.id}`;
    const hasInitialLoaded = sessionStorage.getItem(initialLoadKey);
    
    if (hasInitialLoaded !== "true") {
      // 只有在没有进行过初始加载的情况下，才进行初始加载检查
      const timer = setTimeout(checkInitialScroll, 300);
      // 标记已经进行过初始加载
      sessionStorage.setItem(initialLoadKey, "true");
      return () => clearTimeout(timer);
    }
  }, [selectedGroup?.id, checkInitialScroll]);

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
          // 使用新的prependMessages方法，自动去重和排序
          onMessagesUpdate([...newMessages.reverse(), ...messages]);
          
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

  // 使用ref存储当前状态避免频繁回调重建
  const scrollStateRef = useRef({
    selectedGroup,
    hasMore,
    currentPage
  });
  
  useEffect(() => {
    scrollStateRef.current = { selectedGroup, hasMore, currentPage };
  }, [selectedGroup, hasMore, currentPage]);

  // 统一的滚动事件处理器 - 稳定版本
  const handleScroll = useCallback(() => {
    const container = containerRef.current;
    const { selectedGroup, hasMore, currentPage } = scrollStateRef.current;
    
    if (!container || !selectedGroup || isLoadingRef.current || !hasMore) {
      return;
    }

    const scrollTop = container.scrollTop;
    const timeSinceLastLoad = Date.now() - ((window as any)._lastLoadTrigger || 0);
    
    if (timeSinceLastLoad < 1000) {
      return;
    }
    
    const topThreshold = Math.min(threshold * 2, 100);
    
    if (scrollTop <= topThreshold && currentPage < maxPages) {
      // 记录触发时间
      (window as any)._lastLoadTrigger = Date.now();
      
      // 设置正在加载标记
      isLoadingRef.current = true;
      setIsLoadingMore(true);
      
      // 直接执行加载
      loadMore().finally(() => {
        isLoadingRef.current = false;
        setIsLoadingMore(false);
      });
    }
  }, [threshold, maxPages, loadMore]);

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
  }, [selectedGroup?.id]); // 移除handleScroll依赖避免循环

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