import React, { useState } from 'react';
import { message as antMessage, Input } from 'antd';
import { ChatProvider, useChatContext } from '../contexts/ChatContext';
import { useResponsiveLayout } from '../hooks/useResponsiveLayout';
import { mediaApi } from '../services/apiService';
import ChatLayout from '../components/Chat/Layout/ChatLayout';
import ChatHeader from '../components/Chat/Header/ChatHeader';
import ChatSidebar from '../components/Chat/Sidebar/ChatSidebar';
import MessageList from '../components/Chat/MessageList/MessageList';
import { Message as ChatMessage } from '../components/Chat/MessageList/MessageItem';
import ChatInput from '../components/Chat/Input/ChatInput';
import './ChatInterface.Refactored.css';

/**
 * ChatInterface Content Component
 * 使用新的组件化架构
 */
const ChatInterfaceContent: React.FC = () => {
  const {
    // Groups
    groups,
    selectedGroup,
    selectGroup,

    // Messages
    messages,
    loadingMessages,
    hasMoreMessages,
    loadMoreMessages,
    sendMessage,

    // UI State
    toggleSidebar,
    hideSidebar,

    // Search
    searchKeyword,
    setSearchKeyword,
  } = useChatContext();

  const { isMobile } = useResponsiveLayout();

  const [searchVisible, setSearchVisible] = useState(false);

  // Handle group selection
  const handleSelectGroup = (groupId: string) => {
    selectGroup(groupId);
    if (isMobile) {
      hideSidebar();
    }
  };

  // Handle search
  const handleSearch = () => {
    setSearchVisible(true);
};

  // Handle message download
  const handleDownload = async (chatMessage: ChatMessage) => {
    if (!selectedGroup) {
      antMessage.warning('请先选择群组');
      return;
    }

    const messageId = Number(chatMessage.id);
    if (!Number.isFinite(messageId)) {
      antMessage.error('消息ID无效，无法下载');
      return;
    }

    try {
      const result = await mediaApi.downloadMedia(Number(selectedGroup.id), messageId);
      if (result.success) {
        antMessage.success(result.message || '已启动下载');
      } else {
        antMessage.warning(result.message || '下载未完成');
      }
    } catch (error: any) {
      antMessage.error(`下载失败: ${error?.message || '未知错误'}`);
    }
  };

  const visibleMessages = React.useMemo(() => {
    const keyword = searchKeyword.trim().toLowerCase();
    if (!keyword) {
      return messages;
    }

    return messages.filter((item) => {
      const content = (item.content || '').toLowerCase();
      const sender = (item.sender || '').toLowerCase();
      return content.includes(keyword) || sender.includes(keyword);
    });
  }, [messages, searchKeyword]);

  return (
    <div className="chat-interface-refactored">
      <ChatLayout
        sidebar={
          <ChatSidebar
            groups={groups}
            selectedGroupId={selectedGroup?.id}
            onSelectGroup={handleSelectGroup}
            onSearch={setSearchKeyword}
          />
        }
        header={
          <ChatHeader
            groupName={selectedGroup?.name || '选择一个群组'}
            groupAvatar={selectedGroup?.avatar}
            memberCount={selectedGroup?.memberCount}
            onlineCount={selectedGroup?.onlineCount}
            onToggleSidebar={toggleSidebar}
            onSearch={handleSearch}
            showSidebarToggle={isMobile}
          />
        }
        main={
          <>
            {searchVisible && (
              <div style={{ padding: '8px 12px', borderBottom: '1px solid #f0f0f0' }}>
                <Input.Search
                  autoFocus
                  allowClear
                  placeholder="搜索消息内容或发送者..."
                  defaultValue={searchKeyword}
                  onSearch={(value) => {
                    setSearchKeyword(value.trim());
                    if (value.trim()) {
                      antMessage.success(`已应用搜索关键词: ${value.trim()}`);
                    } else {
                      antMessage.info('已清空搜索关键词');
                    }
                    setSearchVisible(false);
                  }}
                  onPressEnter={(e) => {
                    const val = (e.target as HTMLInputElement).value.trim();
                    setSearchKeyword(val);
                    setSearchVisible(false);
                  }}
                />
              </div>
            )}
            <MessageList
              messages={visibleMessages}
              loading={loadingMessages}
              hasMore={hasMoreMessages}
              onLoadMore={loadMoreMessages}
              onDownload={handleDownload}
            />
          </>
        }
        footer={
          <ChatInput
            onSend={sendMessage}
            placeholder="输入消息..."
            disabled={!selectedGroup}
          />
        }
      />
    </div>
  );
};

/**
 * ChatInterface Main Component
 * 包装ChatProvider提供全局状态
 */
const ChatInterfaceRefactored: React.FC = () => {
  return (
    <ChatProvider>
      <ChatInterfaceContent />
    </ChatProvider>
  );
};

export default ChatInterfaceRefactored;
