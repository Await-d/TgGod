import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Layout, Typography, Drawer, Button, message as antMessage } from 'antd';
import { MenuOutlined, CloseOutlined } from '@ant-design/icons';
import { TelegramGroup, TelegramMessage } from '../types';
import { ChatState, MessageFilter } from '../types/chat';
import { useTelegramStore, useAuthStore } from '../store';
import { webSocketService } from '../services/websocket';
import { messageApi } from '../services/apiService';
import { useMobileGestures, useIsMobile, useKeyboardHeight } from '../hooks/useMobileGestures';
import { useChatPageScrollControl } from '../hooks/usePageScrollControl';
import { useChatGroupNavigation } from '../hooks/useGroupNavigation';
import { useRealTimeMessages } from '../hooks/useRealTimeMessages';
import { useInfiniteScroll } from '../hooks/useInfiniteScroll';
import GroupList from '../components/Chat/GroupList';
import MessageArea from '../components/Chat/MessageArea';
import MessageInput from '../components/Chat/MessageInput';
import QuickActions from '../components/Chat/QuickActions';
import MessageFilterDrawer from '../components/Chat/MessageFilterDrawer';
import QuickRuleModal from '../components/Chat/QuickRuleModal';
import MessageHighlight from '../components/Chat/MessageHighlight';
import MediaPreview from '../components/Chat/MediaPreview';
import VoiceMessage from '../components/Chat/VoiceMessage';
import MessageQuoteForward, { QuotedMessage } from '../components/Chat/MessageQuoteForward';
import './ChatInterface.css';

const { Title } = Typography;

const ChatInterface: React.FC = () => {
  // 页面滚动控制 - 启用聊天界面专用滚动控制
  useChatPageScrollControl();
  
  // 移动端检测
  const isMobile = useIsMobile();
  const { keyboardHeight, isKeyboardVisible } = useKeyboardHeight();
  const chatContainerRef = useRef<HTMLDivElement>(null);
  
  // 群组导航和状态管理 - 新增
  const {
    selectedGroup,
    groups,
    messages,
    selectGroup,
    clearGroupSelection,
    navigateToGroup,
    setMessages
  } = useChatGroupNavigation();
  
  // 实时消息管理 - 新增
  const {
    connectionStatus,
    isConnected,
    fetchLatestMessages,
    reconnect
  } = useRealTimeMessages(selectedGroup);
  
  // 无限滚动管理 - 新增
  const {
    isLoadingMore,
    hasMore,
    currentPage,
    totalLoaded,
    loadMore,
    reset: resetInfiniteScroll,
    scrollToTop,
    scrollToBottom,
    autoScrollToBottom
  } = useInfiniteScroll(
    chatContainerRef,
    selectedGroup,
    messages,
    (updatedMessages) => {
      // 更新消息到store中
      console.log('无限滚动更新消息:', updatedMessages.length);
      setMessages(updatedMessages);
    },
    {
      threshold: 100,
      debounceDelay: 300,
      pageSize: 50,
      preloadThreshold: 3,
      maxPages: 50
    }
  );
  
  // 状态管理
  const [chatState, setChatState] = useState<ChatState>({
    selectedGroup: null,
    isGroupListCollapsed: false,
    isMobile: false,
    searchQuery: '',
    messageFilter: {}
  });
  
  const [replyTo, setReplyTo] = useState<TelegramMessage | null>(null);
  const [quotedMessage, setQuotedMessage] = useState<TelegramMessage | null>(null);
  const [contacts, setContacts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(false);
  const [showFilterDrawer, setShowFilterDrawer] = useState(false);
  const [showRuleModal, setShowRuleModal] = useState(false);
  const [ruleBaseMessage, setRuleBaseMessage] = useState<TelegramMessage | null>(null);
  const [globalError, setGlobalError] = useState<string | null>(null);
  
  // 同步选中群组到内部状态
  useEffect(() => {
    setChatState(prev => ({
      ...prev,
      selectedGroup: selectedGroup,
      isMobile: isMobile
    }));
  }, [selectedGroup, isMobile]);

  // 监听消息加载完成，自动滚动到底部
  useEffect(() => {
    if ((window as any)._shouldScrollToBottom && messages.length > 0) {
      console.log('自动滚动到底部');
      autoScrollToBottom();
      (window as any)._shouldScrollToBottom = false;
    }
  }, [messages, autoScrollToBottom]);

  // Store hooks - 简化，只保留认证状态
  const { isAuthenticated } = useAuthStore();

  // 移动端手势支持
  const { isSwiping } = useMobileGestures({
    onSwipeRight: () => {
      if (isMobile && chatState.isGroupListCollapsed) {
        setChatState(prev => ({ ...prev, isGroupListCollapsed: false }));
      }
    },
    onSwipeLeft: () => {
      if (isMobile && !chatState.isGroupListCollapsed) {
        setChatState(prev => ({ ...prev, isGroupListCollapsed: true }));
      }
    },
    threshold: 100,
    element: chatContainerRef.current
  });

  // 更新移动端状态
  useEffect(() => {
    setChatState(prev => ({ ...prev, isMobile }));
    
    // 移动端默认收起群组列表
    if (isMobile && !chatState.selectedGroup) {
      setChatState(prev => ({ ...prev, isGroupListCollapsed: true }));
    }
  }, [isMobile, chatState.selectedGroup]);

  // 初始化 - 移除旧的WebSocket逻辑，现在由useRealTimeMessages处理
  useEffect(() => {
    console.log('聊天界面已加载，认证状态:', isAuthenticated);
  }, [isAuthenticated]);

  // 处理群组选择 - 现在使用新的selectGroup方法
  const handleGroupSelect = useCallback((group: TelegramGroup) => {
    selectGroup(group);
    
    // 在移动端选择群组后关闭侧边栏
    if (isMobile) {
      setChatState(prev => ({ ...prev, isGroupListCollapsed: true }));
    }
  }, [isMobile, selectGroup]);

  // 处理消息回复
  const handleReply = useCallback((message: TelegramMessage) => {
    setReplyTo(message);
  }, []);

  // 处理消息引用
  const handleQuote = useCallback((message: TelegramMessage) => {
    setQuotedMessage(message);
  }, []);

  // 处理消息转发
  const handleForward = useCallback((message: TelegramMessage, targets: string[], comment?: string) => {
    // TODO: 实现消息转发逻辑
    console.log('转发消息:', message, '到:', targets, '评论:', comment);
    antMessage.success('消息转发成功');
  }, []);

  // 移除引用消息
  const handleRemoveQuote = useCallback(() => {
    setQuotedMessage(null);
  }, []);

  // 处理快捷创建规则
  const handleCreateQuickRule = useCallback((message: TelegramMessage) => {
    setRuleBaseMessage(message);
    setShowRuleModal(true);
  }, []);

  // 处理筛选应用
  const handleApplyFilter = useCallback((filter: MessageFilter) => {
    setChatState(prev => ({ ...prev, messageFilter: filter }));
  }, []);

  // 处理发送消息
  const handleSendMessage = useCallback(async (text: string) => {
    if (!chatState.selectedGroup) return;
    
    try {
      setLoading(true);
      
      // 构建消息发送请求
      const messageData = {
        text: text,
        reply_to_message_id: replyTo?.message_id,
      };
      
      // 调用API发送消息
      const response = await messageApi.sendMessage(chatState.selectedGroup.id, messageData);
      
      console.log('消息发送成功:', response);
      
      // 清除回复状态
      setReplyTo(null);
      
      // 可以在这里添加消息到本地状态，或者让MessageArea自动刷新
      // TODO: 可以考虑通过WebSocket实时接收新消息
      
    } catch (error: any) {
      console.error('发送消息失败:', error);
      throw error; // 让MessageInput组件处理错误显示
    } finally {
      setLoading(false);
    }
  }, [chatState.selectedGroup, replyTo]);

  // 切换群组列表显示/隐藏
  const toggleGroupList = useCallback(() => {
    setChatState(prev => ({ 
      ...prev, 
      isGroupListCollapsed: !prev.isGroupListCollapsed 
    }));
  }, []);

  // 渲染头部标题
  const renderHeader = () => (
    <div className="chat-header">
      {isMobile && (
        <Button
          type="text"
          icon={chatState.isGroupListCollapsed ? <MenuOutlined /> : <CloseOutlined />}
          onClick={toggleGroupList}
          className="mobile-menu-btn"
        />
      )}
      <div className="header-title-section">
        <Title level={3} style={{ margin: 0 }}>
          {chatState.selectedGroup ? chatState.selectedGroup.title : '请选择群组'}
        </Title>
        {/* 连接状态指示器 */}
        <div className={`connection-status ${connectionStatus}`}>
          <span className="status-dot"></span>
          <span className="status-text">
            {connectionStatus === 'connected' ? '已连接' : 
             connectionStatus === 'connecting' ? '连接中...' : '已断开'}
          </span>
        </div>
      </div>
      {globalError && (
        <div className="global-error">
          {globalError}
        </div>
      )}
    </div>
  );

  // 渲染群组列表
  const renderGroupList = () => (
    <GroupList
      selectedGroup={chatState.selectedGroup}
      onGroupSelect={handleGroupSelect}
      searchQuery={chatState.searchQuery}
      onSearchChange={(query) => setChatState(prev => ({ ...prev, searchQuery: query }))}
      isMobile={isMobile}
    />
  );

  // 渲染消息区域
  const renderMessageArea = () => (
    <MessageArea
      selectedGroup={selectedGroup}
      onReply={handleReply}
      onCreateRule={handleCreateQuickRule}
      searchFilter={chatState.messageFilter}
      isMobile={isMobile}
      searchQuery={chatState.searchQuery}
      onQuote={handleQuote}
      onForward={handleForward}
      contacts={contacts}
      // 无限滚动属性
      messages={messages}
      isLoadingMore={isLoadingMore}
      hasMore={hasMore}
      onLoadMore={loadMore}
      containerRef={chatContainerRef}
    />
  );

  // 渲染消息输入区域
  const renderMessageInput = () => (
    <div className="message-input-wrapper">
      {/* 快捷操作按钮 */}
      {chatState.selectedGroup && (
        <QuickActions
          selectedGroup={chatState.selectedGroup}
          onFilter={() => setShowFilterDrawer(true)}
          onSync={() => {
            // TODO: 实现同步功能
            console.log('同步消息');
          }}
          onCreateRule={() => {
            setRuleBaseMessage(null);
            setShowRuleModal(true);
          }}
          onSearch={() => {
            setShowFilterDrawer(true);
          }}
          onDownload={() => {
            // TODO: 实现下载功能
            console.log('下载消息');
          }}
          onSettings={() => {
            // TODO: 实现设置功能
            console.log('群组设置');
          }}
          isMobile={isMobile}
        />
      )}
      
      {/* 引用消息显示 */}
      {quotedMessage && (
        <QuotedMessage
          message={quotedMessage}
          onRemove={handleRemoveQuote}
        />
      )}
      
      {/* 消息输入组件 */}
      <MessageInput
        selectedGroup={chatState.selectedGroup}
        replyTo={replyTo}
        onSend={handleSendMessage}
        onClearReply={() => setReplyTo(null)}
        isMobile={isMobile}
        loading={loading}
      />
    </div>
  );

  return (
    <Layout 
      className="chat-interface" 
      ref={chatContainerRef}
      style={{
        paddingBottom: isKeyboardVisible ? keyboardHeight : 0,
        transition: 'padding-bottom 0.3s ease'
      }}
    >
      {renderHeader()}
      
      <div 
        className="chat-body"
        style={{
          overflow: isSwiping ? 'hidden' : 'auto'
        }}
      >
        {/* 桌面端布局 */}
        {!isMobile ? (
          <div className="desktop-layout">
            <div className={`group-list-panel ${chatState.isGroupListCollapsed ? 'collapsed' : ''}`}>
              {renderGroupList()}
            </div>
            <div className="message-panel">
              {renderMessageArea()}
              {renderMessageInput()}
            </div>
          </div>
        ) : (
          /* 移动端布局 */
          <>
            <Drawer
              title="群组列表"
              placement="left"
              onClose={toggleGroupList}
              open={!chatState.isGroupListCollapsed}
              width={280}
              className="mobile-group-drawer"
              style={{
                zIndex: 1000
              }}
            >
              {renderGroupList()}
            </Drawer>
            
            <div 
              className="mobile-message-panel"
              style={{
                marginBottom: isKeyboardVisible ? `${keyboardHeight}px` : 0,
                transition: 'margin-bottom 0.3s ease'
              }}
            >
              {renderMessageArea()}
              {renderMessageInput()}
            </div>
          </>
        )}
      </div>
      
      {/* 消息筛选抽屉 */}
      <MessageFilterDrawer
        visible={showFilterDrawer}
        onClose={() => setShowFilterDrawer(false)}
        selectedGroup={chatState.selectedGroup}
        currentFilter={chatState.messageFilter}
        onApplyFilter={handleApplyFilter}
        isMobile={isMobile}
      />
      
      {/* 快捷创建规则模态框 */}
      <QuickRuleModal
        visible={showRuleModal}
        onClose={() => {
          setShowRuleModal(false);
          setRuleBaseMessage(null);
        }}
        selectedGroup={chatState.selectedGroup}
        baseMessage={ruleBaseMessage}
        onSuccess={(rule) => {
          console.log('规则创建成功:', rule);
        }}
        isMobile={isMobile}
      />
    </Layout>
  );
};

export default ChatInterface;