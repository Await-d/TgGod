import React, { useEffect, useMemo } from 'react';
import { ConfigProvider, theme as antTheme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import enUS from 'antd/locale/en_US';
import { useUserSettingsStore } from '../../store/userSettingsStore';

const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { settings } = useUserSettingsStore();

  const isDarkMode = useMemo(() => {
    const { theme } = settings;
    if (theme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return theme === 'dark';
  }, [settings]);

  useEffect(() => {
    const { theme } = settings;
    const prefersDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
    let dark = false;
    if (theme === 'system') {
      dark = prefersDarkMode;
    } else {
      dark = theme === 'dark';
    }
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');

    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = (e: MediaQueryListEvent) => {
        document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
      };
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [settings]);

  const antdLocale = settings.language === 'en_US' ? enUS : zhCN;

  return (
    <ConfigProvider
      locale={antdLocale}
      theme={{
        algorithm: isDarkMode ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm,
      }}
    >
      {children}
    </ConfigProvider>
  );
};

export default ThemeProvider;