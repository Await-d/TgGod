import React, { useState, useEffect, useCallback } from 'react';
import { Input, Button, Space, message, Modal, Form, Badge, Spin } from 'antd';
import { PlusOutlined, SearchOutlined, ReloadOutlined, UserOutlined } from '@ant-design/icons';
import { TelegramGroup } from '../../types';
import { GroupListItemProps } from '../../types/chat';
import GroupItem from './GroupItem';
import { telegramApi } from '../../services/apiService';
import { useTelegramStore } from '../../store';
import './GroupList.css';

const { Search } = Input;

interface GroupListProps {
  selectedGroup: TelegramGroup | null;
  onGroupSelect: (group: TelegramGroup) => void;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
  isMobile?: boolean;
}

const GroupList: React.FC<GroupListProps> = ({
  selectedGroup,
  onGroupSelect,
  searchQuery = '',
  onSearchChange,
  isMobile = false
}) => {
  const [loading, setLoading] = useState(false);
  const [addGroupModalVisible, setAddGroupModalVisible] = useState(false);
  const [localSearchQuery, setLocalSearchQuery] = useState(searchQuery);
  const [form] = Form.useForm();
  
  const { groups, setGroups, addGroup } = useTelegramStore();

  // 获取群组列表
  const fetchGroups = useCallback(async () => {
    setLoading(true);
    try {
      const response = await telegramApi.getGroups();
      setGroups(response);
    } catch (error: any) {
      message.error('获取群组列表失败: ' + error.message);
      console.error('获取群组列表失败:', error);
    } finally {
      setLoading(false);
    }
  }, [setGroups]);

  // 添加群组
  const handleAddGroup = async (values: { username: string }) => {
    try {
      const response = await telegramApi.addGroup(values.username);
      addGroup(response);
      setAddGroupModalVisible(false);
      form.resetFields();
      message.success('群组添加成功！');
    } catch (error: any) {
      message.error('添加群组失败: ' + error.message);
      console.error('添加群组失败:', error);
    }
  };

  // 搜索处理
  const handleSearch = useCallback((value: string) => {
    setLocalSearchQuery(value);
    onSearchChange?.(value);
  }, [onSearchChange]);

  // 过滤群组
  const filteredGroups = groups.filter(group => {
    const query = (onSearchChange ? searchQuery : localSearchQuery).toLowerCase();
    return (
      group.title.toLowerCase().includes(query) ||
      (group.username && group.username.toLowerCase().includes(query))
    );
  });

  // 组件挂载时获取群组列表
  useEffect(() => {
    fetchGroups();
  }, [fetchGroups]);

  // 计算群组统计
  const groupStats = {
    total: groups.length,
    active: groups.filter(g => g.is_active).length,
    inactive: groups.filter(g => !g.is_active).length
  };

  return (
    <div className="group-list">
      {/* 群组列表头部 */}
      <div className="group-list-header">
        <div className="header-title">
          <h4>群组列表</h4>
          <Badge count={groupStats.total} showZero style={{ backgroundColor: '#52c41a' }} />
        </div>
        
        <div className="header-actions">
          <Space size="small">
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={fetchGroups}
              loading={loading}
              size={isMobile ? 'small' : 'middle'}
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setAddGroupModalVisible(true)}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '' : '添加'}
            </Button>
          </Space>
        </div>
      </div>

      {/* 搜索框 */}
      <div className="group-search">
        <Search
          placeholder="搜索群组..."
          value={onSearchChange ? searchQuery : localSearchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          prefix={<SearchOutlined />}
          allowClear
        />
      </div>

      {/* 群组统计 */}
      <div className="group-stats">
        <div className="stat-item">
          <span className="stat-label">总计</span>
          <span className="stat-value">{groupStats.total}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">活跃</span>
          <span className="stat-value active">{groupStats.active}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">暂停</span>
          <span className="stat-value inactive">{groupStats.inactive}</span>
        </div>
      </div>

      {/* 群组列表 */}
      <div className="group-list-content">
        {loading ? (
          <div className="loading-container">
            <Spin size="large" />
          </div>
        ) : filteredGroups.length === 0 ? (
          <div className="empty-groups">
            <UserOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
            <p>暂无群组</p>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setAddGroupModalVisible(true)}
            >
              添加群组
            </Button>
          </div>
        ) : (
          filteredGroups.map(group => (
            <GroupItem
              key={group.id}
              group={group}
              isSelected={selectedGroup?.id === group.id}
              onClick={onGroupSelect}
              unreadCount={0} // TODO: 实现未读消息计数
              lastMessageTime={group.updated_at}
            />
          ))
        )}
      </div>

      {/* 添加群组模态框 */}
      <Modal
        title="添加群组"
        open={addGroupModalVisible}
        onCancel={() => {
          setAddGroupModalVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={isMobile ? '90%' : 500}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleAddGroup}
        >
          <Form.Item
            label="群组用户名"
            name="username"
            rules={[
              { required: true, message: '请输入群组用户名' },
              { 
                pattern: /^[a-zA-Z0-9_]+$/, 
                message: '用户名只能包含字母、数字和下划线' 
              }
            ]}
          >
            <Input
              placeholder="请输入群组用户名（不包含@）"
              prefix="@"
              maxLength={50}
            />
          </Form.Item>
          
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button 
                onClick={() => {
                  setAddGroupModalVisible(false);
                  form.resetFields();
                }}
              >
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                添加
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default GroupList;