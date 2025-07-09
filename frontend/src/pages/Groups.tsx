import React from 'react';
import { 
  Table, 
  Button, 
  Space, 
  Modal, 
  Form, 
  Input, 
  message, 
  Popconfirm,
  Tag,
  Typography,
  Card,
  Statistic,
  Row,
  Col
} from 'antd';
import { 
  PlusOutlined, 
  SyncOutlined, 
  DeleteOutlined, 
  PlayCircleOutlined,
  PauseCircleOutlined,
  TeamOutlined,
  MessageOutlined
} from '@ant-design/icons';
import { TelegramGroup } from '../types';
import { useTelegramStore, useGlobalStore } from '../store';
import { apiService } from '../services/api';

const { Title } = Typography;

const Groups: React.FC = () => {
  const { groups, setGroups, addGroup, updateGroup, removeGroup } = useTelegramStore();
  const { setLoading, setError } = useGlobalStore();
  const [isModalVisible, setIsModalVisible] = React.useState(false);
  const [form] = Form.useForm();

  React.useEffect(() => {
    loadGroups();
  }, []);

  const loadGroups = async () => {
    setLoading(true);
    try {
      const response = await apiService.get<TelegramGroup[]>('/telegram/groups');
      if (response.success && response.data) {
        setGroups(response.data);
      }
    } catch (error) {
      setError('加载群组列表失败');
      console.error('加载群组失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddGroup = async (values: { username: string }) => {
    try {
      const response = await apiService.post<TelegramGroup>('/telegram/groups', values);
      if (response.success && response.data) {
        addGroup(response.data);
        setIsModalVisible(false);
        form.resetFields();
        message.success('群组添加成功');
      }
    } catch (error) {
      message.error('添加群组失败');
      console.error('添加群组失败:', error);
    }
  };

  const handleSyncMessages = async (groupId: number) => {
    try {
      const response = await apiService.post(`/telegram/groups/${groupId}/sync`);
      if (response.success) {
        message.success('消息同步成功');
      }
    } catch (error) {
      message.error('消息同步失败');
      console.error('消息同步失败:', error);
    }
  };

  const handleToggleStatus = async (groupId: number, currentStatus: boolean) => {
    try {
      const response = await apiService.put<TelegramGroup>(`/telegram/groups/${groupId}`, {
        is_active: !currentStatus
      });
      if (response.success && response.data) {
        updateGroup(groupId, { is_active: !currentStatus });
        message.success('状态更新成功');
      }
    } catch (error) {
      message.error('状态更新失败');
      console.error('状态更新失败:', error);
    }
  };

  const handleDeleteGroup = async (groupId: number) => {
    try {
      const response = await apiService.delete(`/telegram/groups/${groupId}`);
      if (response.success) {
        removeGroup(groupId);
        message.success('群组删除成功');
      }
    } catch (error) {
      message.error('删除群组失败');
      console.error('删除群组失败:', error);
    }
  };

  const columns = [
    {
      title: '群组名称',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: TelegramGroup) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            @{record.username}
          </div>
        </div>
      ),
    },
    {
      title: '成员数量',
      dataIndex: 'member_count',
      key: 'member_count',
      render: (count: number) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <TeamOutlined />
          <span>{count.toLocaleString()}</span>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'red'}>
          {isActive ? '活跃' : '暂停'}
        </Tag>
      ),
    },
    {
      title: '添加时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: TelegramGroup) => (
        <Space size="middle">
          <Button
            type="text"
            size="small"
            icon={<SyncOutlined />}
            onClick={() => handleSyncMessages(record.id)}
          >
            同步消息
          </Button>
          <Button
            type="text"
            size="small"
            icon={record.is_active ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={() => handleToggleStatus(record.id, record.is_active)}
          >
            {record.is_active ? '暂停' : '启用'}
          </Button>
          <Popconfirm
            title="确定要删除这个群组吗？"
            description="删除后所有相关数据都将被清除"
            onConfirm={() => handleDeleteGroup(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={2}>群组管理</Title>
        <Space>
          <Button icon={<SyncOutlined />} onClick={loadGroups}>
            刷新
          </Button>
          <Button 
            type="primary" 
            icon={<PlusOutlined />} 
            onClick={() => setIsModalVisible(true)}
          >
            添加群组
          </Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="总群组数"
              value={groups.length}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="活跃群组"
              value={groups.filter(g => g.is_active).length}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="总成员数"
              value={groups.reduce((sum, g) => sum + g.member_count, 0)}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 群组表格 */}
      <Table
        columns={columns}
        dataSource={groups}
        rowKey="id"
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
        }}
      />

      {/* 添加群组模态框 */}
      <Modal
        title="添加群组"
        open={isModalVisible}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
        }}
        footer={null}
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
              { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线' }
            ]}
          >
            <Input 
              placeholder="请输入群组用户名（不包含@）"
              prefix="@"
            />
          </Form.Item>
          
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setIsModalVisible(false)}>
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

export default Groups;