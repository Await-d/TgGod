/**
 * 聊天界面布局常量和配置
 * 统一管理响应式断点和布局参数
 */

// 响应式断点
export const BREAKPOINTS = {
  mobile: 768,      // ≤768px 移动端
  tablet: 1024,     // 769-1024px 平板
  desktop: 1025,    // ≥1025px 桌面端
} as const;

// 设备类型
export type DeviceType = 'mobile' | 'tablet' | 'desktop';

// 侧边栏类型
export type SidebarType = 'drawer' | 'fixed' | 'resizable';

// 布局配置
export interface LayoutConfig {
  sidebarType: SidebarType;
  sidebarWidth: number | string;
  minWidth?: number;
  maxWidth?: number;
  showSidebarByDefault: boolean;
}

// 各设备的布局配置
export const LAYOUT_CONFIG: Record<DeviceType, LayoutConfig> = {
  mobile: {
    sidebarType: 'drawer',
    sidebarWidth: '85%',
    showSidebarByDefault: false,
  },
  tablet: {
    sidebarType: 'fixed',
    sidebarWidth: 280,
    showSidebarByDefault: true,
  },
  desktop: {
    sidebarType: 'resizable',
    sidebarWidth: 320,
    minWidth: 260,
    maxWidth: 420,
    showSidebarByDefault: true,
  },
};

// 布局尺寸常量
export const LAYOUT_SIZES = {
  headerHeight: 64,
  footerHeight: 80,
  mobileHeaderHeight: 56,
  mobileFooterHeight: 72,
  sidebarMinWidth: 260,
  sidebarMaxWidth: 420,
  sidebarDefaultWidth: 320,
} as const;

// 动画配置
export const ANIMATION_CONFIG = {
  duration: {
    fast: 150,
    normal: 250,
    slow: 350,
  },
  easing: {
    smooth: 'cubic-bezier(0.4, 0, 0.2, 1)',
    bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
    sharp: 'cubic-bezier(0.4, 0, 0.6, 1)',
  },
} as const;

// Z-index 层级
export const Z_INDEX = {
  base: 1,
  sidebar: 10,
  header: 20,
  drawer: 100,
  modal: 1000,
  tooltip: 1100,
} as const;

// 获取设备类型
export const getDeviceType = (width: number): DeviceType => {
  if (width <= BREAKPOINTS.mobile) return 'mobile';
  if (width <= BREAKPOINTS.tablet) return 'tablet';
  return 'desktop';
};

// 获取布局配置
export const getLayoutConfig = (deviceType: DeviceType): LayoutConfig => {
  return LAYOUT_CONFIG[deviceType];
};
