import api from './apiService';

export interface UserSettings {
  language: string;
  theme: 'light' | 'dark' | 'system';
  notificationEnabled: boolean;
  autoDownload: boolean;
  autoDownloadMaxSize: number;
  thumbnailsEnabled: boolean;
  timezone: string;
  dateFormat: string;
  defaultDownloadPath: string;
  displayDensity: 'default' | 'compact' | 'comfortable';
  previewFilesInline: boolean;
  defaultPageSize: number;
  developerMode: boolean;
}

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

export const userSettingsService = {
  // 获取用户设置
  getUserSettings: async (): Promise<UserSettings> => {
    try {
      // 尝试从后端获取设置
      const response = await api.get('/user/settings');
      return { ...defaultSettings, ...response.data };
    } catch (error) {
      // 如果后端接口不存在，则从本地存储获取
      console.warn('无法从后端获取用户设置，将使用本地存储', error);
      const localSettings = localStorage.getItem('user-settings');
      return localSettings ? 
        { ...defaultSettings, ...JSON.parse(localSettings) } : 
        defaultSettings;
    }
  },

  // 保存用户设置
  saveUserSettings: async (settings: Partial<UserSettings>): Promise<UserSettings> => {
    try {
      // 尝试保存到后端（需要包装为API期望的格式）
      const response = await api.post('/user/settings', { 
        settings_data: settings 
      });
      const savedSettings = { ...defaultSettings, ...response.data };
      
      // 同时保存到本地存储作为备份
      localStorage.setItem('user-settings', JSON.stringify(savedSettings));
      
      return savedSettings;
    } catch (error) {
      // 如果后端接口不存在，则仅保存到本地存储
      console.warn('无法保存用户设置到后端，将仅使用本地存储', error);
      
      // 获取当前存储的设置
      const currentSettings = await userSettingsService.getUserSettings();
      const newSettings = { ...currentSettings, ...settings };
      
      // 保存到本地存储
      localStorage.setItem('user-settings', JSON.stringify(newSettings));
      
      return newSettings;
    }
  },

  // 重置用户设置
  resetUserSettings: async (): Promise<UserSettings> => {
    try {
      // 尝试在后端重置设置
      await api.delete('/user/settings');
    } catch (error) {
      // 接口可能不存在，忽略错误
    }
    
    // 清除本地存储的设置
    localStorage.removeItem('user-settings');
    
    return defaultSettings;
  }
};