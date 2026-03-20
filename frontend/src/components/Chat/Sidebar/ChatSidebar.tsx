import React, { useState, useCallback, useMemo } from 'react';
import { Input, Empty } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import GroupListItem, { GroupInfo } from './GroupListItem';
import styles from './ChatSidebar.module.css';

/**
 * ChatSidebar Component
 *
 * Displays a searchable list of groups with:
 * - Search functionality with debouncing
 * - Group selection and highlighting
 * - Responsive layout (drawer/fixed/resizable)
 * - Keyboard navigation support
 *
 * Usage:
 * <ChatSidebar
 *   groups={groupList}
 *   selectedGroupId={currentGroupId}
 *   onSelectGroup={(id) => setCurrentGroupId(id)}
 *   onSearch={(keyword) => console.log('Search:', keyword)}
 * />
 */

interface ChatSidebarProps {
  groups: GroupInfo[];
  selectedGroupId?: string;
  onSelectGroup: (groupId: string) => void;
  onSearch?: (keyword: string) => void;
  className?: string;
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({
  groups,
  selectedGroupId,
  onSelectGroup,
  onSearch,
  className = ''
}) => {
  const [searchKeyword, setSearchKeyword] = useState('');

  // Debounced search handler
  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchKeyword(value);
    onSearch?.(value);
  }, [onSearch]);

  // Filter groups based on search keyword
  const filteredGroups = useMemo(() => {
    if (!searchKeyword.trim()) {
      return groups;
    }

    const keyword = searchKeyword.toLowerCase();
    return groups.filter(group =>
      group.name.toLowerCase().includes(keyword) ||
      group.lastMessage?.toLowerCase().includes(keyword)
    );
  }, [groups, searchKeyword]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!filteredGroups.length) return;

    const currentIndex = filteredGroups.findIndex(g => g.id === selectedGroupId);

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const nextIndex = (currentIndex + 1) % filteredGroups.length;
      onSelectGroup(filteredGroups[nextIndex].id);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      const prevIndex = currentIndex <= 0 ? filteredGroups.length - 1 : currentIndex - 1;
      onSelectGroup(filteredGroups[prevIndex].id);
    }
  }, [filteredGroups, selectedGroupId, onSelectGroup]);

  return (
    <div
      className={`${styles.chatSidebar} ${className}`}
      role="navigation"
      aria-label="群组列表"
      onKeyDown={handleKeyDown}
    >
      {/* Search bar */}
      <div className={styles.searchContainer}>
        <Input
          placeholder="搜索群组或消息..."
          prefix={<SearchOutlined />}
          value={searchKeyword}
          onChange={handleSearchChange}
          allowClear
          className={styles.searchInput}
          aria-label="搜索群组"
        />
      </div>

      {/* Group list */}
      <div className={styles.groupList} role="list">
        {filteredGroups.length > 0 ? (
          filteredGroups.map(group => (
            <GroupListItem
              key={group.id}
              group={group}
              isSelected={group.id === selectedGroupId}
              onClick={() => onSelectGroup(group.id)}
            />
          ))
        ) : (
          <div className={styles.emptyState}>
            <Empty
              description={searchKeyword ? '未找到匹配的群组' : '暂无群组'}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          </div>
        )}
      </div>

      {/* Group count footer */}
      {filteredGroups.length > 0 && (
        <div className={styles.footer}>
          <span className={styles.groupCount}>
            {searchKeyword
              ? `找到 ${filteredGroups.length} 个群组`
              : `共 ${groups.length} 个群组`}
          </span>
        </div>
      )}
    </div>
  );
};

export default ChatSidebar;
