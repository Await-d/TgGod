import React, { ReactNode } from 'react';
import { useResponsiveLayout, useSidebarState } from '../../../hooks/useResponsiveLayout';
import styles from './ChatLayout.module.css';

interface ChatLayoutProps {
  sidebar: ReactNode;
  header: ReactNode;
  main: ReactNode;
  footer: ReactNode;
  className?: string;
}

/**
 * 聊天界面统一布局组件
 * 自动适配桌面端、平板和移动端
 */
export const ChatLayout: React.FC<ChatLayoutProps> = ({
  sidebar,
  header,
  main,
  footer,
  className = '',
}) => {
  const { deviceType, isMobile, layoutConfig } = useResponsiveLayout();
  const sidebarState = useSidebarState(layoutConfig.showSidebarByDefault);

  // 移动端使用抽屉，桌面端使用固定侧边栏
  const renderSidebar = () => {
    if (isMobile) {
      return (
        <div
          className={`${styles.drawer} ${sidebarState.visible ? styles.drawerVisible : ''}`}
          style={{
            width: layoutConfig.sidebarWidth,
          }}
        >
          <div className={styles.drawerOverlay} onClick={sidebarState.hide} />
          <div className={styles.drawerContent}>{sidebar}</div>
        </div>
      );
    }

    return (
      <aside
        className={`${styles.sidebar} ${!sidebarState.visible ? styles.sidebarHidden : ''}`}
        style={{
          width: sidebarState.visible ? sidebarState.width : 0,
          minWidth: layoutConfig.minWidth,
          maxWidth: layoutConfig.maxWidth,
        }}
      >
        {sidebar}
      </aside>
    );
  };

  return (
    <div
      className={`${styles.chatLayout} ${styles[deviceType]} ${className}`}
      data-device={deviceType}
    >
      {renderSidebar()}

      <div className={styles.mainContainer}>
        <header className={styles.header}>{header}</header>

        <main className={styles.main}>{main}</main>

        <footer className={styles.footer}>{footer}</footer>
      </div>
    </div>
  );
};

export default ChatLayout;
