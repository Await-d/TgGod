import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Space, Button, Empty, Spin, Typography, message as antMessage } from 'antd';
import { 
  ReloadOutlined, 
  SyncOutlined, 
  SettingOutlined,
  ArrowDownOutlined 
} from '@ant-design/icons';
import { TelegramGroup, TelegramMessage } from '../../types';
import MessageBubble from './MessageBubble';
import MessageHeader from './MessageHeader';
import { messageApi, telegramApi } from '../../services/apiService';
import { useTelegramStore } from '../../store';
import './MessageArea.css';

const { Text } = Typography;

interface MessageAreaProps {
  selectedGroup: TelegramGroup | null;
  onReply: (message: TelegramMessage) => void;
  onCreateRule: (message: TelegramMessage) => void;
  searchFilter?: any;
  isMobile?: boolean;
}

const MessageArea: React.FC<MessageAreaProps> = ({
  selectedGroup,
  onReply,
  onCreateRule,
  searchFilter = {},
  isMobile = false
}) => {
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  
  const { messages, setMessages, addMessage, removeMessage } = useTelegramStore();
  const PAGE_SIZE = 50;

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    setShowScrollToBottom(false);
  }, []);

  // 检查是否需要显示"滚动到底部"按钮
  const handleScroll = useCallback(() => {
    if (!messagesContainerRef.current) return;
    
    const container = messagesContainerRef.current;
    const isNearBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 200;
    setShowScrollToBottom(!isNearBottom);
  }, []);

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
      
      if (append && pageNum > 1) {
        // 如果是追加模式，需要将新消息添加到现有消息列表
        const currentMessages = messages;
        setMessages([...currentMessages, ...response]);
      } else {
        setMessages(response);
        // 新消息加载后滚动到底部
        setTimeout(scrollToBottom, 100);
      }
      
      // 检查是否还有更多消息
      if (response.length < PAGE_SIZE) {
        setHasMore(false);
      } else {
        setHasMore(true);
      }
      
      setPage(pageNum);
    } catch (error: any) {
      antMessage.error('获取消息失败: ' + error.message);
      console.error('获取消息失败:', error);
    } finally {
      loadingState(false);
    }
  }, [setMessages, PAGE_SIZE, scrollToBottom]);

  // 加载更多消息
  const loadMoreMessages = useCallback(async () => {
    if (!selectedGroup || loadingMore || !hasMore) return;
    
    await fetchMessages(selectedGroup.id, page + 1, searchFilter, true);
  }, [selectedGroup, loadingMore, hasMore, page, searchFilter, fetchMessages]);

  // 刷新消息
  const refreshMessages = useCallback(async () => {
    if (!selectedGroup) return;
    
    setPage(1);
    setHasMore(true);
    await fetchMessages(selectedGroup.id, 1, searchFilter);
  }, [selectedGroup, searchFilter, fetchMessages]);

  // 同步消息
  const syncMessages = useCallback(async () => {
    if (!selectedGroup) return;
    
    try {
      await telegramApi.syncGroupMessages(selectedGroup.id, 100);
      antMessage.success('消息同步成功！');
      await refreshMessages();
    } catch (error: any) {
      antMessage.error('同步消息失败: ' + error.message);
      console.error('同步消息失败:', error);
    }
  }, [selectedGroup, refreshMessages]);

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

  // 当选择群组变化时重新加载消息
  useEffect(() => {
    if (selectedGroup) {
      setPage(1);
      setHasMore(true);
      fetchMessages(selectedGroup.id, 1, searchFilter);
    } else {
      setMessages([]);
    }
  }, [selectedGroup, fetchMessages, searchFilter, setMessages]);

  // 添加滚动监听
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);

  // 处理滚动加载更多
  const handleScrollToTop = useCallback(() => {
    if (!messagesContainerRef.current) return;
    
    const container = messagesContainerRef.current;
    if (container.scrollTop <= 100 && hasMore && !loadingMore) {
      loadMoreMessages();
    }
  }, [hasMore, loadingMore, loadMoreMessages]);

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScrollToTop);
      return () => container.removeEventListener('scroll', handleScrollToTop);
    }
  }, [handleScrollToTop]);

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
        onRefresh={refreshMessages}
        onSync={syncMessages}
        loading={loading}
        isMobile={isMobile}
      />

      {/* 消息列表 */}
      <div 
        className="message-list" 
        ref={messagesContainerRef}
      >
        {/* 加载更多指示器 */}
        {loadingMore && (
          <div className="load-more-indicator">
            <Spin size="small" />
            <Text type="secondary">加载更多消息...</Text>
          </div>
        )}
        
        {/* 消息列表 */}
        {loading && messages.length === 0 ? (
          <div className="message-loading">
            <Spin size="large" />
            <Text type="secondary">加载消息中...</Text>
          </div>
        ) : messages.length === 0 ? (
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
            {!hasMore && (
              <div className="no-more-messages">
                <Text type="secondary">没有更多消息了</Text>
              </div>
            )}
            
            {messages.map((message, index) => {
              const prevMessage = index > 0 ? messages[index - 1] : null;
              const showAvatar = !prevMessage || 
                prevMessage.sender_id !== message.sender_id ||
                (new Date(message.date).getTime() - new Date(prevMessage.date).getTime()) > 300000; // 5分钟
              
              return (
                <MessageBubble
                  key={message.id}
                  message={message}
                  isOwn={false} // TODO: 判断是否为自己发送的消息
                  showAvatar={showAvatar}
                  onReply={onReply}
                  onCreateRule={onCreateRule}
                  onDelete={handleDeleteMessage}
                  isMobile={isMobile}
                />
              );
            })}
          </>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 滚动到底部按钮 */}
      {showScrollToBottom && (
        <div className="scroll-to-bottom">
          <Button
            type="primary"
            shape="circle"
            icon={<ArrowDownOutlined />}
            onClick={scrollToBottom}
            size="large"
          />
        </div>
      )}
    </div>
  );
};

export default MessageArea;