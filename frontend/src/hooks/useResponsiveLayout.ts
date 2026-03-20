import { useState, useEffect, useCallback } from 'react';
import { getDeviceType, getLayoutConfig } from '../constants/chatLayout';
import type { DeviceType, LayoutConfig } from '../constants/chatLayout';

/**
 * 响应式布局 Hook
 * 统一管理设备类型检测和布局配置
 */
export const useResponsiveLayout = () => {
  const [deviceType, setDeviceType] = useState<DeviceType>(() =>
    getDeviceType(window.innerWidth)
  );

  const [layoutConfig, setLayoutConfig] = useState<LayoutConfig>(() =>
    getLayoutConfig(deviceType)
  );

  const [windowSize, setWindowSize] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  // 更新设备类型和布局配置
  const updateLayout = useCallback(() => {
    const width = window.innerWidth;
    const height = window.innerHeight;

    setWindowSize({ width, height });

    const newDeviceType = getDeviceType(width);
    if (newDeviceType !== deviceType) {
      setDeviceType(newDeviceType);
      setLayoutConfig(getLayoutConfig(newDeviceType));
    }
  }, [deviceType]);

  useEffect(() => {
    // 防抖处理 resize 事件
    let timeoutId: NodeJS.Timeout;

    const handleResize = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(updateLayout, 150);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      clearTimeout(timeoutId);
      window.removeEventListener('resize', handleResize);
    };
  }, [updateLayout]);

  return {
    deviceType,
    layoutConfig,
    windowSize,
    isMobile: deviceType === 'mobile',
    isTablet: deviceType === 'tablet',
    isDesktop: deviceType === 'desktop',
  };
};

/**
 * 侧边栏状态 Hook
 * 管理侧边栏的显示/隐藏和宽度
 */
export const useSidebarState = (initialVisible: boolean = true) => {
  const [visible, setVisible] = useState(initialVisible);
  const [width, setWidth] = useState(320);

  const toggle = useCallback(() => {
    setVisible(prev => !prev);
  }, []);

  const show = useCallback(() => {
    setVisible(true);
  }, []);

  const hide = useCallback(() => {
    setVisible(false);
  }, []);

  const updateWidth = useCallback((newWidth: number) => {
    setWidth(newWidth);
  }, []);

  return {
    visible,
    width,
    toggle,
    show,
    hide,
    updateWidth,
  };
};
