// TypeScript类型定义

// 用户认证相关类型
export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  bio?: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at?: string;
  last_login?: string;
}

// 按月同步相关类型
export interface MonthInfo {
  year: number;
  month: number;
}

export interface MonthlySyncRequest {
  months: MonthInfo[];
}

export interface MonthlySyncResponse {
  success: boolean;
  total_messages: number;
  months_synced: number;
  failed_months: Array<{
    month: MonthInfo;
    error: string;
  }>;
  monthly_stats: Array<{
    year: number;
    month: number;
    total_messages: number;
    saved_messages: number;
    start_date: string;
    end_date: string;
  }>;
  error?: string;
}

export interface BatchMonthlySyncResponse {
  success: boolean;
  total_groups: number;
  synced_groups: number;
  failed_groups: Array<{
    group_id: number;
    title: string;
    error: string;
  }>;
  total_messages: number;
  group_results: Array<{
    group_id: number;
    title: string;
    result: MonthlySyncResponse;
  }>;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}

// Telegram相关类型
export interface TelegramGroup {
  id: number;
  telegram_id: number;
  title: string;
  username?: string;
  description?: string;
  member_count: number;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  is_pinned?: boolean; // 新增：群组置顶状态
  pinned_at?: string;  // 新增：置顶时间
  pin_order?: number;  // 新增：置顶排序
  can_send_messages?: boolean;
  permissions?: {
    can_send_messages?: boolean;
    can_send_media?: boolean;
    can_send_stickers?: boolean;
    can_send_gifs?: boolean;
    can_send_games?: boolean;
    can_use_inline_bots?: boolean;
  };
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
  media_filename?: string;
  media_file_id?: string;
  media_file_unique_id?: string;
  media_downloaded?: boolean;
  media_download_url?: string;
  media_download_error?: string;
  media_thumbnail_path?: string;
  media_thumbnail_url?: string;
  // 音频和语音字段
  audio?: {
    duration?: number;
    title?: string;
    performer?: string;
    file_name?: string;
    file_path?: string;
  };
  voice?: {
    duration?: number;
    file_path?: string;
  };
  video?: {
    duration?: number;
    width?: number;
    height?: number;
    file_path?: string;
  };
  view_count?: number;
  is_forwarded: boolean;
  forwarded_from?: string;
  forwarded_from_id?: number;
  forwarded_from_type?: 'user' | 'group' | 'channel';
  forwarded_date?: string;
  reply_to_message_id?: number;
  edit_date?: string;
  is_pinned: boolean;
  reactions?: Record<string, number> | ReactionEmoji[] | string;
  mentions?: string[];
  hashtags?: string[];
  urls?: string[];
  media_group_id?: string; // 新增：Telegram媒体组ID（用于分组多文件消息）
  date: string;
  created_at: string;
  updated_at?: string;
  is_own_message?: boolean; // 新增：标记是否为当前用户发送的消息
}

export interface ReactionEmoji {
  emoticon: string;
  count?: number;
}

export interface MessageSendRequest {
  text: string;
  reply_to_message_id?: number;
}

export interface MessageSearchRequest {
  query?: string;
  sender_username?: string;
  media_type?: string;
  start_date?: string;
  end_date?: string;
  has_media?: boolean;
  is_forwarded?: boolean;
}

// 规则相关类型
export interface FilterRule {
  id: number;
  name: string;
  // 移除 group_id - 群组关联由任务管理
  keywords: string[];
  exclude_keywords: string[];
  sender_filter?: string[];
  media_types: string[];
  date_from?: string;
  date_to?: string;
  min_views?: number;
  max_views?: number;
  min_file_size?: number;  // 最小文件大小（字节）
  max_file_size?: number;  // 最大文件大小（字节）
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
  date_from?: string;  // 时间范围过滤开始时间
  date_to?: string;    // 时间范围过滤结束时间
  
  // 调度配置
  task_type?: 'once' | 'recurring';  // 任务类型
  schedule_type?: 'interval' | 'cron' | 'daily' | 'weekly' | 'monthly';  // 调度类型
  schedule_config?: Record<string, any>;  // 调度配置
  next_run_time?: string;  // 下次执行时间
  last_run_time?: string;  // 最后执行时间
  is_active?: boolean;     // 是否启用调度
  max_runs?: number;       // 最大执行次数
  run_count?: number;      // 已执行次数
  
  created_at: string;
  updated_at: string;
  completed_at?: string;
  error_message?: string;
}

// 调度配置类型
export interface ScheduleConfig {
  // 间隔调度配置
  interval?: number;
  unit?: 'seconds' | 'minutes' | 'hours' | 'days';
  
  // 时间点调度配置
  hour?: number;
  minute?: number;
  
  // 周调度配置
  weekday?: number;  // 0=Monday, 6=Sunday
  
  // 月调度配置
  day?: number;  // 1-31
  
  // Cron表达式配置
  expression?: string;
}

// 任务调度表单数据
export interface TaskScheduleForm {
  task_type: 'once' | 'recurring';
  schedule_type?: 'interval' | 'cron' | 'daily' | 'weekly' | 'monthly';
  schedule_config?: ScheduleConfig;
  max_runs?: number;
}

// 日志类型
export interface LogEntry {
  id: number;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  message: string;
  task_id?: number;
  created_at: string;
  timestamp: string; // Add timestamp field
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

// 群组统计类型
export interface GroupStats {
  total_messages: number;
  media_messages: number;
  text_messages: number;
  member_count: number;
}