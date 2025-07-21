import React, { useState, useEffect, useCallback } from 'react';
import { Card, Typography, Avatar, Space, Button, message as notification } from 'antd';
import { TeamOutlined, SearchOutlined, UserOutlined } from '@ant-design/icons';
import { telegramApi } from '../../services/apiService';
import './GroupMentionPreview.css';

const { Text } = Typography;

interface GroupMentionPreviewProps {
  type: 'username' | 'id' | 'name';
  value: string;
  text: string;
  onJumpToGroup?: (groupId: number) => void;
  className?: string;
  compact?: boolean;
}

interface GroupSearchResult {
  id: number;
  title: string;
  username?: string;
  description?: string;
  member_count: number;
  is_active: boolean;
}

const GroupMentionPreview: React.FC<GroupMentionPreviewProps> = ({
  type,
  value,
  text,
  onJumpToGroup,
  className = '',
  compact = false
}) => {
  const [loading, setLoading] = useState(false);
  const [groups, setGroups] = useState<GroupSearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  // 搜索群组
  const searchGroups = useCallback(async () => {
    if (loading || (type === 'id' && !value.startsWith('-100'))) return;
    
    setLoading(true);
    setError(null);
    
    try {
      console.log('GroupMentionPreview - searching groups:', { type, value });
      
      let searchResults: GroupSearchResult[] = [];
      
      if (type === 'username') {
        // 通过用户名查找
        try {
          const group = await telegramApi.getGroupByUsername(value);
          if (group) {
            searchResults = [group];
          }
        } catch (err) {
          console.log('Group not found by username, will search in local groups');
        }
      } else if (type === 'id') {
        // 通过ID查找
        try {
          const groupId = parseInt(value);
          const group = await telegramApi.getGroup(groupId);
          if (group) {
            searchResults = [group];
          }
        } catch (err) {
          console.log('Group not found by ID');
        }
      }
      
      // 如果没有找到精确匹配，尝试在本地群组列表中搜索
      if (searchResults.length === 0) {
        const allGroups = await telegramApi.getAllGroups();
        
        if (type === 'username') {
          searchResults = allGroups.filter(group => 
            group.username && group.username.toLowerCase().includes(value.toLowerCase())
          );
        } else if (type === 'name') {
          searchResults = allGroups.filter(group => 
            group.title.toLowerCase().includes(value.toLowerCase())
          );
        } else if (type === 'id') {
          const targetId = parseInt(value);
          searchResults = allGroups.filter(group => 
            group.id === targetId || group.telegram_id === targetId
          );
        }
        
        // 限制结果数量
        searchResults = searchResults.slice(0, 3);
      }
      
      setGroups(searchResults);
      
      if (searchResults.length === 0) {
        setError('未找到相关群组');
      }
      
    } catch (error: any) {
      console.error('Failed to search groups:', error);
      setError('搜索群组失败');
    } finally {
      setLoading(false);
    }
  }, [type, value, loading]);

  // 处理点击展开
  const handleExpand = useCallback(() => {
    if (!expanded && groups.length === 0) {
      searchGroups();
    }
    setExpanded(!expanded);
  }, [expanded, groups.length, searchGroups]);

  // 处理跳转到群组
  const handleJumpToGroup = useCallback((groupId: number) => {
    if (onJumpToGroup) {
      console.log('GroupMentionPreview - jumping to group:', groupId);
      onJumpToGroup(groupId);
    } else {
      notification.info('请在消息列表中点击群组名称进入');
    }
  }, [onJumpToGroup]);

  // 获取显示文本
  const getDisplayText = () => {
    switch (type) {
      case 'username':
        return `@${value}`;
      case 'id':
        return `ID: ${value}`;
      case 'name':
        return value;
      default:
        return text;
    }
  };

  // 获取图标
  const getIcon = () => {
    switch (type) {
      case 'username':
        return <UserOutlined style={{ color: '#1890ff' }} />;
      case 'id':
        return <TeamOutlined style={{ color: '#52c41a' }} />;
      case 'name':
        return <SearchOutlined style={{ color: '#fa8c16' }} />;
      default:
        return <TeamOutlined style={{ color: '#8c8c8c' }} />;
    }
  };

  // 生成群组头像
  const getGroupAvatar = (group: GroupSearchResult) => {
    const firstChar = group.title.charAt(0).toUpperCase();
    return (
      <Avatar 
        size={compact ? 24 : 32}
        style={{ 
          backgroundColor: '#1890ff',
          fontSize: compact ? '12px' : '14px'
        }}
      >
        {firstChar}
      </Avatar>
    );
  };

  return (
    <div className={`group-mention-preview ${compact ? 'compact' : ''} ${className}`}>
      {/* 触发器 */}
      <div 
        className="mention-trigger"
        onClick={handleExpand}
        style={{ 
          cursor: 'pointer',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          padding: '2px 6px',
          borderRadius: 4,
          backgroundColor: '#f0f2f5',
          border: '1px solid #d9d9d9',
          fontSize: compact ? 11 : 12
        }}
      >
        {getIcon()}
        <Text style={{ fontSize: compact ? 11 : 12, color: '#1890ff' }}>
          {getDisplayText()}
        </Text>
        {expanded && (
          <Text type="secondary" style={{ fontSize: 10 }}>
            {loading ? '搜索中...' : groups.length > 0 ? `${groups.length}个` : '点击搜索'}
          </Text>
        )}
      </div>

      {/* 展开的搜索结果 */}
      {expanded && (
        <div className="mention-results" style={{ marginTop: 8 }}>
          {loading && (
            <div style={{ textAlign: 'center', padding: 16 }}>
              <SearchOutlined spin />
              <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                搜索中...
              </Text>
            </div>
          )}

          {error && !loading && (
            <div style={{ textAlign: 'center', padding: 16 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {error}
              </Text>
            </div>
          )}

          {groups.length > 0 && !loading && (
            <div className="group-results">
              {groups.map((group, index) => (
                <Card
                  key={group.id}
                  size="small"
                  style={{ 
                    marginBottom: index < groups.length - 1 ? 8 : 0,
                    cursor: onJumpToGroup ? 'pointer' : 'default'
                  }}
                  onClick={() => onJumpToGroup && handleJumpToGroup(group.id)}
                  hoverable={!!onJumpToGroup}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    {getGroupAvatar(group)}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Text strong style={{ fontSize: 13 }}>
                          {group.title}
                        </Text>
                        {group.username && (
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            @{group.username}
                          </Text>
                        )}
                      </div>
                      
                      {group.description && (
                        <Text 
                          type="secondary" 
                          style={{ 
                            fontSize: 11,
                            display: 'block',
                            marginTop: 2,
                            lineHeight: '1.4'
                          }}
                        >
                          {group.description.length > 50 
                            ? group.description.substring(0, 50) + '...'
                            : group.description
                          }
                        </Text>
                      )}
                      
                      <Space size={8} style={{ marginTop: 4 }}>
                        <Text type="secondary" style={{ fontSize: 10 }}>
                          <TeamOutlined style={{ marginRight: 2 }} />
                          {group.member_count.toLocaleString()} 成员
                        </Text>
                        {group.is_active && (
                          <Text type="success" style={{ fontSize: 10 }}>
                            ● 活跃
                          </Text>
                        )}
                      </Space>
                    </div>
                    
                    {onJumpToGroup && (
                      <Button 
                        type="link" 
                        size="small"
                        style={{ fontSize: 11 }}
                      >
                        查看
                      </Button>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )}

          {!loading && (
            <div style={{ textAlign: 'center', marginTop: 8 }}>
              <Button 
                type="link" 
                size="small"
                onClick={() => setExpanded(false)}
                style={{ fontSize: 11 }}
              >
                收起
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default GroupMentionPreview;