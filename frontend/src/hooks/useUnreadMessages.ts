import { useState, useEffect, useCallback } from 'react';
import { telegramApi } from '../services/apiService';

interface UnreadMessage {
  group_id: number;
  group_title: string;
  unread_count: number;
  cutoff_time: string;
  latest_message?: {
    id: number;
    message_id: number;
    text: string;
    sender_name: string;
    date: string;
    media_type?: string;
  };
  latest_unread_message?: {
    id: number;
    message_id: number;
    text: string;
    sender_name: string;
    date: string;
    media_type?: string;
  };
}

interface UnreadSummary {
  total_unread: number;
  groups_count: number;
  groups_with_unread: number;
  groups: Array<{
    group_id: number;
    group_title: string;
    group_username?: string;
    unread_count: number;
    cutoff_time?: string;
    latest_message_time?: string;
    latest_message_text?: string;
  }>;
}

// 本地存储键名
const LAST_READ_TIMES_KEY = 'telegram_group_last_read_times';

export const useUnreadMessages = () => {
  const [unreadSummary, setUnreadSummary] = useState<UnreadSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 从localStorage获取最后读取时间
  const getLastReadTimes = useCallback((): Record<string, string> => {
    try {
      const stored = localStorage.getItem(LAST_READ_TIMES_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch (error) {
      console.error('解析最后读取时间失败:', error);
      return {};
    }
  }, []);

  // 保存最后读取时间到localStorage
  const saveLastReadTimes = useCallback((times: Record<string, string>) => {
    try {
      localStorage.setItem(LAST_READ_TIMES_KEY, JSON.stringify(times));
    } catch (error) {
      console.error('保存最后读取时间失败:', error);
    }
  }, []);

  // 标记群组为已读
  const markGroupAsRead = useCallback((groupId: number) => {
    const currentTime = new Date().toISOString();
    const lastReadTimes = getLastReadTimes();
    lastReadTimes[groupId.toString()] = currentTime;
    saveLastReadTimes(lastReadTimes);
    
    // 更新未读摘要中对应群组的计数
    if (unreadSummary) {
      const updatedGroups = unreadSummary.groups.map(group => 
        group.group_id === groupId 
          ? { ...group, unread_count: 0, cutoff_time: currentTime }
          : group
      );
      
      const newTotalUnread = updatedGroups.reduce((sum, group) => sum + group.unread_count, 0);
      const newGroupsWithUnread = updatedGroups.filter(group => group.unread_count > 0).length;
      
      setUnreadSummary({
        ...unreadSummary,
        total_unread: newTotalUnread,
        groups_with_unread: newGroupsWithUnread,
        groups: updatedGroups
      });
    }
  }, [unreadSummary, getLastReadTimes, saveLastReadTimes]);

  // 获取单个群组的未读消息数量
  const getGroupUnreadCount = useCallback(async (groupId: number): Promise<UnreadMessage | null> => {
    try {
      const lastReadTimes = getLastReadTimes();
      const lastReadTime = lastReadTimes[groupId.toString()];
      
      const result = await telegramApi.getGroupUnreadCount(groupId, lastReadTime);
      return result;
    } catch (error) {
      console.error(`获取群组 ${groupId} 未读消息数量失败:`, error);
      return null;
    }
  }, [getLastReadTimes]);

  // 获取所有群组的未读消息摘要
  const fetchUnreadSummary = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const lastReadTimes = getLastReadTimes();
      const result = await telegramApi.getAllGroupsUnreadSummary(lastReadTimes);
      setUnreadSummary(result);
    } catch (error: any) {
      const errorMessage = error?.message || '获取未读消息摘要失败';
      setError(errorMessage);
      console.error('获取未读消息摘要失败:', error);
    } finally {
      setLoading(false);
    }
  }, [getLastReadTimes]);

  // 获取特定群组的未读数量（从摘要中）
  const getUnreadCountForGroup = useCallback((groupId: number): number => {
    if (!unreadSummary) return 0;
    const group = unreadSummary.groups.find(g => g.group_id === groupId);
    return group?.unread_count || 0;
  }, [unreadSummary]);

  // 重置所有未读计数
  const markAllAsRead = useCallback(() => {
    if (!unreadSummary) return;
    
    const currentTime = new Date().toISOString();
    const lastReadTimes: Record<string, string> = {};
    
    unreadSummary.groups.forEach(group => {
      lastReadTimes[group.group_id.toString()] = currentTime;
    });
    
    saveLastReadTimes(lastReadTimes);
    
    // 更新状态
    const updatedGroups = unreadSummary.groups.map(group => ({
      ...group,
      unread_count: 0,
      cutoff_time: currentTime
    }));
    
    setUnreadSummary({
      ...unreadSummary,
      total_unread: 0,
      groups_with_unread: 0,
      groups: updatedGroups
    });
  }, [unreadSummary, saveLastReadTimes]);

  // 组件挂载时获取未读消息摘要
  useEffect(() => {
    fetchUnreadSummary();
  }, [fetchUnreadSummary]);

  // 定期刷新未读消息摘要（每5分钟）
  useEffect(() => {
    const interval = setInterval(fetchUnreadSummary, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchUnreadSummary]);

  return {
    unreadSummary,
    loading,
    error,
    markGroupAsRead,
    markAllAsRead,
    getGroupUnreadCount,
    getUnreadCountForGroup,
    fetchUnreadSummary,
    totalUnreadCount: unreadSummary?.total_unread || 0,
    groupsWithUnreadCount: unreadSummary?.groups_with_unread || 0
  };
};

export default useUnreadMessages;