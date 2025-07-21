import { useState, useCallback, useEffect } from 'react';

// 导航历史记录条目类型
export interface NavigationHistoryEntry {
  type: 'group' | 'message'; // 导航类型：群组或消息
  groupId: number;          // 群组ID
  messageId?: number;       // 消息ID（可选，仅当type为message时有效）
  timestamp: number;        // 导航时间戳
  title?: string;           // 群组标题（可选）
}

// 导航历史hook配置
export interface NavigationHistoryOptions {
  maxHistory?: number;      // 最大历史记录数量
  storageKey?: string;      // localStorage存储键名
  persistHistory?: boolean; // 是否持久化存储历史记录
}

/**
 * 导航历史记录Hook
 * 用于管理群组、消息的导航历史，支持前进、后退操作
 */
export const useNavigationHistory = (options: NavigationHistoryOptions = {}) => {
  const {
    maxHistory = 50,
    storageKey = 'group_navigation_history',
    persistHistory = true
  } = options;

  // 历史记录状态
  const [history, setHistory] = useState<NavigationHistoryEntry[]>([]);
  // 当前位置（历史记录索引）
  const [currentIndex, setCurrentIndex] = useState<number>(-1);

  // 从localStorage加载历史记录
  useEffect(() => {
    if (persistHistory) {
      try {
        const savedHistory = localStorage.getItem(storageKey);
        if (savedHistory) {
          const parsed = JSON.parse(savedHistory);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setHistory(parsed);
            setCurrentIndex(parsed.length - 1);
          }
        }
      } catch (error) {
        console.error('加载导航历史记录失败:', error);
      }
    }
  }, [persistHistory, storageKey]);

  // 保存历史记录到localStorage
  const saveHistoryToStorage = useCallback((newHistory: NavigationHistoryEntry[]) => {
    if (persistHistory) {
      try {
        localStorage.setItem(storageKey, JSON.stringify(newHistory));
      } catch (error) {
        console.error('保存导航历史记录失败:', error);
      }
    }
  }, [persistHistory, storageKey]);

  // 添加导航历史记录
  const addHistory = useCallback((entry: Omit<NavigationHistoryEntry, 'timestamp'>) => {
    setHistory(prev => {
      // 如果当前不在历史记录末尾，截断历史记录
      const basedHistory = currentIndex < prev.length - 1 
        ? prev.slice(0, currentIndex + 1) 
        : prev;
        
      // 创建新条目
      const newEntry: NavigationHistoryEntry = {
        ...entry,
        timestamp: Date.now()
      };
      
      // 检查是否与最后一条记录相同
      const lastEntry = basedHistory[basedHistory.length - 1];
      if (lastEntry && 
          lastEntry.groupId === newEntry.groupId && 
          lastEntry.messageId === newEntry.messageId &&
          lastEntry.type === newEntry.type) {
        return basedHistory; // 不添加重复记录
      }
      
      // 添加新记录，保持最大长度
      const newHistory = [...basedHistory, newEntry].slice(-maxHistory);
      
      // 更新当前位置
      setCurrentIndex(newHistory.length - 1);
      
      // 保存到localStorage
      saveHistoryToStorage(newHistory);
      
      return newHistory;
    });
  }, [currentIndex, maxHistory, saveHistoryToStorage]);

  // 导航到历史记录中的特定条目
  const navigateToIndex = useCallback((index: number) => {
    if (index >= 0 && index < history.length && index !== currentIndex) {
      setCurrentIndex(index);
      return history[index];
    }
    return null;
  }, [history, currentIndex]);

  // 导航到上一条记录
  const goBack = useCallback(() => {
    return navigateToIndex(currentIndex - 1);
  }, [navigateToIndex, currentIndex]);

  // 导航到下一条记录
  const goForward = useCallback(() => {
    return navigateToIndex(currentIndex + 1);
  }, [navigateToIndex, currentIndex]);

  // 清除历史记录
  const clearHistory = useCallback(() => {
    setHistory([]);
    setCurrentIndex(-1);
    if (persistHistory) {
      localStorage.removeItem(storageKey);
    }
  }, [persistHistory, storageKey]);

  // 检查是否可以后退/前进
  const canGoBack = currentIndex > 0;
  const canGoForward = currentIndex < history.length - 1;

  // 获取当前导航记录
  const currentEntry = history[currentIndex] || null;

  return {
    history,
    currentEntry,
    currentIndex,
    addHistory,
    goBack,
    goForward,
    navigateToIndex,
    clearHistory,
    canGoBack,
    canGoForward
  };
}; 