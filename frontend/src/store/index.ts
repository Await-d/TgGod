import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { TelegramGroup, TelegramMessage, FilterRule, DownloadTask, LogEntry, Statistics, User } from '../types';

// 用户认证状态接口
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setIsAuthenticated: (isAuthenticated: boolean) => void;
  setIsLoading: (isLoading: boolean) => void;
  initializeAuth: () => void;
  logout: () => void;
}

// 全局状态接口
interface GlobalState {
  // 加载状态
  loading: boolean;
  setLoading: (loading: boolean) => void;

  // 错误状态
  error: string | null;
  setError: (error: string | null) => void;

  // 连接状态
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
  setConnectionStatus: (status: 'connected' | 'disconnected' | 'connecting') => void;

  // 清除状态
  clearError: () => void;
  reset: () => void;
}

// Telegram状态接口
interface TelegramState {
  groups: TelegramGroup[];
  messages: TelegramMessage[];
  selectedGroup: TelegramGroup | null;
  
  setGroups: (groups: TelegramGroup[]) => void;
  setMessages: (messages: TelegramMessage[]) => void;
  setSelectedGroup: (group: TelegramGroup | null) => void;
  addGroup: (group: TelegramGroup) => void;
  updateGroup: (id: number, updates: Partial<TelegramGroup>) => void;
  removeGroup: (id: number) => void;
  addMessage: (message: TelegramMessage) => void;
  updateMessage: (id: number, updates: Partial<TelegramMessage>) => void;
  removeMessage: (id: number) => void;
  // 新增方法
  mergeMessages: (newMessages: TelegramMessage[]) => void;
  prependMessages: (newMessages: TelegramMessage[]) => void;
}

// 规则状态接口
interface RuleState {
  rules: FilterRule[];
  selectedRule: FilterRule | null;
  
  setRules: (rules: FilterRule[]) => void;
  setSelectedRule: (rule: FilterRule | null) => void;
  addRule: (rule: FilterRule) => void;
  updateRule: (id: number, updates: Partial<FilterRule>) => void;
  removeRule: (id: number) => void;
}

// 下载任务状态接口
interface TaskState {
  tasks: DownloadTask[];
  selectedTask: DownloadTask | null;
  
  setTasks: (tasks: DownloadTask[]) => void;
  setSelectedTask: (task: DownloadTask | null) => void;
  addTask: (task: DownloadTask) => void;
  updateTask: (id: number, updates: Partial<DownloadTask>) => void;
  removeTask: (id: number) => void;
}

// 日志状态接口
interface LogState {
  logs: LogEntry[];
  maxLogs: number;
  
  setLogs: (logs: LogEntry[]) => void;
  addLog: (log: LogEntry) => void;
  clearLogs: () => void;
  setMaxLogs: (maxLogs: number) => void;
}

// 统计数据状态接口
interface StatisticsState {
  statistics: Statistics | null;
  setStatistics: (statistics: Statistics) => void;
}

// 创建用户认证状态store（持久化）
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      
      setUser: (user) => set({ user }),
      setToken: (token) => set({ token, isAuthenticated: !!token }),
      setIsAuthenticated: (isAuthenticated) => set({ isAuthenticated }),
      setIsLoading: (isLoading) => set({ isLoading }),
      
      initializeAuth: () => {
        const { token } = get();
        if (token) {
          set({ isAuthenticated: true });
        }
      },
      
      logout: () => {
        set({ 
          user: null, 
          token: null, 
          isAuthenticated: false,
          isLoading: false
        });
        // 清除localStorage
        localStorage.removeItem('auth-storage');
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        user: state.user, 
        token: state.token, 
        isAuthenticated: state.isAuthenticated 
      }),
    }
  )
);

// 创建全局状态store
export const useGlobalStore = create<GlobalState>((set) => ({
  loading: false,
  error: null,
  connectionStatus: 'disconnected',
  
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
  clearError: () => set({ error: null }),
  reset: () => set({ loading: false, error: null, connectionStatus: 'disconnected' }),
}));

// 创建Telegram状态store
export const useTelegramStore = create<TelegramState>((set) => ({
  groups: [],
  messages: [],
  selectedGroup: null,
  
  setGroups: (groups) => set({ groups }),
  setMessages: (messages) => set({ messages }),
  
  // 新增：智能合并消息数组，去重并保持顺序
  mergeMessages: (newMessages) => set((state) => {
    if (!newMessages || newMessages.length === 0) return state;
    
    // 创建现有消息的Map，以message_id为key
    const existingMessagesMap = new Map();
    state.messages.forEach(msg => {
      existingMessagesMap.set(msg.message_id, msg);
    });
    
    // 合并新消息，如果存在则更新，不存在则添加
    newMessages.forEach(newMsg => {
      existingMessagesMap.set(newMsg.message_id, newMsg);
    });
    
    // 将Map转换回数组，按date排序
    const mergedMessages = Array.from(existingMessagesMap.values())
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
    
    return { messages: mergedMessages };
  }),
  
  // 新增：批量添加消息到顶部（用于历史消息加载）
  prependMessages: (newMessages) => set((state) => {
    if (!newMessages || newMessages.length === 0) return state;
    
    // 创建现有消息ID的Set用于快速查找
    const existingIds = new Set(state.messages.map(m => m.message_id));
    
    // 过滤出不重复的新消息
    const uniqueNewMessages = newMessages.filter(msg => !existingIds.has(msg.message_id));
    
    // 将新消息添加到现有消息前面
    const combinedMessages = [...uniqueNewMessages, ...state.messages];
    
    // 按日期排序确保消息顺序正确
    const sortedMessages = combinedMessages.sort((a, b) => 
      new Date(a.date).getTime() - new Date(b.date).getTime()
    );
    
    return { messages: sortedMessages };
  }),
  setSelectedGroup: (selectedGroup) => set({ selectedGroup }),
  
  addGroup: (group) => set((state) => ({ 
    groups: [...state.groups, group] 
  })),
  
  updateGroup: (id, updates) => set((state) => ({
    groups: state.groups.map(group => 
      group.id === id ? { ...group, ...updates } : group
    )
  })),
  
  removeGroup: (id) => set((state) => ({
    groups: state.groups.filter(group => group.id !== id)
  })),
  
  addMessage: (message) => set((state) => {
    // 检查消息是否已存在（基于message_id去重）
    const existingIndex = state.messages.findIndex(m => m.message_id === message.message_id);
    if (existingIndex !== -1) {
      // 如果消息已存在，更新它
      const updatedMessages = [...state.messages];
      updatedMessages[existingIndex] = { ...updatedMessages[existingIndex], ...message };
      return { messages: updatedMessages };
    }
    // 如果消息不存在，添加到末尾
    return { messages: [...state.messages, message] };
  }),
  
  updateMessage: (id, updates) => set((state) => ({
    messages: state.messages.map(message => 
      message.id === id ? { ...message, ...updates } : message
    )
  })),
  
  removeMessage: (id) => set((state) => ({
    messages: state.messages.filter(message => message.id !== id)
  })),
}));

// Telegram 用户状态接口
interface TelegramUserState {
  currentTelegramUser: {
    id: number;
    username: string | null;
    first_name: string | null;
    last_name: string | null;
    full_name: string | null;
    is_self: boolean;
  } | null;
  
  setCurrentTelegramUser: (user: TelegramUserState['currentTelegramUser']) => void;
  clearCurrentTelegramUser: () => void;
}

// 创建 Telegram 用户状态 store
export const useTelegramUserStore = create<TelegramUserState>((set) => ({
  currentTelegramUser: null,
  
  setCurrentTelegramUser: (currentTelegramUser) => set({ currentTelegramUser }),
  clearCurrentTelegramUser: () => set({ currentTelegramUser: null }),
}));

// 创建规则状态store
export const useRuleStore = create<RuleState>((set) => ({
  rules: [],
  selectedRule: null,
  
  setRules: (rules) => set({ rules }),
  setSelectedRule: (selectedRule) => set({ selectedRule }),
  
  addRule: (rule) => set((state) => ({ 
    rules: [...state.rules, rule] 
  })),
  
  updateRule: (id, updates) => set((state) => ({
    rules: state.rules.map(rule => 
      rule.id === id ? { ...rule, ...updates } : rule
    )
  })),
  
  removeRule: (id) => set((state) => ({
    rules: state.rules.filter(rule => rule.id !== id)
  })),
}));

// 创建任务状态store
export const useTaskStore = create<TaskState>((set) => ({
  tasks: [],
  selectedTask: null,
  
  setTasks: (tasks) => set({ tasks }),
  setSelectedTask: (selectedTask) => set({ selectedTask }),
  
  addTask: (task) => set((state) => ({ 
    tasks: [...state.tasks, task] 
  })),
  
  updateTask: (id, updates) => set((state) => ({
    tasks: state.tasks.map(task => 
      task.id === id ? { ...task, ...updates } : task
    )
  })),
  
  removeTask: (id) => set((state) => ({
    tasks: state.tasks.filter(task => task.id !== id)
  })),
}));

// 创建日志状态store
export const useLogStore = create<LogState>((set) => ({
  logs: [],
  maxLogs: 1000,
  
  setLogs: (logs) => set({ logs }),
  
  addLog: (log) => set((state) => {
    const newLogs = [log, ...state.logs];
    return { 
      logs: newLogs.slice(0, state.maxLogs)
    };
  }),
  
  clearLogs: () => set({ logs: [] }),
  setMaxLogs: (maxLogs) => set({ maxLogs }),
}));

// 创建统计数据状态store
export const useStatisticsStore = create<StatisticsState>((set) => ({
  statistics: null,
  setStatistics: (statistics) => set({ statistics }),
}));

// 导出用户设置Store (导入自userSettingsStore.ts)
export { useUserSettingsStore } from './userSettingsStore';