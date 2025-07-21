import { useState, useEffect, useCallback, useRef, useMemo } from 'react';

interface VirtualScrollOptions {
  itemHeight: number; // 每个消息的估计高度
  containerHeight: number; // 容器高度
  overscan?: number; // 额外渲染的项目数量
  totalItems: number; // 总项目数量
}

interface VirtualScrollResult {
  startIndex: number;
  endIndex: number;
  visibleItems: number[];
  containerProps: {
    style: React.CSSProperties;
    onScroll: (e: React.UIEvent<HTMLDivElement>) => void;
    ref: React.RefObject<HTMLDivElement>;
  };
  getItemStyle: (index: number) => React.CSSProperties;
  scrollToIndex: (index: number) => void;
  isItemVisible: (index: number) => boolean;
}

export const useVirtualScroll = ({
  itemHeight,
  containerHeight,
  overscan = 5,
  totalItems
}: VirtualScrollOptions): VirtualScrollResult => {
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const [actualItemHeights, setActualItemHeights] = useState<Map<number, number>>(new Map());

  // 计算可见范围
  const { startIndex, endIndex, visibleItems } = useMemo(() => {
    if (totalItems === 0 || containerHeight === 0) {
      return { startIndex: 0, endIndex: 0, visibleItems: [] };
    }

    // 使用实际高度计算，如果没有实际高度则使用估计高度
    let accumulatedHeight = 0;
    let start = 0;
    let end = 0;

    // 找到起始索引
    for (let i = 0; i < totalItems; i++) {
      const height = actualItemHeights.get(i) || itemHeight;
      if (accumulatedHeight + height > scrollTop) {
        start = Math.max(0, i - overscan);
        break;
      }
      accumulatedHeight += height;
    }

    // 找到结束索引
    accumulatedHeight = 0;
    for (let i = 0; i < totalItems; i++) {
      const height = actualItemHeights.get(i) || itemHeight;
      if (i >= start) {
        accumulatedHeight += height;
        if (accumulatedHeight > containerHeight + overscan * itemHeight) {
          end = Math.min(totalItems - 1, i + overscan);
          break;
        }
      } else {
        accumulatedHeight = 0; // 重置，从start开始计算
      }
    }

    // 如果没有找到结束索引，说明所有剩余项目都应该渲染
    if (end === 0) {
      end = Math.min(totalItems - 1, start + Math.ceil(containerHeight / itemHeight) + overscan * 2);
    }

    const visible = [];
    for (let i = start; i <= end; i++) {
      visible.push(i);
    }

    return { startIndex: start, endIndex: end, visibleItems: visible };
  }, [scrollTop, totalItems, containerHeight, itemHeight, overscan, actualItemHeights]);

  // 处理滚动事件
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement;
    setScrollTop(target.scrollTop);
  }, []);

  // 滚动到指定索引
  const scrollToIndex = useCallback((index: number) => {
    if (!containerRef.current) return;

    let offset = 0;
    for (let i = 0; i < index; i++) {
      offset += actualItemHeights.get(i) || itemHeight;
    }

    containerRef.current.scrollTop = offset;
  }, [actualItemHeights, itemHeight]);

  // 检查项目是否可见
  const isItemVisible = useCallback((index: number) => {
    return index >= startIndex && index <= endIndex;
  }, [startIndex, endIndex]);

  // 获取项目样式
  const getItemStyle = useCallback((index: number): React.CSSProperties => {
    let offset = 0;
    for (let i = 0; i < index; i++) {
      offset += actualItemHeights.get(i) || itemHeight;
    }

    return {
      position: 'absolute',
      top: offset,
      left: 0,
      right: 0,
      minHeight: itemHeight, // 使用minHeight而不是固定height
      width: '100%',
    };
  }, [actualItemHeights, itemHeight]);

  // 更新实际项目高度的方法
  const updateItemHeight = useCallback((index: number, height: number) => {
    setActualItemHeights(prev => {
      const newMap = new Map(prev);
      newMap.set(index, height);
      return newMap;
    });
  }, []);

  // 计算总高度
  const totalHeight = useMemo(() => {
    let height = 0;
    for (let i = 0; i < totalItems; i++) {
      height += actualItemHeights.get(i) || itemHeight;
    }
    return height;
  }, [totalItems, actualItemHeights, itemHeight]);

  // 容器属性
  const containerProps = {
    style: {
      height: containerHeight,
      overflow: 'auto',
      position: 'relative' as const,
    },
    onScroll: handleScroll,
    ref: containerRef,
  };

  // 监听容器大小变化
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const resizeObserver = new ResizeObserver(() => {
      // 容器大小变化时重新计算
      setScrollTop(container.scrollTop);
    });

    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  return {
    startIndex,
    endIndex,
    visibleItems,
    containerProps,
    getItemStyle,
    scrollToIndex,
    isItemVisible,
    // 扩展属性
    updateItemHeight,
    totalHeight,
    scrollTop,
  } as VirtualScrollResult & {
    updateItemHeight: (index: number, height: number) => void;
    totalHeight: number;
    scrollTop: number;
  };
};