import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import { message } from 'antd';
import { telegramApi, messageApi } from '../services/apiService';
import { messageCacheService } from '../services/messageCacheService';

// Types
export interface GroupInfo {
  id: string;
  name: string;
  username?: string;
  avatar?: string;
  memberCount?: number;
  onlineCount?: number;
  lastMessage?: string;
  lastMessageTime?: Date;
  unreadCount?: number;
  status?: 'active' | 'paused';
}

export interface Message {
  id: string;
  type: 'text' | 'image' | 'video' | 'file' | 'audio';
  content: string;
  sender: string;
  timestamp: Date;
  mediaUrl?: string;
  thumbnailUrl?: string;
  fileSize?: number;
  fileName?: string;
  groupId?: string;
}

// API Response Types
interface GroupApiData {
  id: number;
  title?: string;
  username?: string;
  member_count?: number;
  status?: 'active' | 'paused';
}

interface MessageApiData {
  id: number;
  text?: string;
  media_type?: string;
  sender_name?: string;
  date: string;
  media_url?: string;
  thumbnail_url?: string;
  file_size?: number;
  file_name?: string;
}

interface MessageApiResponse {
  messages?: MessageApiData[];
  total?: number;
  length?: number;
}

// Helper function to convert API media type to Message type
const normalizeMediaType = (mediaType?: string): Message['type'] => {
  if (!mediaType) return 'text';
  const normalized = mediaType.toLowerCase();
  if (['image', 'video', 'file', 'audio'].includes(normalized)) {
    return normalized as Message['type'];
  }
  return 'text';
};

export interface ChatContextValue {
  // Groups
  groups: GroupInfo[];
  selectedGroup: GroupInfo | null;
  loadingGroups: boolean;
  selectGroup: (groupId: string) => void;
  loadGroups: () => Promise<void>;
  addGroup: (username: string) => Promise<void>;

  // Messages
  messages: Message[];
  loadingMessages: boolean;
  hasMoreMessages: boolean;
  loadMessages: (groupId: string) => Promise<void>;
  loadMoreMessages: () => Promise<void>;
  sendMessage: (content: string, files?: File[]) => Promise<void>;

  // UI State
  sidebarVisible: boolean;
  toggleSidebar: () => void;
  showSidebar: () => void;
  hideSidebar: () => void;

  // Search
  searchKeyword: string;
  setSearchKeyword: (keyword: string) => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export const useChatContext = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChatContext must be used within ChatProvider');
  }
  return context;
};

interface ChatProviderProps {
  children: ReactNode;
}

export const ChatProvider: React.FC<ChatProviderProps> = ({ children }) => {
  // Groups state
  const [groups, setGroups] = useState<GroupInfo[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<GroupInfo | null>(null);
  const [loadingGroups, setLoadingGroups] = useState(false);

  // Messages state
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [hasMoreMessages, setHasMoreMessages] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);

  // UI state
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [searchKeyword, setSearchKeyword] = useState('');

  // Load groups
  const loadGroups = useCallback(async () => {
    setLoadingGroups(true);
    try {
      const response: GroupApiData[] = await telegramApi.getGroups();
      const groupsData: GroupInfo[] = response.map((g) => ({
        id: g.id.toString(),
        name: g.title || g.username || 'Unknown',
        username: g.username,
        memberCount: g.member_count,
        status: g.status,
      }));
      setGroups(groupsData);
    } catch (error) {
      console.error('Failed to load groups:', error);
      message.error('加载群组失败');
    } finally {
      setLoadingGroups(false);
    }
  }, []);

  // Load messages
  const loadMessages = useCallback(async (groupId: string) => {
    setLoadingMessages(true);
    setCurrentPage(1);

    const cachedRaw = messageCacheService.getMessages(parseInt(groupId));
    if (cachedRaw && cachedRaw.length > 0) {
      const cachedMapped: Message[] = cachedRaw.map((m): Message => ({
        id: m.id.toString(),
        type: normalizeMediaType(m.media_type),
        content: m.text || '',
        sender: m.sender_name || 'Unknown',
        timestamp: new Date(m.date),
        mediaUrl: m.media_path,
        thumbnailUrl: m.media_thumbnail_url,
        fileSize: m.media_size,
        fileName: m.media_filename,
        groupId,
      }));
      setMessages(cachedMapped);
      setLoadingMessages(false);
    }

    try {
      const response: MessageApiResponse = await messageApi.getGroupMessages(parseInt(groupId), { skip: 0, limit: 50 });
      const messagesData: Message[] = (response.messages || []).map((m): Message => ({
        id: m.id.toString(),
        type: normalizeMediaType(m.media_type),
        content: m.text || '',
        sender: m.sender_name || 'Unknown',
        timestamp: new Date(m.date),
        mediaUrl: m.media_url,
        thumbnailUrl: m.thumbnail_url,
        fileSize: m.file_size,
        fileName: m.file_name,
        groupId,
      }));
      setMessages(messagesData);
      setHasMoreMessages((response.total || messagesData.length) > 50);
      messageCacheService.saveMessages(parseInt(groupId), (response.messages || []) as any);
    } catch (error) {
      console.error('Failed to load messages:', error);
      if (!cachedRaw || cachedRaw.length === 0) {
        message.error('加载消息失败');
      }
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  // Select group
  const selectGroup = useCallback(
    (groupId: string) => {
      const group = groups.find((g) => g.id === groupId);
      if (group) {
        setSelectedGroup(group);
        loadMessages(groupId);
      }
    },
    [groups, loadMessages]
  );

  // Load more messages
  const loadMoreMessages = useCallback(async () => {
    if (!selectedGroup || !hasMoreMessages || loadingMessages) return;

    const nextPage = currentPage + 1;
    const skip = nextPage * 50;
    setLoadingMessages(true);
    try {
      const response: MessageApiResponse = await messageApi.getGroupMessages(parseInt(selectedGroup.id), { skip, limit: 50 });
      const messagesData: Message[] = (response.messages || []).map((m): Message => ({
        id: m.id.toString(),
        type: normalizeMediaType(m.media_type),
        content: m.text || '',
        sender: m.sender_name || 'Unknown',
        timestamp: new Date(m.date),
        mediaUrl: m.media_url,
        thumbnailUrl: m.thumbnail_url,
        fileSize: m.file_size,
        fileName: m.file_name,
        groupId: selectedGroup.id,
      }));
      setMessages((prev) => [...messagesData, ...prev]);
      setCurrentPage(nextPage);
      setHasMoreMessages((response.total || messagesData.length) > skip + 50);
    } catch (error) {
      console.error('Failed to load more messages:', error);
      message.error('加载更多消息失败');
    } finally {
      setLoadingMessages(false);
    }
  }, [selectedGroup, hasMoreMessages, loadingMessages, currentPage]);

  const sendMessage = useCallback(
    async (content: string, files?: File[]) => {
      if (!selectedGroup) return;

      const text = content.trim();
      if (!text && (!files || files.length === 0)) {
        return;
      }

      try {
        const groupId = parseInt(selectedGroup.id, 10);

        if (files && files.length > 0) {
          await messageApi.sendMediaMessage(groupId, {
            files,
            text: text || undefined,
          });
        } else {
          await messageApi.sendMessage(groupId, {
            text,
          });
        }

        message.success('消息发送成功');

        await loadMessages(selectedGroup.id);
      } catch (error) {
        console.error('Failed to send message:', error);
        message.error('发送消息失败');
      }
    },
    [selectedGroup, loadMessages]
  );

  // Add group
  const addGroup = useCallback(
    async (username: string) => {
      try {
        await telegramApi.addGroup(username);
        message.success('群组添加成功');
        await loadGroups();
      } catch (error) {
        console.error('Failed to add group:', error);
        message.error('添加群组失败');
      }
    },
    [loadGroups]
  );

  // Sidebar controls
  const toggleSidebar = useCallback(() => {
    setSidebarVisible((prev) => !prev);
  }, []);

  const showSidebar = useCallback(() => {
    setSidebarVisible(true);
  }, []);

  const hideSidebar = useCallback(() => {
    setSidebarVisible(false);
  }, []);

  // Load groups on mount
  useEffect(() => {
    loadGroups();
  }, [loadGroups]);

  const value: ChatContextValue = {
    // Groups
    groups,
    selectedGroup,
    loadingGroups,
    selectGroup,
    loadGroups,
    addGroup,

    // Messages
    messages,
    loadingMessages,
    hasMoreMessages,
    loadMessages,
    loadMoreMessages,
    sendMessage,

    // UI State
    sidebarVisible,
    toggleSidebar,
    showSidebar,
    hideSidebar,

    // Search
    searchKeyword,
    setSearchKeyword,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
};

export default ChatContext;
