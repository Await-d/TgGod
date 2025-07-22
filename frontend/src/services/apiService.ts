import axios from 'axios';
import { 
  User, 
  LoginRequest, 
  LoginResponse, 
  RegisterRequest,
  TelegramGroup,
  TelegramMessage,
  MessageSendRequest,
  MessageSearchRequest,
  GroupStats,
  FilterRule,
  DownloadTask,
  PaginatedResponse,
  LogEntry
} from '../types';

// 创建axios实例
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 从localStorage或store获取token
    const token = localStorage.getItem('auth-storage') ? 
      JSON.parse(localStorage.getItem('auth-storage')!).state.token : null;
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    if (error.response?.status === 401) {
      // 清除认证信息
      localStorage.removeItem('auth-storage');
      window.location.href = '/login';
    }
    
    const message = error.response?.data?.detail || error.message || '请求失败';
    return Promise.reject(new Error(message));
  }
);

// 认证相关API
export const authApi = {
  // 用户登录
  login: (credentials: LoginRequest): Promise<LoginResponse> => {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    
    return api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  },

  // 用户注册
  register: (userData: RegisterRequest): Promise<User> => {
    return api.post('/auth/register', userData);
  },

  // 获取当前用户信息
  getCurrentUser: (): Promise<User> => {
    return api.get('/auth/me');
  },

  // 更新用户信息
  updateUser: (userData: Partial<User>): Promise<User> => {
    return api.put('/auth/me', userData);
  },

  // 用户登出
  logout: (): Promise<{ message: string }> => {
    return api.post('/auth/logout');
  },

  // 获取管理员信息
  getAdminInfo: (): Promise<any> => {
    return api.get('/auth/admin-info');
  },

  // 获取用户列表
  getUsers: (skip: number = 0, limit: number = 10): Promise<User[]> => {
    return api.get('/auth/users', { params: { skip, limit } });
  },
};

// Telegram群组相关API
export const telegramApi = {
  // 获取群组列表
  getGroups: (skip: number = 0, limit: number = 100): Promise<TelegramGroup[]> => {
    return api.get('/telegram/groups', { params: { skip, limit } });
  },

  // 获取所有群组（自动分页处理）
  getAllGroups: async (): Promise<TelegramGroup[]> => {
    const allGroups: TelegramGroup[] = [];
    let skip = 0;
    const limit = 1000; // 使用最大限制
    
    while (true) {
      const response = await api.get('/telegram/groups', { params: { skip, limit } });
      const groups = response.data || response; // 处理可能的响应格式差异
      
      if (!groups || groups.length === 0) {
        break;
      }
      
      allGroups.push(...groups);
      
      // 如果返回的群组数量小于limit，说明已经获取完所有数据
      if (groups.length < limit) {
        break;
      }
      
      skip += limit;
    }
    
    return allGroups;
  },

  // 添加群组
  addGroup: (username: string): Promise<TelegramGroup> => {
    return api.post('/telegram/groups', { username });
  },

  // 获取群组信息
  getGroup: (groupId: number): Promise<TelegramGroup> => {
    return api.get(`/telegram/groups/${groupId}`);
  },

  // 通过用户名获取群组信息（搜索现有群组）
  getGroupByUsername: async (username: string): Promise<TelegramGroup | null> => {
    try {
      const groups = await api.get('/telegram/groups', { 
        params: { limit: 1000 } 
      }) as TelegramGroup[];
      
      const group = groups.find(g => 
        g.username && g.username.toLowerCase() === username.toLowerCase()
      );
      
      return group || null;
    } catch (error) {
      console.error('Failed to get group by username:', error);
      return null;
    }
  },

  // 更新群组
  updateGroup: (groupId: number, data: Partial<TelegramGroup>): Promise<TelegramGroup> => {
    return api.put(`/telegram/groups/${groupId}`, data);
  },

  // 同步群组信息
  syncGroup: (groupId: number): Promise<TelegramGroup> => {
    return api.post(`/telegram/groups/${groupId}/sync-info`);
  },

  // 根据Telegram ID查找群组
  searchGroupByTelegramId: (telegramId: number): Promise<TelegramGroup | null> => {
    return api.get(`/telegram/groups/search-by-id/${telegramId}`);
  },

  // 删除群组
  deleteGroup: (groupId: number): Promise<{ message: string }> => {
    return api.delete(`/telegram/groups/${groupId}`);
  },


  // 同步群组消息
  syncGroupMessages: (groupId: number, limit: number = 100): Promise<{ message: string }> => {
    return api.post(`/telegram/groups/${groupId}/sync`, { limit });
  },

  // 按月同步群组消息（异步任务，不等待完成）
  syncGroupMessagesMonthly: (groupId: number, months: Array<{year: number, month: number}>): Promise<{success: boolean, message: string, task_id?: string}> => {
    return api.post(`/telegram/groups/${groupId}/sync-monthly`, { months });
  },

  // 获取默认同步月份
  getDefaultSyncMonths: (groupId: number, count: number = 3): Promise<{months: Array<{year: number, month: number}>}> => {
    return api.get(`/telegram/groups/${groupId}/default-sync-months`, { params: { count } });
  },

  // 批量按月同步所有群组
  syncAllGroupsMonthly: (months: Array<{year: number, month: number}>): Promise<any> => {
    return api.post('/telegram/sync-all-groups-monthly', { months });
  },

  // 批量同步指定群组消息
  batchSyncGroupMessages: (groupIds: number[], limit: number = 100): Promise<{
    success: boolean;
    message: string;
    results: Array<{
      group_id: number;
      group_title: string;
      success: boolean;
      message: string;
      sync_count?: number;
    }>;
  }> => {
    return api.post('/telegram/batch-sync-messages', { group_ids: groupIds, limit });
  },

  // 从Telegram同步群组列表
  syncGroups: (): Promise<{
    success: boolean;
    message: string;
    synced_count: number;
    total_groups: number;
    errors: string[];
  }> => {
    return api.post('/telegram/sync-groups');
  },

  // 获取当前 Telegram 用户信息
  getCurrentTelegramUser: (): Promise<{
    id: number;
    username: string | null;
    first_name: string | null;
    last_name: string | null;
    full_name: string | null;
    is_self: boolean;
  }> => {
    return api.get('/telegram/me');
  },

  // 获取同步状态
  getSyncStatus: (): Promise<{
    success: boolean;
    data: {
      is_running: boolean;
      active_groups: number[];
      total_groups: number;
    };
  }> => {
    return api.get('/telegram/sync-status');
  },

  // 控制同步任务
  controlSync: (action: 'start' | 'stop'): Promise<{
    success: boolean;
    message: string;
  }> => {
    return api.post('/telegram/sync-control', { action });
  },

  // 启用/禁用群组实时同步
  enableRealtimeSync: (groupId: number, enabled: boolean): Promise<{
    success: boolean;
    message: string;
  }> => {
    return api.post(`/telegram/groups/${groupId}/enable-realtime`, { enabled });
  },

  // 获取群组统计信息
  getGroupStats: (groupId: number): Promise<{
    total_messages: number;
    media_messages: number;
    text_messages: number;
    photo_messages: number;
    video_messages: number;
    document_messages: number;
    audio_messages: number;
    forwarded_messages: number;
    pinned_messages: number;
    messages_with_reactions: number;
    member_count: number;
  }> => {
    return api.get(`/telegram/groups/${groupId}/stats`);
  },

  // 获取群组预览信息（通过用户名）
  getGroupPreview: (username: string): Promise<{
    id: number;
    title: string;
    description?: string;
    member_count?: number;
    is_joined: boolean;
    is_public: boolean;
    photo_url?: string;
  }> => {
    return api.get(`/telegram/groups/preview/${username}`);
  },

  // 获取群组预览信息（通过邀请链接）
  getGroupPreviewByInvite: (inviteHash: string): Promise<{
    id: number;
    title: string;
    description?: string;
    member_count?: number;
    is_joined: boolean;
    is_public: boolean;
    photo_url?: string;
  }> => {
    return api.get(`/telegram/groups/preview/invite/${inviteHash}`);
  },

  // 加入公开群组
  joinGroup: (username: string): Promise<{
    success: boolean;
    group: TelegramGroup;
    message: string;
  }> => {
    return api.post(`/telegram/groups/join/${username}`);
  },

  // 通过邀请链接加入群组
  joinGroupByInvite: (inviteHash: string): Promise<{
    success: boolean;
    group: TelegramGroup;
    message: string;
  }> => {
    return api.post(`/telegram/groups/join/invite/${inviteHash}`);
  },
};

// 消息相关API
export const messageApi = {
  // 获取群组消息
  getGroupMessages: (
    groupId: number,
    params: {
      skip?: number;
      limit?: number;
      search?: string;
      sender_username?: string;
      media_type?: string;
      has_media?: boolean;
      is_forwarded?: boolean;
      start_date?: string;
      end_date?: string;
    } = {}
  ): Promise<TelegramMessage[]> => {
    return api.get(`/telegram/groups/${groupId}/messages`, { params });
  },

  // 获取群组消息（分页版本，用于Messages页面）
  getGroupMessagesPaginated: (
    groupId: number,
    params: {
      skip?: number;
      limit?: number;
      search?: string;
      sender_username?: string;
      media_type?: string;
      has_media?: boolean;
      is_forwarded?: boolean;
      is_pinned?: boolean;
      start_date?: string;
      end_date?: string;
    } = {}
  ): Promise<{data: TelegramMessage[], pagination: {current: number, pageSize: number, total: number}}> => {
    return api.get(`/telegram/groups/${groupId}/messages/paginated`, { params });
  },

  // 获取群组置顶消息
  getPinnedMessages: (groupId: number): Promise<TelegramMessage[]> => {
    return api.get(`/telegram/groups/${groupId}/messages`, { 
      params: { is_pinned: true, limit: 100 } 
    });
  },

  // 获取消息详情
  getMessageDetail: (groupId: number, messageId: number): Promise<TelegramMessage> => {
    return api.get(`/telegram/groups/${groupId}/messages/${messageId}`);
  },

  // 根据消息ID获取消息（用于转发消息预览）
  getMessageById: (groupId: number, messageId: number): Promise<TelegramMessage> => {
    return api.get(`/telegram/groups/${groupId}/messages/${messageId}`);
  },

  // 获取消息回复
  getMessageReplies: (
    groupId: number, 
    messageId: number, 
    skip: number = 0, 
    limit: number = 100
  ): Promise<TelegramMessage[]> => {
    return api.get(`/telegram/groups/${groupId}/messages/${messageId}/replies`, {
      params: { skip, limit }
    });
  },

  // 发送消息
  sendMessage: (groupId: number, message: MessageSendRequest): Promise<{
    success: boolean;
    message_id: number;
    message: string;
  }> => {
    return api.post(`/telegram/groups/${groupId}/send`, message);
  },

  // 回复消息
  replyMessage: (groupId: number, messageId: number, text: string): Promise<{
    success: boolean;
    message_id: number;
    reply_to_message_id: number;
    message: string;
  }> => {
    return api.post(`/telegram/groups/${groupId}/messages/${messageId}/reply`, { text });
  },

  // 删除消息
  deleteMessage: (groupId: number, messageId: number): Promise<{
    success: boolean;
    message: string;
  }> => {
    return api.delete(`/telegram/groups/${groupId}/messages/${messageId}`);
  },

  // 清空群组所有消息（通过批量调用单个删除API实现）
  clearGroupMessages: async (groupId: number, onProgress?: (progress: { current: number; total: number; }) => void): Promise<{
    success: boolean;
    deletedCount: number;
    failedCount: number;
    message: string;
  }> => {
    try {
      // 首先获取群组的所有消息
      const allMessages: TelegramMessage[] = [];
      let page = 0;
      const pageSize = 100;
      let hasMore = true;

      // 分页获取所有消息
      while (hasMore) {
        const response = await messageApi.getGroupMessages(groupId, {
          skip: page * pageSize,
          limit: pageSize
        });
        
        if (response.length === 0) {
          hasMore = false;
        } else {
          allMessages.push(...response);
          page++;
          // 避免获取过多消息，设置上限
          if (allMessages.length >= 10000) {
            hasMore = false;
          }
        }
      }

      if (allMessages.length === 0) {
        return {
          success: true,
          deletedCount: 0,
          failedCount: 0,
          message: '群组中没有消息需要删除'
        };
      }

      // 批量删除消息
      let deletedCount = 0;
      let failedCount = 0;
      const total = allMessages.length;

      // 并发删除，但限制并发数避免API压力过大
      const BATCH_SIZE = 5;
      for (let i = 0; i < allMessages.length; i += BATCH_SIZE) {
        const batch = allMessages.slice(i, i + BATCH_SIZE);
        
        const deletePromises = batch.map(async (message) => {
          try {
            await messageApi.deleteMessage(groupId, message.message_id);
            deletedCount++;
          } catch (error) {
            failedCount++;
            console.error(`删除消息 ${message.message_id} 失败:`, error);
          }
        });

        await Promise.all(deletePromises);

        // 报告进度
        if (onProgress) {
          onProgress({
            current: deletedCount + failedCount,
            total: total
          });
        }
      }

      return {
        success: deletedCount > 0,
        deletedCount,
        failedCount,
        message: failedCount === 0 
          ? `成功删除 ${deletedCount} 条消息` 
          : `删除完成：成功 ${deletedCount} 条，失败 ${failedCount} 条`
      };

    } catch (error: any) {
      throw new Error(`清空群组消息失败: ${error.message}`);
    }
  },

  // 搜索消息
  searchMessages: (
    groupId: number,
    searchRequest: MessageSearchRequest,
    skip: number = 0,
    limit: number = 100
  ): Promise<PaginatedResponse<TelegramMessage>> => {
    return api.post(`/telegram/groups/${groupId}/messages/search`, searchRequest, {
      params: { skip, limit }
    });
  },
};

// 规则相关API
export const ruleApi = {
  // 获取规则列表
  getRules: (skip: number = 0, limit: number = 100): Promise<FilterRule[]> => {
    return api.get('/rule', { params: { skip, limit } });
  },

  // 获取群组规则
  getGroupRules: (groupId: number): Promise<FilterRule[]> => {
    return api.get(`/rule/group/${groupId}`);
  },

  // 创建规则
  createRule: (rule: Partial<FilterRule>): Promise<FilterRule> => {
    return api.post('/rule', rule);
  },

  // 更新规则
  updateRule: (ruleId: number, rule: Partial<FilterRule>): Promise<FilterRule> => {
    return api.put(`/rule/${ruleId}`, rule);
  },

  // 删除规则
  deleteRule: (ruleId: number): Promise<{ message: string }> => {
    return api.delete(`/rule/${ruleId}`);
  },

  // 获取规则详情
  getRule: (ruleId: number): Promise<FilterRule> => {
    return api.get(`/rule/${ruleId}`);
  },

  // 测试规则
  testRule: (rule: Partial<FilterRule>): Promise<{
    matched_messages: number;
    sample_messages: TelegramMessage[];
  }> => {
    return api.post('/rule/test', rule);
  },
};

// 下载任务相关API
export const downloadApi = {
  // 获取下载任务列表
  getDownloadTasks: (skip: number = 0, limit: number = 100): Promise<PaginatedResponse<DownloadTask>> => {
    return api.get('/download', { params: { skip, limit } });
  },

  // 创建下载任务
  createDownloadTask: (task: {
    name: string;
    group_id: number;
    rule_id: number;
    download_path: string;
    start_immediately?: boolean;
  }): Promise<DownloadTask> => {
    return api.post('/download', task);
  },

  // 获取下载任务详情
  getDownloadTask: (taskId: number): Promise<DownloadTask> => {
    return api.get(`/download/${taskId}`);
  },

  // 暂停下载任务
  pauseDownloadTask: (taskId: number): Promise<DownloadTask> => {
    return api.post(`/download/${taskId}/pause`);
  },

  // 恢复下载任务
  resumeDownloadTask: (taskId: number): Promise<DownloadTask> => {
    return api.post(`/download/${taskId}/resume`);
  },

  // 停止下载任务
  stopDownloadTask: (taskId: number): Promise<DownloadTask> => {
    return api.post(`/download/${taskId}/stop`);
  },

  // 删除下载任务
  deleteDownloadTask: (taskId: number): Promise<{ message: string }> => {
    return api.delete(`/download/${taskId}`);
  },

  // 预估下载数量
  estimateDownloadCount: (groupId: number, ruleId: number): Promise<number> => {
    return api.post('/download/estimate', { group_id: groupId, rule_id: ruleId });
  },
};

// 媒体下载相关API
export const mediaApi = {
  // 下载媒体文件
  downloadMedia: (messageId: number, force: boolean = false): Promise<{
    status: string;
    message: string;
    file_path?: string;
    file_size?: number;
    download_url?: string;
    message_id?: number;
    media_type?: string;
    estimated_size?: number;
  }> => {
    return api.post(`/media/start-download/${messageId}`, {}, { params: { force } });
  },

  // 获取媒体下载状态
  getDownloadStatus: (messageId: number): Promise<{
    status: string;
    message: string;
    file_path?: string;
    file_size?: number;
    download_url?: string;
    media_type?: string;
    file_id?: string;
    error?: string;
    // 新增进度相关字段
    progress?: number;
    downloaded_size?: number;
    total_size?: number;
    download_speed?: number;
    estimated_time_remaining?: number;
    download_started_at?: string;
  }> => {
    return api.get(`/media/download-status/${messageId}`);
  },

  // 取消下载
  cancelDownload: (messageId: number): Promise<{
    status: string;
    message: string;
    message_id?: number;
  }> => {
    return api.post(`/media/cancel-download/${messageId}`);
  },

  // 删除本地媒体文件
  deleteMediaFile: (messageId: number): Promise<{
    status: string;
    message: string;
    message_id?: number;
  }> => {
    return api.delete(`/media/media/${messageId}`);
  },
};

// 群组管理相关API
export const groupApi = {
  // 同步群组信息
  syncGroup: (groupId: number): Promise<TelegramGroup> => {
    return api.post(`/telegram/groups/${groupId}/sync-info`);
  },

  // 更新群组设置
  updateGroup: (groupId: number, data: Partial<TelegramGroup>): Promise<TelegramGroup> => {
    return api.put(`/telegram/groups/${groupId}`, data);
  },
};

// 日志管理相关API
export const logApi = {
  // 获取日志列表
  getLogs: (params?: {
    level?: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
    search?: string;
    start_time?: string;
    end_time?: string;
    task_id?: number;
    skip?: number;
    limit?: number;
  }): Promise<{
    logs: LogEntry[];
    total: number;
    page: number;
    size: number;
  }> => {
    return api.get('/logs', { params });
  },

  // 获取任务日志
  getTaskLogs: (params?: {
    level?: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
    search?: string;
    start_time?: string;
    end_time?: string;
    task_id?: number;
    skip?: number;
    limit?: number;
  }): Promise<LogEntry[]> => {
    return api.get('/logs/task', { params });
  },

  // 获取系统日志
  getSystemLogs: (params?: {
    level?: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
    search?: string;
    start_time?: string;
    end_time?: string;
    skip?: number;
    limit?: number;
  }): Promise<LogEntry[]> => {
    return api.get('/logs/system', { params });
  },

  // 清除日志
  clearLogs: (type: 'task' | 'system' | 'all'): Promise<{
    success: boolean;
    message: string;
    cleared_count?: number;
  }> => {
    return api.delete(`/logs/${type}`);
  },

  // 导出日志
  exportLogs: (params: {
    type: 'task' | 'system' | 'all';
    level?: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
    search?: string;
    start_time?: string;
    end_time?: string;
    format: 'json' | 'csv' | 'txt';
  }): Promise<{
    download_url: string;
    filename: string;
    size: number;
  }> => {
    return api.post('/logs/export', params);
  },

  // 获取日志统计
  getLogStats: (params?: {
    start_time?: string;
    end_time?: string;
  }): Promise<{
    total_logs: number;
    error_count: number;
    warning_count: number;
    info_count: number;
    debug_count: number;
    task_log_count: number;
    system_log_count: number;
  }> => {
    return api.get('/logs/stats', { params });
  },

  // 获取最新日志
  getRecentLogs: (limit: number = 100): Promise<LogEntry[]> => {
    return api.get('/logs/recent', { params: { limit } });
  },

  // 批量删除日志
  deleteLogs: (logIds: number[]): Promise<{
    success: boolean;
    message: string;
    deleted_count: number;
  }> => {
    return api.delete('/logs/batch', { data: { log_ids: logIds } });
  },
};

// 导出默认API实例
export default api;