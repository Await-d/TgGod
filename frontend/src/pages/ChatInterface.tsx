import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Layout, Typography, Drawer, Button, message as antMessage } from 'antd';
import { MenuOutlined, CloseOutlined } from '@ant-design/icons';
import { TelegramGroup, TelegramMessage } from '../types';
import { ChatState, MessageFilter } from '../types/chat';
import { useTelegramStore, useAuthStore } from '../store';
import { webSocketService } from '../services/websocket';
import { messageApi, telegramApi } from '../services/apiService';
import { useMobileGestures, useIsMobile, useKeyboardHeight } from '../hooks/useMobileGestures';
// import { useChatPageScrollControl } from '../hooks/usePageScrollControl';
import { useChatGroupNavigation } from '../hooks/useGroupNavigation';
import { useRealTimeMessages } from '../hooks/useRealTimeMessages';
import { useInfiniteScroll } from '../hooks/useInfiniteScroll';
import { useLocation, useSearchParams } from 'react-router-dom';  // 新增导入
import GroupList from '../components/Chat/GroupList';
import MessageArea from '../components/Chat/MessageArea';
import MessageInput from '../components/Chat/MessageInput';
import QuickActions from '../components/Chat/QuickActions';
import MessageFilterDrawer from '../components/Chat/MessageFilterDrawer';
import MessageSearchDrawer from '../components/Chat/MessageSearchDrawer';
import MessageDownloadModal from '../components/Chat/MessageDownloadModal';
import GroupSettingsModal from '../components/Chat/GroupSettingsModal';
import QuickRuleModal from '../components/Chat/QuickRuleModal';
import MessageHighlight from '../components/Chat/MessageHighlight';
import MediaPreview from '../components/Chat/MediaPreview';
import VoiceMessage from '../components/Chat/VoiceMessage';
import MessageQuoteForward, { QuotedMessage } from '../components/Chat/MessageQuoteForward';
import './ChatInterface.css';

const { Title } = Typography;

const ChatInterface: React.FC = () => {
  // 添加URL相关hooks
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

  // 页面滚动控制 - 移除，允许正常滚动
  // useChatPageScrollControl();

  // 移动端和平板检测
  const isMobile = useIsMobile();
  const [isTablet, setIsTablet] = useState(false);
  const [groupListWidth, setGroupListWidth] = useState(380);
  const [isGroupListMini, setIsGroupListMini] = useState(false);
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
    setMessages,
    mergeMessages,
    prependMessages
  } = useChatGroupNavigation();

  // 从 store 获取 addGroup 方法
  const { addGroup } = useTelegramStore();

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
      // 使用智能合并，避免重复消息
      console.log('无限滚动合并消息:', updatedMessages.length);
      mergeMessages(updatedMessages);
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
    groups: [],
    isGroupListCollapsed: false,
    isMobile: false,
    searchQuery: '',
    messageFilter: {}
  });

  // 平板模式检测和响应
  useEffect(() => {
    const checkTabletMode = () => {
      const width = window.innerWidth;
      const newIsTablet = width > 768 && width <= 1200; // 平板模式范围
      setIsTablet(newIsTablet);

      // 平板模式下自动调整群组列表宽度
      if (newIsTablet) {
        if (width <= 900) {
          setGroupListWidth(280); // 较小平板
        } else {
          setGroupListWidth(320); // 较大平板
        }
      } else if (!isMobile) {
        setGroupListWidth(380); // 桌面模式
      }
    };

    checkTabletMode();
    window.addEventListener('resize', checkTabletMode);
    return () => window.removeEventListener('resize', checkTabletMode);
  }, [isMobile]);

  // 群组列表控制功能
  const toggleGroupListMini = useCallback(() => {
    setIsGroupListMini(!isGroupListMini);
  }, [isGroupListMini]);

  const adjustGroupListWidth = useCallback((width: number) => {
    const minWidth = isTablet ? 280 : 320;
    const maxWidth = isTablet ? 400 : 500;
    setGroupListWidth(Math.max(minWidth, Math.min(maxWidth, width)));
  }, [isTablet]);

  const [replyTo, setReplyTo] = useState<TelegramMessage | null>(null);
  const [quotedMessage, setQuotedMessage] = useState<TelegramMessage | null>(null);
  const [contacts, setContacts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(false);
  const [showFilterDrawer, setShowFilterDrawer] = useState(false);
  const [showSearchDrawer, setShowSearchDrawer] = useState(false);
  const [showDownloadModal, setShowDownloadModal] = useState(false);
  const [showGroupSettings, setShowGroupSettings] = useState(false);
  const [showRuleModal, setShowRuleModal] = useState(false);
  const [ruleBaseMessage, setRuleBaseMessage] = useState<TelegramMessage | null>(null);
  const [globalError, setGlobalError] = useState<string | null>(null);

  // 置顶消息状态 - 移除，不再需要单独的置顶消息组件
  // const [showPinnedMessages, setShowPinnedMessages] = useState(true);
  const [jumpToMessageId, setJumpToMessageId] = useState<number | null>(null);

  // 同步选中群组到内部状态
  useEffect(() => {
    setChatState(prev => ({
      ...prev,
      selectedGroup: selectedGroup,
      isMobile: isMobile
    }));
  }, [selectedGroup, isMobile]);

  // 同步群组列表到内部状态
  useEffect(() => {
    setChatState(prev => ({
      ...prev,
      groups: groups || []
    }));
  }, [groups]);

  // 确保页面加载完成后，保存当前URL参数
  useEffect(() => {
    // 当页面加载时，检查当前URL中是否有group参数
    const groupParam = searchParams.get('group');
    console.log('当前URL中的群组参数:', groupParam);

    // 如果有group参数，确保它在selectedGroup变化后依然保留
    if (groupParam && selectedGroup && groupParam !== selectedGroup.id.toString()) {
      console.log('同步选中群组到URL:', selectedGroup.id);
      const newParams = new URLSearchParams(searchParams);
      newParams.set('group', selectedGroup.id.toString());
      setSearchParams(newParams, { replace: true });
    }
  }, [selectedGroup, searchParams, setSearchParams]);

  // 添加一个独立的effect来处理初始群组恢复
  useEffect(() => {
    // 这个effect专门用于处理页面加载时的群组恢复
    if (groups.length > 0) {
      // 从URL参数中获取群组ID
      const urlGroupId = searchParams.get('group');

      // 检查URL参数中是否有有效的群组ID
      if (urlGroupId) {
        const groupFromUrl = groups.find(g => g.id.toString() === urlGroupId);
        if (groupFromUrl) {
          console.log('页面加载：从URL恢复群组:', groupFromUrl.title);
          selectGroup(groupFromUrl);
          return; // 如果从URL恢复了群组，就不再尝试其他方式
        }
      }

      // 如果URL中没有参数，尝试从sessionStorage恢复
      const storedGroupId = sessionStorage.getItem('last_selected_group_id');
      if (storedGroupId) {
        const storedGroup = groups.find(g => g.id.toString() === storedGroupId);
        if (storedGroup) {
          console.log('页面加载：从sessionStorage恢复群组:', storedGroup.title);
          selectGroup(storedGroup);

          // 确保URL也被更新
          const newParams = new URLSearchParams(searchParams);
          newParams.set('group', storedGroupId);
          setSearchParams(newParams, { replace: true });
          return;
        }
      }

      // 如果没有恢复到任何群组，则选择默认群组
      if (!selectedGroup) {
        const defaultGroup = groups.find(g => g.is_active) || groups[0];
        if (defaultGroup) {
          console.log('页面加载：选择默认群组:', defaultGroup.title);
          selectGroup(defaultGroup);
        }
      }
    }
  }, [groups.length, searchParams, setSearchParams, selectGroup, selectedGroup]);

  // 确保用户手动点击群组时会保存记录
  useEffect(() => {
    if (selectedGroup) {
      console.log('保存当前群组到sessionStorage:', selectedGroup.title);
      sessionStorage.setItem('last_selected_group_id', selectedGroup.id.toString());

      // 确保URL也被更新
      const newParams = new URLSearchParams(searchParams);
      newParams.set('group', selectedGroup.id.toString());
      setSearchParams(newParams, { replace: true });
    }
  }, [selectedGroup, searchParams, setSearchParams]);

  // 监听浏览器前进后退操作
  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const groupId = params.get('group');

      if (groupId && (!selectedGroup || selectedGroup.id.toString() !== groupId)) {
        console.log('检测到浏览器导航操作，恢复群组:', groupId);
        navigateToGroup(groupId);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, [selectedGroup, navigateToGroup]);

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

  // 处理跳转到群组
  const handleJumpToGroup = useCallback(async (groupId: number) => {
    console.log('ChatInterface - handleJumpToGroup called', {
      groupId,
      totalGroups: groups.length,
      availableGroupIds: groups.map(g => g.id)
    });

    // 首先在当前群组列表中查找
    let targetGroup = groups.find(group => group.id === groupId);

    if (targetGroup) {
      console.log('ChatInterface - found target group in current list:', targetGroup);
      selectGroup(targetGroup);
      antMessage.success(`已跳转到${targetGroup!.title}`);
      return;
    }

    // 如果在当前列表中找不到，尝试从API获取
    console.log('ChatInterface - target group not found in current list, fetching from API...');
    try {
      targetGroup = await telegramApi.getGroup(groupId);
      console.log('ChatInterface - fetched target group from API:', targetGroup);

      if (!targetGroup) {
        console.error('ChatInterface - API returned undefined group');
        antMessage.error('无法获取群组信息');
        return;
      }

      // 将获取到的群组添加到当前群组列表中（如果不存在）
      const existingGroup = groups.find(g => g.id === targetGroup!.id);
      if (!existingGroup) {
        // 更新群组列表状态
        addGroup(targetGroup);
        console.log('ChatInterface - added new group to list:', targetGroup!.title);
      }

      selectGroup(targetGroup);
      antMessage.success(`已跳转到${targetGroup!.title}`);

    } catch (error) {
      console.error('ChatInterface - failed to fetch group from API:', error);
      antMessage.error(`无法找到群组 (ID: ${groupId})，可能已被删除或无权限访问`);
    }
  }, [groups, selectGroup, addGroup]);

  // 处理跳转到消息
  const handleJumpToMessage = useCallback((messageId: number) => {
    setJumpToMessageId(messageId);
    // 移除置顶消息相关逻辑
  }, []);

  // 处理跳转完成
  const handleJumpComplete = useCallback(() => {
    setJumpToMessageId(null);
  }, []);

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

  // 处理消息刷新
  const handleRefreshMessages = useCallback(async () => {
    if (!selectedGroup) return;

    try {
      setLoading(true);

      // 重置状态并获取最新消息
      resetInfiniteScroll();
      await fetchLatestMessages(selectedGroup.id, 50);

      antMessage.success('消息刷新成功！');
    } catch (error: any) {
      antMessage.error('刷新消息失败: ' + error.message);
      console.error('刷新消息失败:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedGroup, resetInfiniteScroll, fetchLatestMessages]);

  // 处理消息同步
  const handleSyncMessages = useCallback(async () => {
    if (!selectedGroup) return;

    try {
      setLoading(true);

      // 调用同步API
      await telegramApi.syncGroupMessages(selectedGroup.id, 100);

      // 同步完成后刷新消息列表
      resetInfiniteScroll();
      await fetchLatestMessages(selectedGroup.id, 50);

      antMessage.success('消息同步成功！');
    } catch (error: any) {
      antMessage.error('同步消息失败: ' + error.message);
      console.error('同步消息失败:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedGroup, resetInfiniteScroll, fetchLatestMessages]);

  // 切换群组列表显示/隐藏
  const toggleGroupList = useCallback(() => {
    setChatState(prev => ({
      ...prev,
      isGroupListCollapsed: !prev.isGroupListCollapsed
    }));
  }, []);

  // 渲染头部标题
  // 渲染群组列表
  const renderGroupList = () => (
    <GroupList
      selectedGroup={chatState.selectedGroup}
      onGroupSelect={handleGroupSelect}
      searchQuery={chatState.searchQuery}
      onSearchChange={(query) => setChatState(prev => ({ ...prev, searchQuery: query }))}
      isMobile={isMobile}
      isTablet={isTablet}
      isGroupListMini={isGroupListMini}
      onToggleMini={toggleGroupListMini}
      groupListWidth={groupListWidth}
      onWidthChange={adjustGroupListWidth}
    />
  );

  // 渲染消息区域
  const renderMessageArea = () => (
    <div className="message-area-container">
      {/* 消息区域 */}
      <MessageArea
        selectedGroup={selectedGroup}
        onReply={handleReply}
        onCreateRule={handleCreateQuickRule}
        searchFilter={chatState.messageFilter}
        isMobile={isMobile}
        isTablet={isTablet}
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
        // 跳转功能
        jumpToMessageId={jumpToMessageId}
        onJumpComplete={handleJumpComplete}
        onJumpToGroup={handleJumpToGroup}
        onJumpToMessage={handleJumpToMessage}
      />
    </div>
  );

  // 渲染消息输入区域
  const renderMessageInput = () => (
    <div className="message-input-wrapper">
      {/* 快捷操作按钮 */}
      {chatState.selectedGroup && (
        <QuickActions
          selectedGroup={chatState.selectedGroup}
          onFilter={() => setShowFilterDrawer(true)}
          onRefresh={handleRefreshMessages}
          onSync={handleSyncMessages}
          loading={loading}
          onCreateRule={() => {
            setRuleBaseMessage(null);
            setShowRuleModal(true);
          }}
          onSearch={() => {
            setShowSearchDrawer(true);
          }}
          onDownload={() => {
            setShowDownloadModal(true);
          }}
          onSettings={() => {
            setShowGroupSettings(true);
          }}
          isMobile={isMobile}
          allGroups={chatState.groups}
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
      <div
        className="chat-body"
        style={{
          overflow: isSwiping ? 'hidden' : 'auto'
        }}
      >
        {/* 桌面端布局 */}
        {!isMobile ? (
          <div className={`desktop-layout ${isTablet ? 'tablet-mode' : ''}`}>
            <div
              className={`group-list-panel ${chatState.isGroupListCollapsed ? 'collapsed' : ''} ${isGroupListMini ? 'mini-mode' : ''}`}
              style={{
                width: chatState.isGroupListCollapsed ? 0 : (isGroupListMini ? 80 : groupListWidth),
                minWidth: chatState.isGroupListCollapsed ? 0 : (isGroupListMini ? 80 : (isTablet ? 280 : 320)),
                maxWidth: isGroupListMini ? 80 : (isTablet ? 400 : 500)
              }}
            >
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
              {/* 移动端头部 */}
              <div className="mobile-header">
                <Button
                  type="text"
                  icon={<MenuOutlined />}
                  onClick={toggleGroupList}
                  className="mobile-menu-btn"
                />
                <Title level={4} style={{ margin: 0, flex: 1, textAlign: 'center' }}>
                  {chatState.selectedGroup ? chatState.selectedGroup.title : '请选择群组'}
                </Title>
                {/* 连接状态指示器 */}
                <div className={`connection-status ${connectionStatus}`}>
                  <span className="status-dot"></span>
                </div>
              </div>

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

      {/* 消息搜索抽屉 */}
      <MessageSearchDrawer
        visible={showSearchDrawer}
        onClose={() => setShowSearchDrawer(false)}
        selectedGroup={chatState.selectedGroup}
        onMessageSelect={(message) => {
          // 可以在这里添加跳转到消息的逻辑
          console.log('选择消息:', message);
        }}
        isMobile={isMobile}
      />

      {/* 消息下载模态框 */}
      <MessageDownloadModal
        visible={showDownloadModal}
        onClose={() => setShowDownloadModal(false)}
        selectedGroup={chatState.selectedGroup}
        onSuccess={(task) => {
          console.log('下载任务创建成功:', task);
        }}
        isMobile={isMobile}
      />

      {/* 群组设置模态框 */}
      <GroupSettingsModal
        visible={showGroupSettings}
        onClose={() => setShowGroupSettings(false)}
        selectedGroup={chatState.selectedGroup}
        onGroupUpdate={(group) => {
          // 更新群组信息
          console.log('群组信息更新:', group);
          // 可以在这里更新 store 中的群组信息
        }}
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