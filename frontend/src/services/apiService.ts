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
  FilterRule,
  DownloadTask,
  PaginatedResponse,
  LogEntry,
  ServiceHealthResponse,
  ServiceHealthSummaryResponse,
  ServiceStatusSnapshotResponse,
  ServiceHealthCheckResponse,
  GroupMember
} from '../types';

// 创建axios实例
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 响应拦截器，用于统一错误处理
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // 处理网络错误或超时
    if (!error.response) {
      console.error('网络连接错误:', error.message);
      return Promise.reject(new Error('无法连接到服务器，请检查网络连接'));
    }

    // 处理服务器错误
    const message = error.response?.data?.detail || error.message || '未知错误';
    console.error('API错误:', message);
    return Promise.reject(new Error(message));
  }
);

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

    let maxIterations = 100; // 最大迭代次数，防止死循环
    while (maxIterations > 0) {
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
      maxIterations--;
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

  getGroupMembers: (groupId: number): Promise<{ members: GroupMember[]; total: number }> => {
    return api.get(`/telegram/groups/${groupId}/members`);
  },


  // 同步群组消息
  syncGroupMessages: (groupId: number, limit: number = 100): Promise<{ message: string }> => {
    return api.post(`/telegram/groups/${groupId}/sync`, { limit });
  },

  // 按月同步群组消息（异步任务，不等待完成）
  syncGroupMessagesMonthly: (groupId: number, months: Array<{ year: number, month: number }>): Promise<{ success: boolean, message: string, task_id?: string }> => {
    return api.post(`/telegram/groups/${groupId}/sync-monthly`, { months });
  },

  // 获取默认同步月份
  getDefaultSyncMonths: (groupId: number, count: number = 3): Promise<{ months: Array<{ year: number, month: number }> }> => {
    return api.get(`/telegram/groups/${groupId}/default-sync-months`, { params: { count } });
  },

  // 批量按月同步所有群组
  syncAllGroupsMonthly: (months: Array<{ year: number, month: number }>): Promise<any> => {
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

  // 获取群组未读消息数量
  getGroupUnreadCount: (groupId: number, lastReadTime?: string): Promise<{
    group_id: number;
    group_title: string;
    unread_count: number;
    cutoff_time: string;
    latest_message?: {
      id: number;
      message_id: number;
      text: string;
      sender_name: string;
      date: string;
      media_type?: string;
    };
    latest_unread_message?: {
      id: number;
      message_id: number;
      text: string;
      sender_name: string;
      date: string;
      media_type?: string;
    };
  }> => {
    const params = lastReadTime ? { last_read_time: lastReadTime } : {};
    return api.get(`/telegram/groups/${groupId}/unread`, { params });
  },

  // 获取所有群组未读消息摘要
  getAllGroupsUnreadSummary: (lastReadTimes?: Record<string, string>): Promise<{
    total_unread: number;
    groups_count: number;
    groups_with_unread: number;
    groups: Array<{
      group_id: number;
      group_title: string;
      group_username?: string;
      unread_count: number;
      cutoff_time?: string;
      latest_message_time?: string;
      latest_message_text?: string;
    }>;
  }> => {
    const params = lastReadTimes ? { last_read_times: JSON.stringify(lastReadTimes) } : {};
    return api.get('/telegram/groups/unread-summary', { params });
  },
};

// 消息相关API
export const messageApi = {
  // 获取群组消息 - 支持完整的筛选参数
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
      is_pinned?: boolean;
      start_date?: string;
      end_date?: string;
    } = {}
  ): Promise<TelegramMessage[]> => {
    // 过滤掉undefined值，避免发送不必要的参数
    const cleanParams = Object.fromEntries(
      Object.entries(params).filter(([_, value]) => value !== undefined)
    );


    return api.get(`/telegram/groups/${groupId}/messages`, { params: cleanParams });
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
  ): Promise<{ data: TelegramMessage[], pagination: { current: number, pageSize: number, total: number } }> => {
    // 过滤掉undefined值，避免发送不必要的参数
    const cleanParams = Object.fromEntries(
      Object.entries(params).filter(([_, value]) => value !== undefined)
    );

    return api.get(`/telegram/groups/${groupId}/messages/paginated`, { params: cleanParams });
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

  sendMediaMessage: (
    groupId: number,
    payload: {
      files: File[];
      text?: string;
      reply_to_message_id?: number;
    }
  ): Promise<{
    success: boolean;
    message_ids: number[];
    message: string;
  }> => {
    const formData = new FormData();
    payload.files.forEach((file) => {
      formData.append('files', file);
    });

    if (payload.text) {
      formData.append('text', payload.text);
    }

    if (payload.reply_to_message_id !== undefined) {
      formData.append('reply_to_message_id', String(payload.reply_to_message_id));
    }

    return api.post(`/telegram/groups/${groupId}/send-media`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
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
            return { success: true };
          } catch (error) {
            console.error(`删除消息 ${message.message_id} 失败:`, error);
            return { success: false };
          }
        });

        const results = await Promise.all(deletePromises);
        const batchDeleted = results.filter(r => r.success).length;
        const batchFailed = results.filter(r => !r.success).length;

        deletedCount += batchDeleted;
        failedCount += batchFailed;


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
    return api.get('/rules', { params: { skip, limit } });
  },

  // 获取群组规则 - 已移除，规则不再直接关联群组
  // getGroupRules: (groupId: number): Promise<FilterRule[]> => {
  //   return api.get('/rules', { params: { group_id: groupId } });
  // },

  // 创建规则
  createRule: (rule: Partial<FilterRule>): Promise<FilterRule> => {
    return api.post('/rules', rule);
  },

  // 更新规则
  updateRule: (ruleId: number, rule: Partial<FilterRule>): Promise<FilterRule> => {
    return api.put(`/rules/${ruleId}`, rule);
  },

  // 删除规则
  deleteRule: (ruleId: number): Promise<{ message: string }> => {
    return api.delete(`/rules/${ruleId}`);
  },

  // 获取规则详情
  getRule: (ruleId: number): Promise<FilterRule> => {
    return api.get(`/rules/${ruleId}`);
  },

  // 测试规则
  testRule: (ruleId: number): Promise<{
    matched_messages: number;
    sample_messages: TelegramMessage[];
  }> => {
    return api.post(`/rules/${ruleId}/test`);
  },
};

// 任务管理相关API
export const taskApi = {
  // 获取任务列表
  getTasks: (params?: {
    group_id?: number;
    status?: string;
    skip?: number;
    limit?: number;
  }): Promise<DownloadTask[]> => {
    return api.get('/tasks', { params });
  },

  // 创建任务
  createTask: (task: {
    name: string;
    group_id: number;
    rule_ids: number[];
    download_path: string;
    date_from?: string;
    date_to?: string;
  }): Promise<DownloadTask> => {
    return api.post('/tasks', task);
  },

  // 获取任务详情
  getTask: (taskId: number): Promise<DownloadTask> => {
    return api.get(`/tasks/${taskId}`);
  },

  // 启动任务 - 带重试机制
  startTask: async (taskId: number): Promise<{ message: string }> => {
    try {
      const response = await api.post(`/tasks/${taskId}/start`);
      return response.data;
    } catch (error: any) {
      // 如果任务执行服务未初始化，提供友好的错误消息
      if (error.message.includes('未在运行') || error.message.includes('服务不可用')) {
        throw new Error('任务执行服务暂时不可用，请稍后重试');
      }
      throw error;
    }
  },

  // 暂停任务 - 带重试机制
  pauseTask: async (taskId: number): Promise<{ message: string }> => {
    try {
      const response = await api.post(`/tasks/${taskId}/pause`);
      return response.data;
    } catch (error: any) {
      if (error.message.includes('未在运行') || error.message.includes('服务不可用')) {
        throw new Error('任务执行服务暂时不可用，请稍后重试');
      }
      throw error;
    }
  },

  // 停止任务 - 带重试机制
  stopTask: async (taskId: number): Promise<{ message: string }> => {
    try {
      const response = await api.post(`/tasks/${taskId}/stop`);
      return response.data;
    } catch (error: any) {
      if (error.message.includes('未在运行') || error.message.includes('服务不可用')) {
        throw new Error('任务执行服务暂时不可用，请稍后重试');
      }
      throw error;
    }
  },

  // 更新任务
  updateTask: (taskId: number, task: {
    name?: string;
    group_id?: number;
    rule_ids?: number[];
    download_path?: string;
    date_from?: string;
    date_to?: string;
    task_type?: string;
    schedule_type?: string;
    schedule_config?: any;
    max_runs?: number;
  }): Promise<DownloadTask> => {
    return api.put(`/tasks/${taskId}`, task);
  },

  // 删除任务
  deleteTask: (taskId: number): Promise<{ message: string }> => {
    return api.delete(`/tasks/${taskId}`);
  },

  // 获取任务统计
  getTaskStats: (): Promise<{
    total: number;
    running: number;
    completed: number;
    failed: number;
    pending: number;
  }> => {
    return api.get('/tasks/stats');
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

// 服务健康检查相关API
export const serviceHealthApi = {
  // 获取所有服务的健康状态
  getServicesHealth: (): Promise<ServiceHealthResponse> => {
    return api.get('/health/services');
  },

  // 获取健康摘要
  getHealthSummary: (): Promise<ServiceHealthSummaryResponse> => {
    return api.get('/health/summary');
  },

  // 获取当前缓存状态
  getCurrentStatus: (): Promise<ServiceStatusSnapshotResponse> => {
    return api.get('/health/status');
  },

  // 强制执行一次检查
  forceHealthCheck: (): Promise<ServiceHealthCheckResponse> => {
    return api.post('/health/check');
  }
};

export const realtimeControlApi = {
  recoverService: (serviceName: string): Promise<{
    success: boolean;
    data: {
      service_name: string;
      recovery_started: boolean;
    };
    message: string;
  }> => {
    return api.post('/realtime/services/recover', null, {
      params: { service_name: serviceName }
    });
  },

  setMaintenanceMode: (payload: {
    enabled: boolean;
    message?: string;
    eta?: string;
  }): Promise<{
    success: boolean;
    data: {
      enabled: boolean;
      message: string;
      eta?: string;
    };
    message: string;
  }> => {
    return api.post('/realtime/maintenance/mode', payload);
  }
};

// 媒体下载相关API
export const mediaApi = {
  // 下载媒体文件
  downloadMedia: (
    groupId: number,
    messageId: number,
    options?: {
      force?: boolean;
      onProgress?: (progress: number) => void;
    }
  ): Promise<{
    success: boolean;
    status: string;
    message: string;
    file_path?: string;
    file_size?: number;
    download_url?: string;
    message_id?: number;
    media_type?: string;
    estimated_size?: number;
  }> => {
    const { force = false, onProgress } = options || {};

    return new Promise(async (resolve, reject) => {
      try {
        // 开始下载
        const startResponse = await api.post(`/media/start-download/${messageId}`, {}, {
          params: { force }
        });

        if (startResponse.status !== 200) {
          resolve({
            success: false,
            status: startResponse.status.toString(),
            message: startResponse.statusText,
            file_path: startResponse.data.file_path,
            file_size: startResponse.data.file_size,
            download_url: startResponse.data.download_url,
            message_id: startResponse.data.message_id,
            media_type: startResponse.data.media_type,
            estimated_size: startResponse.data.estimated_size
          });
          return;
        }

        // 如果有进度回调，轮询下载状态
        if (onProgress) {
          const pollInterval = setInterval(async () => {
            try {
              const statusResponse = await api.get(`/media/download-status/${messageId}`);

              if (statusResponse.data.progress !== undefined) {
                onProgress(statusResponse.data.progress);
              }

              // 下载完成或失败时停止轮询
              if (statusResponse.data.status === 'completed' || statusResponse.data.status === 'failed') {
                clearInterval(pollInterval);
                resolve({
                  success: statusResponse.data.status === 'completed',
                  ...statusResponse.data
                });
              }
            } catch (error) {
              clearInterval(pollInterval);
              reject(error);
            }
          }, 500); // 每500ms检查一次进度

          // 设置超时
          setTimeout(() => {
            clearInterval(pollInterval);
            resolve({
              success: false,
              status: 'timeout',
              message: '下载超时'
            });
          }, 60000); // 60秒超时
        } else {
          resolve({
            success: true,
            ...startResponse.data
          });
        }
      } catch (error) {
        reject(error);
      }
    });
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

  // 🔥 新增：获取并发下载统计
  getDownloadStats: (): Promise<{
    status: string;
    stats: {
      total_active_downloads: number;
      user_active_downloads: Record<string, number>;
      max_concurrent_downloads: number;
      user_concurrent_limit: number;
      started_at: string | null;
      current_downloads: number[];
      available_slots: number;
    };
  }> => {
    return api.get('/media/download-stats');
  },

  // 🔥 新增：取消并发下载
  cancelConcurrentDownload: (messageId: number): Promise<{
    status: string;
    message: string;
    message_id?: number;
  }> => {
    return api.post(`/media/cancel-concurrent-download/${messageId}`);
  },

  // 🔥 新增：批量并发下载
  batchConcurrentDownload: (messageIds: number[], force: boolean = false): Promise<{
    status: string;
    message: string;
    total_requested: number;
    successfully_started: number;
    already_downloading: number;
    failed_to_start: number;
    started_downloads: number[];
    already_downloading_list: number[];
    failed_downloads: Array<{ message_id: number; error: string }>;
    current_concurrent_downloads: number;
  }> => {
    return api.post('/media/batch-concurrent-download', {
      message_ids: messageIds,
      force
    });
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
  getLogs: async (params?: {
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
    const response = await api.get('/logs/recent', { 
      params: {
        limit: params?.limit || 100,
        log_type: 'all',
        ...params
      }
    });
    // 转换为期望格式
    const data = response.data;
    const logs = Array.isArray(data) ? data.map((log: any) => ({
      id: log.id,
      level: log.level,
      message: log.message,
      created_at: log.created_at,
      timestamp: log.created_at, // timestamp与created_at相同
      task_id: log.task_id,
      details: log.details
    })) : [];
    return {
      logs,
      total: logs.length,
      page: Math.floor((params?.skip || 0) / (params?.limit || 100)) + 1,
      size: params?.limit || 100
    };
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
  clearLogs: (type: 'task' | 'system' | 'all', task_id?: number): Promise<{
    success: boolean;
    message: string;
    cleared_count?: number;
  }> => {
    const params = task_id ? { task_id } : {};
    return api.delete(`/logs/${type}`, { params });
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
  getLogStats: async (params?: {
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
    try {
      const response = await api.get('/logs/stats', { params });
      const data = response.data;
      
      // 安全的数据提取，提供默认值
      return {
        total_logs: data?.total_logs || 0,
        error_count: data?.total_errors || 0,
        warning_count: data?.total_warnings || 0,
        info_count: data?.total_info || 0,  
        debug_count: data?.total_debug || 0,
        task_log_count: data?.task_logs?.total || 0,
        system_log_count: data?.system_logs?.total || 0
      };
    } catch (error) {
      console.error('获取日志统计失败:', error);
      // 返回默认值避免前端错误
      return {
        total_logs: 0,
        error_count: 0,
        warning_count: 0,
        info_count: 0,
        debug_count: 0,
        task_log_count: 0,
        system_log_count: 0
      };
    }
  },

  // 获取最新日志
  getRecentLogs: (limit: number = 100, log_type: string = 'all'): Promise<LogEntry[]> => {
    return api.get('/logs/recent', { params: { limit, log_type } });
  },

  // 添加系统日志
  addSystemLog: (data: {
    level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
    message: string;
    module?: string;
    function?: string;
    details?: any;
  }): Promise<{
    success: boolean;
    message: string;
    log_id: number;
  }> => {
    return api.post('/logs/system', data);
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

// 仪表盘相关API
export const dashboardApi = {
  // 获取仪表盘概览数据
  getOverview: (forceRefresh: boolean = false): Promise<{
    basic_stats: {
      total_groups: number;
      active_groups: number;
      total_messages: number;
      media_messages: number;
      text_messages: number;
    };
    download_stats: {
      downloaded_media: number;
      total_media_size: number;
      downloading_tasks: number;
      download_completion_rate: number;
    };
    today_stats: {
      new_messages: number;
      new_downloads: number;
    };
    media_distribution: Record<string, number>;
    last_updated: string;
  }> => {
    return api.get('/dashboard/overview', { params: { force_refresh: forceRefresh } });
  },

  // 获取群组汇总信息
  getGroupsSummary: (limit: number = 10, forceRefresh: boolean = false): Promise<{
    groups: Array<{
      group_id: number;
      title: string;
      username?: string;
      member_count: number;
      is_active: boolean;
      message_count: number;
      media_count: number;
      downloaded_count: number;
      download_rate: number;
      last_message_date?: string;
    }>;
    total_groups: number;
    last_updated: string;
  }> => {
    return api.get('/dashboard/groups-summary', {
      params: { limit, force_refresh: forceRefresh }
    });
  },

  // 获取最近活动
  getRecentActivity: (hours: number = 24, limit: number = 20, forceRefresh: boolean = false): Promise<{
    recent_messages: Array<{
      id: number;
      group_id: number;
      group_title: string;
      message_id: number;
      sender_name?: string;
      text?: string;
      media_type?: string;
      date: string;
      type: 'message';
    }>;
    recent_downloads: Array<{
      id: number;
      group_id: number;
      group_title: string;
      message_id: number;
      filename?: string;
      media_type?: string;
      size?: number;
      date: string;
      type: 'download';
    }>;
    time_range_hours: number;
    last_updated: string;
  }> => {
    return api.get('/dashboard/recent-activity', {
      params: { hours, limit, force_refresh: forceRefresh }
    });
  },

  // 获取下载统计信息
  getDownloadStatistics: (days: number = 7, forceRefresh: boolean = false): Promise<{
    daily_downloads: Array<{
      date: string;
      count: number;
      total_size: number;
    }>;
    downloads_by_type: Record<string, {
      count: number;
      total_size: number;
    }>;
    average_download_speed: number;
    time_range_days: number;
    last_updated: string;
  }> => {
    return api.get('/dashboard/download-stats', {
      params: { days, force_refresh: forceRefresh }
    });
  },

  // 获取系统信息
  getSystemInfo: (forceRefresh: boolean = false): Promise<{
    database: {
      total_groups: number;
      total_messages: number;
      media_files: number;
    };
    disk_usage?: {
      total: number;
      used: number;
      free: number;
      usage_percent: number;
    };
    memory: {
      total: number;
      available: number;
      used: number;
      usage_percent: number;
    };
    cpu_percent: number;
    media_root: string;
    last_updated: string;
  }> => {
    return api.get('/dashboard/system-info', {
      params: { force_refresh: forceRefresh }
    });
  },

  // 清除仪表盘缓存
  clearCache: (): Promise<{
    success: boolean;
    message: string;
    timestamp: string;
  }> => {
    return api.delete('/dashboard/cache');
  }
};

// 下载历史相关API
export const downloadHistoryApi = {
  // 获取下载记录列表
  getDownloadRecords: (params?: {
    page?: number;
    page_size?: number;
    task_id?: number;
    group_id?: number;
    file_type?: string;
    status?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
  }): Promise<{
    records: Array<{
      id: number;
      task_id: number;
      task_name: string;
      group_name: string;
      file_name: string;
      local_file_path: string;
      file_size: number;
      file_type: string;
      message_id: number;
      sender_id: number;
      sender_name: string;
      message_date: string;
      message_text: string;
      download_status: string;
      download_progress: number;
      error_message?: string;
      download_started_at: string;
      download_completed_at: string;
    }>;
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }> => {
    return api.get('/download-history/records', { params });
  },

  // 获取单个下载记录详情
  getDownloadRecord: (recordId: number): Promise<{
    id: number;
    task_id: number;
    task_name: string;
    group_name: string;
    file_name: string;
    local_file_path: string;
    file_size: number;
    file_type: string;
    message_id: number;
    sender_id: number;
    sender_name: string;
    message_date: string;
    message_text: string;
    download_status: string;
    download_progress: number;
    error_message?: string;
    download_started_at: string;
    download_completed_at: string;
  }> => {
    return api.get(`/download-history/records/${recordId}`);
  },

  // 获取下载历史统计信息
  getDownloadStats: (days: number = 30): Promise<{
    total_downloads: number;
    successful_downloads: number;
    failed_downloads: number;
    success_rate: number;
    total_file_size: number;
    file_types: Record<string, number>;
    top_tasks: Array<{ task_name: string; download_count: number }>;
    period_days: number;
  }> => {
    return api.get('/download-history/stats', { params: { days } });
  },

  // 删除下载记录
  deleteDownloadRecord: (recordId: number): Promise<{
    message: string;
    record_id: number;
  }> => {
    return api.delete(`/download-history/records/${recordId}`);
  },

  // 批量删除下载记录
  batchDeleteRecords: (recordIds: number[]): Promise<{
    message: string;
    deleted_count: number;
    requested_count: number;
  }> => {
    return api.post('/download-history/records/batch-delete', recordIds);
  },

  // 获取任务的下载记录
  getTaskDownloadRecords: (taskId: number, params?: {
    page?: number;
    page_size?: number;
  }): Promise<{
    records: Array<{
      id: number;
      task_id: number;
      task_name: string;
      group_name: string;
      file_name: string;
      local_file_path: string;
      file_size: number;
      file_type: string;
      message_id: number;
      sender_id: number;
      sender_name: string;
      message_date: string;
      message_text: string;
      download_status: string;
      download_progress: number;
      error_message?: string;
      download_started_at: string;
      download_completed_at: string;
    }>;
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }> => {
    return api.get(`/download-history/tasks/${taskId}/records`, { params });
  },

  // 创建下载记录（供下载服务调用）
  createDownloadRecord: (recordData: {
    task_id: number;
    file_name: string;
    local_file_path: string;
    file_size?: number;
    file_type?: string;
    message_id: number;
    sender_id?: number;
    sender_name?: string;
    message_date?: string;
    message_text?: string;
    download_status?: string;
    download_progress?: number;
    error_message?: string;
    download_started_at?: string;
    download_completed_at?: string;
  }): Promise<{
    id: number;
    task_id: number;
    task_name: string;
    group_name: string;
    file_name: string;
    local_file_path: string;
    file_size: number;
    file_type: string;
    message_id: number;
    sender_id: number;
    sender_name: string;
    message_date: string;
    message_text: string;
    download_status: string;
    download_progress: number;
    error_message?: string;
    download_started_at: string;
    download_completed_at: string;
  }> => {
    return api.post('/download-history/records', recordData);
  },
};

// 导出默认API实例
export default api;
