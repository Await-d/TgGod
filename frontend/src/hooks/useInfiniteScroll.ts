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

  // 当群组变化时重置 - 简化初始化逻辑
  useEffect(() => {
    if (!selectedGroup?.id || selectedGroup?.id !== lastGroupId.current) {
      console.log('[InfiniteScroll] 群组变更，重置滚动状态', {
        newGroupId: selectedGroup?.id,
        oldGroupId: lastGroupId.current
      });
      
      // 重置状态
      reset();
      
      // 重置加载标记，确保可以立即加载
      (window as any)._lastLoadTrigger = 0;
      (window as any)._lastScrollAdjust = 0;
      
      // 不再延迟滚动检测，立即启用
      console.log('[InfiniteScroll] 立即启用滚动检测');
    }
  }, [selectedGroup?.id, reset]);
  
  // 创建一个初始检查函数
  const checkInitialScroll = useCallback(() => {
    if (containerRef.current && selectedGroup?.id) {
      const scrollTop = containerRef.current.scrollTop;
      console.log('[InfiniteScroll] 初始滚动位置检查', { scrollTop });
      
      // 如果一开始就在顶部附近，主动加载一次历史数据
      if (scrollTop < 200 && hasMore && !isLoadingRef.current) {
        console.log('[InfiniteScroll] 初始化时接近顶部，主动加载历史数据');
        
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
    
    // 延迟300ms后检查是否需要预加载，确保UI已更新
    const timer = setTimeout(checkInitialScroll, 300);
    
    return () => clearTimeout(timer);
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

  // 统一的滚动事件处理器 - 简化版，更直接地触发加载
  const handleScroll = useCallback(() => {
    if (!containerRef.current || !selectedGroup || isLoadingRef.current || !hasMore) {
      console.log('[InfiniteScroll] 未满足基本滚动条件，跳过处理', {
        hasContainer: !!containerRef.current,
        hasSelectedGroup: !!selectedGroup,
        isLoading: isLoadingRef.current,
        hasMore
      });
      return;
    }

    // 简化滚动条件判断
    const container = containerRef.current;
    const scrollTop = container.scrollTop;
    const scrollHeight = container.scrollHeight;
    const clientHeight = container.clientHeight;
    
    // 记录滚动状态
    console.log(`[InfiniteScroll] 滚动状态: top=${scrollTop}, height=${scrollHeight}, client=${clientHeight}`);
    
    // 更宽松的时间限制
    const timeSinceLastLoad = Date.now() - ((window as any)._lastLoadTrigger || 0);
    if (timeSinceLastLoad < 1000) {
      console.log('[InfiniteScroll] 距离上次加载时间太短，跳过', { timeSinceLastLoad });
      return;
    }
    
    // 简化触发区域，降低阈值提高灵敏度
    const topThreshold = Math.min(threshold * 2, 100); // 更宽松的顶部阈值，至少100px
    
    // 当滚动接近顶部时，直接触发加载
    if (scrollTop <= topThreshold) {
      console.log(`[InfiniteScroll] 已滚动到顶部区域(${scrollTop} <= ${topThreshold})，触发加载历史消息...`);
      
      // 清除防抖定时器
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
        debounceTimer.current = null;
      }
      
      // 记录触发时间
      (window as any)._lastLoadTrigger = Date.now();
      
      // 设置正在加载标记
      isLoadingRef.current = true;
      setIsLoadingMore(true);
      
      // 直接执行加载，确保被调用
      loadMore().finally(() => {
        isLoadingRef.current = false;
        setIsLoadingMore(false);
      });
      
      return;
    }
    
    // 优化预加载逻辑：更大的预加载区域
    const preloadThreshold = Math.min(scrollHeight * 0.25, 800); // 增加预加载范围
    
    if (scrollTop <= preloadThreshold && currentPage < maxPages) {
      console.log('[InfiniteScroll] 进入预加载区域', { scrollTop, preloadThreshold });
      
      // 防抖处理：减少延迟以更快响应
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
      
      debounceTimer.current = setTimeout(() => {
        // 简化条件检查
        if (containerRef.current && !isLoadingRef.current) {
          console.log('[InfiniteScroll] 预加载定时器触发');
          (window as any)._lastLoadTrigger = Date.now();
          
          // 设置加载状态
          isLoadingRef.current = true;
          setIsLoadingMore(true);
          
          loadMore().finally(() => {
            isLoadingRef.current = false;
            setIsLoadingMore(false);
          });
        }
      }, debounceDelay / 2); // 减少防抖延迟提高响应速度
    }
  }, [containerRef, selectedGroup, hasMore, threshold, debounceDelay, loadMore, currentPage, maxPages, setIsLoadingMore]);

  // 绑定滚动事件 - 只使用统一的handleScroll
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 使用节流而不是直接绑定，进一步减少触发频率
    let ticking = false;
    const scrollHandler = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          // 添加更多调试日志
          const scrollTop = container.scrollTop;
          const scrollHeight = container.scrollHeight;
          console.log(`[InfiniteScroll] 滚动处理: scrollTop=${scrollTop}, scrollHeight=${scrollHeight}`);
          
          // 检查是否接近顶部
          if (scrollTop <= 100) {
            console.log(`[InfiniteScroll] 接近顶部! scrollTop=${scrollTop}`);
          }
          
          handleScroll();
          ticking = false;
        });
        ticking = true;
      }
    };

    console.log(`[InfiniteScroll] 绑定滚动事件到容器:`, container);
    container.addEventListener('scroll', scrollHandler, { passive: true });

    return () => {
      container.removeEventListener('scroll', scrollHandler);
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [handleScroll, containerRef]);

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