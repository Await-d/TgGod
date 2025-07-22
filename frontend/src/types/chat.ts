import { TelegramGroup, TelegramMessage } from './index';

// 聊天界面相关类型定义
export interface ChatState {
  selectedGroup: TelegramGroup | null;
  groups: TelegramGroup[];
  isGroupListCollapsed: boolean;
  isMobile: boolean;
  searchQuery: string;
  messageFilter: MessageFilter;
}

// 前端筛选条件格式（用于UI组件）
export interface MessageFilter {
  search?: string;
  sender_username?: string;
  media_type?: string;
  has_media?: boolean;
  is_forwarded?: boolean;
  is_pinned?: boolean;
  date_range?: [string, string]; // 前端日期范围格式
}

// 后端API筛选参数格式（用于API调用）
export interface MessageAPIFilter {
  search?: string;
  sender_username?: string;
  media_type?: string;
  has_media?: boolean;
  is_forwarded?: boolean;
  is_pinned?: boolean;
  start_date?: string; // 后端单独的开始日期
  end_date?: string;   // 后端单独的结束日期
  skip?: number;
  limit?: number;
}

export interface GroupListItemProps {
  group: TelegramGroup;
  isSelected: boolean;
  onClick: (group: TelegramGroup) => void;
  unreadCount?: number;
  lastMessageTime?: string;
  isMiniMode?: boolean;
  isTablet?: boolean;
}

export interface MessageBubbleProps {
  message: TelegramMessage;
  isOwn: boolean;
  showAvatar: boolean;
  onReply: (message: TelegramMessage) => void;
  onCreateRule: (message: TelegramMessage) => void;
  onDelete: (messageId: number) => void;
  onJumpToGroup?: (groupId: number) => void;
  onJumpToMessage?: (messageId: number) => void;
  onUpdateDownloadState?: (messageId: number, state: any) => void;
}

export interface MessageInputProps {
  selectedGroup: TelegramGroup | null;
  replyTo: TelegramMessage | null;
  onSend: (text: string) => void;
  onClearReply: () => void;
}

export interface QuickActionsProps {
  selectedGroup: TelegramGroup | null;
  onFilter: () => void;
  onSync: () => void;
  onCreateRule: () => void;
}

export interface ChatLayoutProps {
  children: React.ReactNode;
  className?: string;
}

// 聊天界面布局相关
export interface ChatLayoutState {
  groupListWidth: number;
  messageAreaWidth: number;
  isGroupListVisible: boolean;
}