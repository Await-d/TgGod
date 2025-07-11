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
  PaginatedResponse
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

  // 添加群组
  addGroup: (username: string): Promise<TelegramGroup> => {
    return api.post('/telegram/groups', { username });
  },

  // 获取群组信息
  getGroup: (groupId: number): Promise<TelegramGroup> => {
    return api.get(`/telegram/groups/${groupId}`);
  },

  // 更新群组
  updateGroup: (groupId: number, data: Partial<TelegramGroup>): Promise<TelegramGroup> => {
    return api.put(`/telegram/groups/${groupId}`, data);
  },

  // 同步群组信息
  syncGroup: (groupId: number): Promise<TelegramGroup> => {
    return api.post(`/telegram/groups/${groupId}/sync-info`);
  },

  // 删除群组
  deleteGroup: (groupId: number): Promise<{ message: string }> => {
    return api.delete(`/telegram/groups/${groupId}`);
  },


  // 同步群组消息
  syncGroupMessages: (groupId: number, limit: number = 100): Promise<{ message: string }> => {
    return api.post(`/telegram/groups/${groupId}/sync`, { limit });
  },

  // 按月同步群组消息
  syncGroupMessagesMonthly: (groupId: number, months: Array<{year: number, month: number}>): Promise<any> => {
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
    limit: number = 50
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

// 导出默认API实例
export default api;