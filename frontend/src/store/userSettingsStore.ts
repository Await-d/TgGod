import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { UserSettings } from '../services/userSettingsService';

// 定义用户设置状态接口
interface UserSettingsState {
  // 设置数据
  settings: UserSettings;
  isLoading: boolean;
  error: string | null;
  
  // 设置方法
  setSettings: (settings: Partial<UserSettings>) => void;
  setIsLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  resetSettings: () => void;
  
  // 具体设置项的便捷方法
  setTheme: (theme: UserSettings['theme']) => void;
  setLanguage: (language: string) => void;
  setNotificationEnabled: (enabled: boolean) => void;
  setAutoDownload: (enabled: boolean) => void;
  setAutoDownloadMaxSize: (size: number) => void;
  setDisplayDensity: (density: UserSettings['displayDensity']) => void;
  setDeveloperMode: (enabled: boolean) => void;
}

// 默认设置
const defaultSettings: UserSettings = {
  language: 'zh_CN',
  theme: 'system',
  notificationEnabled: true,
  autoDownload: false,
  autoDownloadMaxSize: 10, // MB
  thumbnailsEnabled: true,
  timezone: 'Asia/Shanghai',
  dateFormat: 'YYYY-MM-DD HH:mm',
  defaultDownloadPath: 'downloads',
  displayDensity: 'default',
  previewFilesInline: true,
  defaultPageSize: 20,
  developerMode: false
};

// 创建用户设置状态store（持久化）
export const useUserSettingsStore = create<UserSettingsState>()(
  persist(
    (set) => ({
      settings: defaultSettings,
      isLoading: false,
      error: null,
      
      setSettings: (newSettings) => set((state) => ({
        settings: { ...state.settings, ...newSettings }
      })),
      
      setIsLoading: (isLoading) => set({ isLoading }),
      
      setError: (error) => set({ error }),
      
      resetSettings: () => set({ settings: defaultSettings }),
      
      // 便捷方法
      setTheme: (theme) => set((state) => ({
        settings: { ...state.settings, theme }
      })),
      
      setLanguage: (language) => set((state) => ({
        settings: { ...state.settings, language }
      })),
      
      setNotificationEnabled: (notificationEnabled) => set((state) => ({
        settings: { ...state.settings, notificationEnabled }
      })),
      
      setAutoDownload: (autoDownload) => set((state) => ({
        settings: { ...state.settings, autoDownload }
      })),
      
      setAutoDownloadMaxSize: (autoDownloadMaxSize) => set((state) => ({
        settings: { ...state.settings, autoDownloadMaxSize }
      })),
      
      setDisplayDensity: (displayDensity) => set((state) => ({
        settings: { ...state.settings, displayDensity }
      })),
      
      setDeveloperMode: (developerMode) => set((state) => ({
        settings: { ...state.settings, developerMode }
      })),
    }),
    {
      name: 'user-settings-storage',
      partialize: (state) => ({ settings: state.settings }),
    }
  )
);