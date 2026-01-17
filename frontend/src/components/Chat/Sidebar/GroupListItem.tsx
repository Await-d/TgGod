import React from 'react';
import { Avatar, Badge } from 'antd';
import { TeamOutlined } from '@ant-design/icons';
import styles from './GroupListItem.module.css';

/**
 * GroupListItem Component
 *
 * Displays a single group in the sidebar list with:
 * - Avatar (generated from group name)
 * - Group name and last message preview
 * - Unread count badge
 * - Selected and hover states
 *
 * Usage:
 * <GroupListItem
 *   group={groupInfo}
 *   isSelected={selectedGroupId === groupInfo.id}
 *   onClick={() => handleSelectGroup(groupInfo.id)}
 * />
 */

export interface GroupInfo {
  id: string;
  name: string;
  avatar?: string;
  lastMessage?: string;
  lastMessageTime?: Date;
  unreadCount?: number;
}

interface GroupListItemProps {
  group: GroupInfo;
  isSelected?: boolean;
  onClick?: () => void;
  className?: string;
}

const GroupListItem: React.FC<GroupListItemProps> = React.memo(({
  group,
  isSelected = false,
  onClick,
  className = ''
}) => {
  // Generate avatar from first letter of group name
  const getAvatarText = (name: string): string => {
    return name.charAt(0).toUpperCase();
  };

  // Format time display
  const formatTime = (date?: Date): string => {
    if (!date) return '';

    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;

    return date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' });
  };

  // Truncate long text
  const truncateText = (text: string, maxLength: number = 30): string => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div
      className={`${styles.groupListItem} ${isSelected ? styles.selected : ''} ${className}`}
      onClick={onClick}
      role="option"
      aria-selected={isSelected}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.();
        }
      }}
    >
      <div className={styles.avatarWrapper}>
        <Badge count={group.unreadCount || 0} offset={[-5, 5]}>
          {group.avatar ? (
            <Avatar size={48} src={group.avatar} alt={group.name} />
          ) : (
            <Avatar
              size={48}
              style={{
                backgroundColor: '#1890ff',
                fontSize: '20px',
                fontWeight: 600
              }}
              icon={!group.name ? <TeamOutlined /> : undefined}
            >
              {group.name ? getAvatarText(group.name) : null}
            </Avatar>
          )}
        </Badge>
      </div>

      <div className={styles.content}>
        <div className={styles.header}>
          <span className={styles.groupName} title={group.name}>
            {truncateText(group.name, 20)}
          </span>
          {group.lastMessageTime && (
            <span className={styles.time}>
              {formatTime(group.lastMessageTime)}
            </span>
          )}
        </div>

        {group.lastMessage && (
          <div className={styles.lastMessage} title={group.lastMessage}>
            {truncateText(group.lastMessage)}
          </div>
        )}
      </div>
    </div>
  );
});

GroupListItem.displayName = 'GroupListItem';

export default GroupListItem;
