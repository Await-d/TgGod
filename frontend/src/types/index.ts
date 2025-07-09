// TypeScript类型定义

// Telegram相关类型
export interface TelegramGroup {
  id: number;
  title: string;
  username?: string;
  description?: string;
  member_count: number;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface TelegramMessage {
  id: number;
  group_id: number;
  message_id: number;
  sender_id?: number;
  sender_username?: string;
  sender_name?: string;
  text?: string;
  media_type?: 'photo' | 'video' | 'document' | 'audio' | 'voice' | 'sticker';
  media_path?: string;
  media_size?: number;
  view_count?: number;
  created_at: string;
  forwarded_from?: string;
}

// 规则相关类型
export interface FilterRule {
  id: number;
  name: string;
  group_id: number;
  keywords: string[];
  exclude_keywords: string[];
  sender_filter?: string[];
  media_types: string[];
  date_from?: string;
  date_to?: string;
  min_views?: number;
  max_views?: number;
  include_forwarded: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// 下载任务类型
export interface DownloadTask {
  id: number;
  name: string;
  group_id: number;
  rule_id: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused';
  progress: number;
  total_messages: number;
  downloaded_messages: number;
  download_path: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  error_message?: string;
}

// 日志类型
export interface LogEntry {
  id: number;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  message: string;
  task_id?: number;
  created_at: string;
  details?: Record<string, any>;
}

// WebSocket消息类型
export interface WebSocketMessage {
  type: 'log' | 'progress' | 'status' | 'notification';
  data: any;
  timestamp: string;
}

// API响应类型
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// 分页响应类型
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// 统计数据类型
export interface Statistics {
  total_groups: number;
  total_messages: number;
  total_downloads: number;
  active_tasks: number;
  storage_used: number;
  today_downloads: number;
}