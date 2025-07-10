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
  FilterRule
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
  updateGroup: (groupId: number, isActive: boolean): Promise<TelegramGroup> => {
    return api.put(`/telegram/groups/${groupId}`, { is_active: isActive });
  },

  // 删除群组
  deleteGroup: (groupId: number): Promise<{ message: string }> => {
    return api.delete(`/telegram/groups/${groupId}`);
  },

  // 获取群组统计
  getGroupStats: (groupId: number): Promise<GroupStats> => {
    return api.get(`/telegram/groups/${groupId}/stats`);
  },

  // 同步群组消息
  syncGroupMessages: (groupId: number, limit: number = 100): Promise<{ message: string }> => {
    return api.post(`/telegram/groups/${groupId}/sync`, { limit });
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

  // 获取消息详情
  getMessageDetail: (groupId: number, messageId: number): Promise<TelegramMessage> => {
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
  ): Promise<TelegramMessage[]> => {
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

// 导出默认API实例
export default api;