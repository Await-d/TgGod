import React, { useState, useEffect, useCallback } from 'react';
import { Layout, Typography, Drawer, Button } from 'antd';
import { MenuOutlined, CloseOutlined } from '@ant-design/icons';
import { TelegramGroup, TelegramMessage } from '../types';
import { ChatState, MessageFilter } from '../types/chat';
import { useTelegramStore, useAuthStore } from '../store';
import { webSocketService } from '../services/websocket';
import GroupList from '../components/Chat/GroupList';
import MessageArea from '../components/Chat/MessageArea';
import './ChatInterface.css';

const { Title } = Typography;

const ChatInterface: React.FC = () => {
  // 状态管理
  const [chatState, setChatState] = useState<ChatState>({
    selectedGroup: null,
    isGroupListCollapsed: false,
    isMobile: false,
    searchQuery: '',
    messageFilter: {}
  });
  
  const [replyTo, setReplyTo] = useState<TelegramMessage | null>(null);
  const [loading, setLoading] = useState(false);
  
  // Store hooks
  const { groups, messages, setGroups, setMessages, setSelectedGroup } = useTelegramStore();
  const { isAuthenticated } = useAuthStore();

  // 检查是否为移动设备
  const checkMobile = useCallback(() => {
    const isMobile = window.innerWidth <= 768;
    setChatState(prev => ({ ...prev, isMobile }));
  }, []);

  // 监听窗口大小变化
  useEffect(() => {
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [checkMobile]);

  // 初始化WebSocket连接
  useEffect(() => {
    if (isAuthenticated) {
      try {
        webSocketService.connect();
      } catch (error) {
        console.error('WebSocket连接失败:', error);
      }
    }
    return () => webSocketService.disconnect();
  }, [isAuthenticated]);

  // 处理群组选择
  const handleGroupSelect = useCallback((group: TelegramGroup) => {
    setChatState(prev => ({ ...prev, selectedGroup: group }));
    setSelectedGroup(group);
    
    // 在移动端选择群组后关闭侧边栏
    if (chatState.isMobile) {
      setChatState(prev => ({ ...prev, isGroupListCollapsed: true }));
    }
  }, [chatState.isMobile, setSelectedGroup]);

  // 处理消息回复
  const handleReply = useCallback((message: TelegramMessage) => {
    setReplyTo(message);
  }, []);

  // 处理发送消息
  const handleSendMessage = useCallback(async (text: string) => {
    if (!chatState.selectedGroup) return;
    
    try {
      setLoading(true);
      // TODO: 实现发送消息逻辑
      console.log('发送消息:', text, '回复:', replyTo?.message_id);
      
      // 清除回复状态
      setReplyTo(null);
    } catch (error) {
      console.error('发送消息失败:', error);
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
      {chatState.isMobile && (
        <Button
          type="text"
          icon={chatState.isGroupListCollapsed ? <MenuOutlined /> : <CloseOutlined />}
          onClick={toggleGroupList}
          className="mobile-menu-btn"
        />
      )}
      <Title level={3} style={{ margin: 0 }}>
        {chatState.selectedGroup ? chatState.selectedGroup.title : '请选择群组'}
      </Title>
    </div>
  );

  // 渲染群组列表
  const renderGroupList = () => (
    <GroupList
      selectedGroup={chatState.selectedGroup}
      onGroupSelect={handleGroupSelect}
      searchQuery={chatState.searchQuery}
      onSearchChange={(query) => setChatState(prev => ({ ...prev, searchQuery: query }))}
      isMobile={chatState.isMobile}
    />
  );

  // 渲染消息区域
  const renderMessageArea = () => (
    <MessageArea
      selectedGroup={chatState.selectedGroup}
      onReply={handleReply}
      onCreateRule={(message) => {
        // TODO: 实现快捷创建规则功能
        console.log('创建规则:', message);
      }}
      searchFilter={chatState.messageFilter}
      isMobile={chatState.isMobile}
    />
  );

  // 渲染消息输入区域
  const renderMessageInput = () => (
    <div className="message-input-container">
      {replyTo && (
        <div className="reply-preview">
          <div className="reply-content">
            <span>回复: {replyTo.sender_name}</span>
            <span>{replyTo.text}</span>
          </div>
          <Button 
            type="text" 
            size="small" 
            onClick={() => setReplyTo(null)}
          >
            取消
          </Button>
        </div>
      )}
      
      <div className="input-controls">
        <input
          type="text"
          placeholder={chatState.selectedGroup ? "输入消息..." : "请先选择群组"}
          disabled={!chatState.selectedGroup}
          className="message-input"
          onKeyPress={(e) => {
            if (e.key === 'Enter' && e.currentTarget.value.trim()) {
              handleSendMessage(e.currentTarget.value.trim());
              e.currentTarget.value = '';
            }
          }}
        />
        <Button 
          type="primary" 
          disabled={!chatState.selectedGroup}
          loading={loading}
        >
          发送
        </Button>
      </div>
    </div>
  );

  return (
    <Layout className="chat-interface">
      {renderHeader()}
      
      <div className="chat-body">
        {/* 桌面端布局 */}
        {!chatState.isMobile ? (
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
            >
              {renderGroupList()}
            </Drawer>
            
            <div className="mobile-message-panel">
              {renderMessageArea()}
              {renderMessageInput()}
            </div>
          </>
        )}
      </div>
    </Layout>
  );
};

export default ChatInterface;