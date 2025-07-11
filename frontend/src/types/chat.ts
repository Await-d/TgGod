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

export interface MessageFilter {
  search?: string;
  sender_username?: string;
  media_type?: string;
  has_media?: boolean;
  is_forwarded?: boolean;
  date_range?: [string, string];
}

export interface GroupListItemProps {
  group: TelegramGroup;
  isSelected: boolean;
  onClick: (group: TelegramGroup) => void;
  unreadCount?: number;
  lastMessageTime?: string;
}

export interface MessageBubbleProps {
  message: TelegramMessage;
  isOwn: boolean;
  showAvatar: boolean;
  onReply: (message: TelegramMessage) => void;
  onCreateRule: (message: TelegramMessage) => void;
  onDelete: (messageId: number) => void;
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