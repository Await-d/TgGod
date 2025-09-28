// 暂时移除API依赖，使用本地存储

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
      // 从本地存储获取设置
      const localSettings = localStorage.getItem('user-settings');
      const settings = localSettings ? 
        { ...defaultSettings, ...JSON.parse(localSettings) } : 
        defaultSettings;
      
      console.log('Loaded user settings:', settings);
      return settings;
    } catch (error) {
      console.warn('Failed to load user settings, using defaults:', error);
      return defaultSettings;
    }
  },

  // 保存用户设置
  saveUserSettings: async (settings: Partial<UserSettings>): Promise<UserSettings> => {
    try {
      // 获取当前存储的设置
      const currentSettings = await userSettingsService.getUserSettings();
      const newSettings = { ...currentSettings, ...settings };
      
      // 保存到本地存储
      localStorage.setItem('user-settings', JSON.stringify(newSettings));
      
      console.log('Saved user settings:', newSettings);
      return newSettings;
    } catch (error) {
      console.error('Failed to save user settings:', error);
      throw error;
    }
  },

  // 重置用户设置
  resetUserSettings: async (): Promise<UserSettings> => {
    try {
      // 清除本地存储的设置
      localStorage.removeItem('user-settings');
      console.log('Reset user settings to defaults');
      return defaultSettings;
    } catch (error) {
      console.error('Failed to reset user settings:', error);
      throw error;
    }
  }
};