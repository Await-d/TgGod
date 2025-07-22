import React, { useEffect } from 'react';
import { useUserSettingsStore } from '../../store/userSettingsStore';

// 主题提供器组件 - 根据用户设置应用主题
const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { settings } = useUserSettingsStore();
  
  useEffect(() => {
    // 获取当前主题设置
    const { theme } = settings;
    
    // 检测系统主题
    const prefersDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // 应用主题
    let isDarkMode = false;
    
    if (theme === 'system') {
      isDarkMode = prefersDarkMode;
    } else {
      isDarkMode = theme === 'dark';
    }
    
    // 应用主题到HTML元素
    if (isDarkMode) {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
    }
    
    // 监听系统主题变化
    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      
      const handleChange = (e: MediaQueryListEvent) => {
        const newIsDarkMode = e.matches;
        document.documentElement.setAttribute('data-theme', newIsDarkMode ? 'dark' : 'light');
      };
      
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [settings.theme]);
  
  return <>{children}</>;
};

export default ThemeProvider;