import { useEffect, useCallback, useRef } from 'react';
import { TelegramMessage, TelegramGroup } from '../types';
import { useTelegramStore } from '../store';
import { subscribeToMessages, subscribeToGroupStatus, webSocketService } from '../services/websocket';
import { messageApi } from '../services/apiService';

export interface RealTimeMessageOptions {
  autoConnect?: boolean;
  maxRetries?: number;
  retryDelay?: number;
}

/**
 * 实时消息管理 Hook
 * 负责WebSocket连接、消息接收、自动同步
 */
export const useRealTimeMessages = (
  selectedGroup: TelegramGroup | null,
  options: RealTimeMessageOptions = {}
) => {
  const {
    autoConnect = true,
    maxRetries = 5,
    retryDelay = 3000
  } = options;

  const { setMessages, addMessage } = useTelegramStore();
  const connectionAttempts = useRef(0);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);

  // 连接WebSocket
  const connectWebSocket = useCallback(() => {
    if (!autoConnect) return;
    
    try {
      webSocketService.connect();
      connectionAttempts.current = 0;
    } catch (error) {
      console.error('WebSocket连接失败:', error);
      
      // 重试逻辑
      if (connectionAttempts.current < maxRetries) {
        connectionAttempts.current++;
        reconnectTimer.current = setTimeout(() => {
          connectWebSocket();
        }, retryDelay * connectionAttempts.current);
      }
    }
  }, [autoConnect, maxRetries, retryDelay]);

  // 处理新消息接收 - 使用ref避免依赖循环
  const selectedGroupRef = useRef(selectedGroup);
  useEffect(() => {
    selectedGroupRef.current = selectedGroup;
  }, [selectedGroup]);

  const handleNewMessage = useCallback((messageData: any) => {
    console.log('收到新消息:', messageData);
    
    const currentGroup = selectedGroupRef.current;
    // 检查消息是否属于当前选中的群组
    if (!currentGroup || !messageData.chat_id) {
      return;
    }

    // 如果消息来自当前选中的群组，添加到消息列表
    if (messageData.chat_id.toString() === currentGroup.id.toString()) {
      const newMessage: TelegramMessage = {
        id: messageData.id || Date.now(),
        message_id: messageData.message_id || Date.now(),
        group_id: messageData.chat_id,
        sender_name: messageData.sender_name || messageData.from?.first_name || '未知用户',
        sender_username: messageData.sender_username || messageData.from?.username,
        text: messageData.text || messageData.caption || '',
        date: messageData.date || new Date().toISOString(),
        created_at: messageData.date || new Date().toISOString(),
        media_type: messageData.media_type,
        media_path: messageData.media_path,
        media_filename: messageData.media_filename,
        media_size: messageData.media_size,
        reply_to_message_id: messageData.reply_to_message_id,
        is_forwarded: messageData.forward_from !== undefined,
        is_pinned: messageData.is_pinned || false,
        view_count: messageData.view_count || 0,
        reactions: messageData.reactions || {},
        mentions: messageData.mentions || [],
        hashtags: messageData.hashtags || [],
        edit_date: messageData.edit_date
      };

      addMessage(newMessage);
      console.log('新消息已添加到列表');
    }
  }, [addMessage]);

  // 处理群组状态更新 - 使用ref避免依赖循环
  const handleGroupStatusUpdate = useCallback((statusData: any) => {
    console.log('群组状态更新:', statusData);
    
    const currentGroup = selectedGroupRef.current;
    // 如果是当前群组的状态更新，可以处理相关逻辑
    if (currentGroup && statusData.group_id === currentGroup.id) {
      // 可以更新群组相关状态，比如在线成员数、最后活动时间等
      console.log(`群组 ${currentGroup.title} 状态更新:`, statusData);
    }
  }, []);

  // 订阅群组实时消息
  const subscribeToGroupMessages = useCallback((groupId: string | number) => {
    console.log('订阅群组消息:', groupId);
    
    // 发送订阅消息到服务器
    if (webSocketService.isConnected()) {
      webSocketService.send({
        type: 'subscribe_group',
        group_id: groupId.toString()
      });
    }
  }, []);

  // 取消订阅群组消息
  const unsubscribeFromGroupMessages = useCallback((groupId?: string | number) => {
    const targetGroupId = groupId || selectedGroup?.id;
    if (targetGroupId) {
      console.log('取消订阅群组消息:', targetGroupId);
      
      if (webSocketService.isConnected()) {
        webSocketService.send({
          type: 'unsubscribe_group',
          group_id: targetGroupId.toString()
        });
      }
    }
  }, [selectedGroup]);

  // 自动获取最新消息
  const fetchLatestMessages = useCallback(async (groupId: string | number, limit: number = 50, shouldScrollToBottom: boolean = true) => {
    try {
      console.log('获取最新消息:', groupId);
      const response = await messageApi.getGroupMessages(Number(groupId), {
        skip: 0,
        limit: limit
      });

      if (response && Array.isArray(response)) {
        setMessages(response);
        console.log(`成功加载 ${response.length} 条消息`);
        
        // 根据参数决定是否需要滚动到底部
        if (shouldScrollToBottom) {
          (window as any)._shouldScrollToBottom = true;
        }
      }
    } catch (error) {
      console.error('获取最新消息失败:', error);
    }
  }, [setMessages]);

  // 当选中群组变化时的处理 - 使用ref避免重复订阅
  const lastSubscribedGroupId = useRef<string | number | null>(null);
  
  useEffect(() => {
    const currentGroupId = selectedGroup?.id;
    
    // 如果群组ID没有变化，跳过处理
    if (currentGroupId === lastSubscribedGroupId.current) {
      return;
    }
    
    // 取消之前群组的订阅
    if (lastSubscribedGroupId.current) {
      unsubscribeFromGroupMessages(lastSubscribedGroupId.current);
    }
    
    // 订阅新群组的消息并加载初始消息
    if (currentGroupId) {
      subscribeToGroupMessages(currentGroupId);
      console.log('useRealTimeMessages: 已订阅群组消息，开始加载初始消息');
      
      // 延迟加载初始消息，确保其他状态已经重置
      setTimeout(() => {
        fetchLatestMessages(currentGroupId, 50, true);
      }, 100);
    }
    
    // 更新订阅记录
    lastSubscribedGroupId.current = currentGroupId || null;

    // 清理函数：组件卸载时取消订阅
    return () => {
      if (lastSubscribedGroupId.current) {
        unsubscribeFromGroupMessages(lastSubscribedGroupId.current);
        lastSubscribedGroupId.current = null;
      }
    };
  }, [selectedGroup?.id, fetchLatestMessages]); // 添加fetchLatestMessages依赖

  // WebSocket 消息订阅 - 只在组件挂载时订阅一次
  useEffect(() => {
    const unsubscribeMessages = subscribeToMessages(handleNewMessage);
    const unsubscribeGroupStatus = subscribeToGroupStatus(handleGroupStatusUpdate);

    return () => {
      unsubscribeMessages();
      unsubscribeGroupStatus();
    };
  }, []); // 移除依赖，只在挂载时执行一次

  // 组件挂载时连接WebSocket
  useEffect(() => {
    connectWebSocket();

    // 清理函数
    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
    };
  }, [connectWebSocket]);

  // 获取WebSocket连接状态
  const getConnectionStatus = useCallback(() => {
    if (webSocketService.isConnected()) {
      return 'connected';
    } else if (connectionAttempts.current > 0 && connectionAttempts.current < maxRetries) {
      return 'connecting';
    } else {
      return 'disconnected';
    }
  }, [maxRetries]);

  // 手动重新连接
  const reconnect = useCallback(() => {
    connectionAttempts.current = 0;
    connectWebSocket();
  }, [connectWebSocket]);

  return {
    // 状态
    connectionStatus: getConnectionStatus(),
    isConnected: webSocketService.isConnected(),
    
    // 操作方法
    subscribeToGroupMessages,
    unsubscribeFromGroupMessages,
    fetchLatestMessages,
    reconnect,
    
    // 统计信息
    connectionAttempts: connectionAttempts.current,
    maxRetries
  };
};