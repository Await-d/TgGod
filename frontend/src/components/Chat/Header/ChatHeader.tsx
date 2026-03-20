import React, { useCallback, useMemo } from 'react';
import { Button, Dropdown, Avatar, Space, Badge } from 'antd';
import {
  MenuOutlined, SearchOutlined, MoreOutlined, UserOutlined,
  BellOutlined, SettingOutlined, LogoutOutlined, InfoCircleOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useResponsiveLayout } from '../../../hooks/useResponsiveLayout';
import styles from './ChatHeader.module.css';

export interface ChatHeaderProps {
  groupName: string;
  groupAvatar?: string;
  memberCount?: number;
  onlineCount?: number;
  onToggleSidebar?: () => void;
  onSearch?: () => void;
  showSidebarToggle?: boolean;
  className?: string;
}

/**
 * ChatHeader - Chat interface header component
 * Features: Group info, responsive layout, action buttons, accessibility
 *
 * @example
 * <ChatHeader groupName="Tech" memberCount={1234} onlineCount={89} />
 */
const ChatHeader: React.FC<ChatHeaderProps> = React.memo(({
  groupName,
  groupAvatar,
  memberCount,
  onlineCount,
  onToggleSidebar,
  onSearch,
  showSidebarToggle = false,
  className = '',
}) => {
  const { isMobile } = useResponsiveLayout();

  const moreMenuItems: MenuProps['items'] = useMemo(() => [
    { key: 'info', icon: <InfoCircleOutlined />, label: 'Group Info' },
    { key: 'notifications', icon: <BellOutlined />, label: 'Notifications' },
    { key: 'settings', icon: <SettingOutlined />, label: 'Settings' },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: 'Logout', danger: true },
  ], []);

  const handleMenuClick: MenuProps['onClick'] = useCallback((e: { key: string }) => {
  }, []);

  const memberCountText = useMemo(() => {
    if (!memberCount) return '';
    return onlineCount
      ? `${onlineCount} online / ${memberCount} members`
      : `${memberCount} members`;
  }, [memberCount, onlineCount]);

  const avatarFallback = useMemo(() =>
    groupName.charAt(0).toUpperCase(), [groupName]
  );

  return (
    <header
      className={`${styles.header} ${className}`}
      role="banner"
      aria-label="Chat header"
    >
      <div className={styles.headerContent}>
        <div className={styles.leftSection}>
          {showSidebarToggle && (
            <Button
              type="text"
              icon={<MenuOutlined />}
              onClick={onToggleSidebar}
              className={styles.iconButton}
              aria-label="Toggle sidebar"
            />
          )}

          <Space size={isMobile ? 8 : 12} className={styles.groupInfo}>
            <Badge
              dot
              status={onlineCount ? 'success' : 'default'}
              offset={[-4, 32]}
            >
              <Avatar
                src={groupAvatar}
                icon={!groupAvatar && <UserOutlined />}
                size={isMobile ? 36 : 40}
                className={styles.avatar}
              >
                {!groupAvatar && avatarFallback}
              </Avatar>
            </Badge>

            <div className={styles.groupDetails}>
              <h1 className={styles.groupName} title={groupName}>
                {groupName}
              </h1>
              {memberCountText && !isMobile && (
                <p className={styles.memberCount}>{memberCountText}</p>
              )}
            </div>
          </Space>
        </div>

        <div className={styles.rightSection}>
          <Space size={isMobile ? 4 : 8}>
            <Button
              type="text"
              icon={<SearchOutlined />}
              onClick={onSearch}
              className={styles.iconButton}
              aria-label="Search messages"
            />

            <Dropdown
              menu={{ items: moreMenuItems, onClick: handleMenuClick }}
              trigger={['click']}
              placement="bottomRight"
            >
              <Button
                type="text"
                icon={<MoreOutlined />}
                className={styles.iconButton}
                aria-label="More options"
              />
            </Dropdown>
          </Space>
        </div>
      </div>
    </header>
  );
});

ChatHeader.displayName = 'ChatHeader';

export default ChatHeader;
