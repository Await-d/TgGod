import { create } from 'zustand';
import { TelegramGroup, TelegramMessage, FilterRule, DownloadTask, LogEntry, Statistics } from '../types';

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

  // 用户信息
  user: any | null;
  setUser: (user: any | null) => void;

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

// 创建全局状态store
export const useGlobalStore = create<GlobalState>((set) => ({
  loading: false,
  error: null,
  connectionStatus: 'disconnected',
  user: null,
  
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
  setUser: (user) => set({ user }),
  clearError: () => set({ error: null }),
  reset: () => set({ loading: false, error: null, connectionStatus: 'disconnected', user: null }),
}));

// 创建Telegram状态store
export const useTelegramStore = create<TelegramState>((set) => ({
  groups: [],
  messages: [],
  selectedGroup: null,
  
  setGroups: (groups) => set({ groups }),
  setMessages: (messages) => set({ messages }),
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