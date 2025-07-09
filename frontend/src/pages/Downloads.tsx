import React from 'react';
import { 
  Table, 
  Button, 
  Space, 
  Modal, 
  Form, 
  Input, 
  Select, 
  Progress,
  Tag,
  message,
  Popconfirm,
  Typography,
  Card,
  Row,
  Col,
  Statistic
} from 'antd';
import { 
  PlusOutlined, 
  PlayCircleOutlined, 
  PauseCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  DownloadOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { DownloadTask, TelegramGroup, FilterRule } from '../types';
import { useTaskStore, useTelegramStore, useRuleStore, useGlobalStore } from '../store';
import { apiService } from '../services/api';

const { Title } = Typography;

const Downloads: React.FC = () => {
  const { tasks, setTasks, addTask, updateTask, removeTask } = useTaskStore();
  const { groups, setGroups } = useTelegramStore();
  const { rules, setRules } = useRuleStore();
  const { setLoading, setError } = useGlobalStore();
  const [isModalVisible, setIsModalVisible] = React.useState(false);
  const [form] = Form.useForm();

  const loadData = React.useCallback(async () => {
    setLoading(true);
    try {
      // 加载群组数据
      const groupsResponse = await apiService.get<TelegramGroup[]>('/telegram/groups');
      if (groupsResponse.success && groupsResponse.data) {
        setGroups(groupsResponse.data);
      }

      // 加载规则数据
      const rulesResponse = await apiService.get<FilterRule[]>('/rule/rules');
      if (rulesResponse.success && rulesResponse.data) {
        setRules(rulesResponse.data);
      }

      // 加载任务数据
      const tasksResponse = await apiService.get<DownloadTask[]>('/task/tasks');
      if (tasksResponse.success && tasksResponse.data) {
        setTasks(tasksResponse.data);
      }
    } catch (error) {
      setError('加载数据失败');
      console.error('加载数据失败:', error);
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, setGroups, setRules, setTasks]);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSubmit = async (values: any) => {
    try {
      const response = await apiService.post<DownloadTask>('/task/tasks', values);
      if (response.success && response.data) {
        addTask(response.data);
        setIsModalVisible(false);
        form.resetFields();
        message.success('任务创建成功');
      }
    } catch (error) {
      message.error('创建任务失败');
      console.error('创建任务失败:', error);
    }
  };

  const handleStartTask = async (taskId: number) => {
    try {
      const response = await apiService.post(`/task/tasks/${taskId}/start`);
      if (response.success) {
        updateTask(taskId, { status: 'running' });
        message.success('任务启动成功');
      }
    } catch (error) {
      message.error('启动任务失败');
      console.error('启动任务失败:', error);
    }
  };

  const handlePauseTask = async (taskId: number) => {
    try {
      const response = await apiService.post(`/task/tasks/${taskId}/pause`);
      if (response.success) {
        updateTask(taskId, { status: 'paused' });
        message.success('任务暂停成功');
      }
    } catch (error) {
      message.error('暂停任务失败');
      console.error('暂停任务失败:', error);
    }
  };

  const handleStopTask = async (taskId: number) => {
    try {
      const response = await apiService.post(`/task/tasks/${taskId}/stop`);
      if (response.success) {
        updateTask(taskId, { status: 'failed' });
        message.success('任务停止成功');
      }
    } catch (error) {
      message.error('停止任务失败');
      console.error('停止任务失败:', error);
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    try {
      const response = await apiService.delete(`/task/tasks/${taskId}`);
      if (response.success) {
        removeTask(taskId);
        message.success('任务删除成功');
      }
    } catch (error) {
      message.error('删除任务失败');
      console.error('删除任务失败:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'processing';
      case 'paused': return 'warning';
      case 'completed': return 'success';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'running': return '运行中';
      case 'paused': return '已暂停';
      case 'completed': return '已完成';
      case 'failed': return '失败';
      case 'pending': return '等待中';
      default: return '未知';
    }
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: DownloadTask) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {groups.find(g => g.id === record.group_id)?.title || '未知群组'}
          </div>
        </div>
      ),
    },
    {
      title: '规则',
      dataIndex: 'rule_id',
      key: 'rule_id',
      render: (ruleId: number) => (
        <span>{rules.find(r => r.id === ruleId)?.name || '未知规则'}</span>
      ),
    },
    {
      title: '进度',
      key: 'progress',
      render: (_: any, record: DownloadTask) => (
        <div>
          <Progress 
            percent={record.progress} 
            size="small"
            status={record.status === 'failed' ? 'exception' : 'active'}
          />
          <div style={{ fontSize: '12px', color: '#666', marginTop: 4 }}>
            {record.downloaded_messages}/{record.total_messages} 条消息
          </div>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {getStatusText(status)}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: DownloadTask) => (
        <Space size="middle">
          {record.status === 'pending' || record.status === 'paused' ? (
            <Button
              type="text"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleStartTask(record.id)}
            >
              启动
            </Button>
          ) : null}
          
          {record.status === 'running' ? (
            <Button
              type="text"
              size="small"
              icon={<PauseCircleOutlined />}
              onClick={() => handlePauseTask(record.id)}
            >
              暂停
            </Button>
          ) : null}
          
          {record.status === 'running' || record.status === 'paused' ? (
            <Button
              type="text"
              size="small"
              icon={<StopOutlined />}
              onClick={() => handleStopTask(record.id)}
            >
              停止
            </Button>
          ) : null}
          
          {record.status === 'completed' || record.status === 'failed' ? (
            <Popconfirm
              title="确定要删除这个任务吗？"
              onConfirm={() => handleDeleteTask(record.id)}
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
          ) : null}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={2}>下载任务</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadData}>
            刷新
          </Button>
          <Button 
            type="primary" 
            icon={<PlusOutlined />} 
            onClick={() => setIsModalVisible(true)}
          >
            创建任务
          </Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="总任务数"
              value={tasks.length}
              prefix={<DownloadOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="运行中"
              value={tasks.filter(t => t.status === 'running').length}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="已完成"
              value={tasks.filter(t => t.status === 'completed').length}
              prefix={<DownloadOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="失败"
              value={tasks.filter(t => t.status === 'failed').length}
              prefix={<StopOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 任务表格 */}
      <Table
        columns={columns}
        dataSource={tasks}
        rowKey="id"
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
        }}
      />

      {/* 创建任务模态框 */}
      <Modal
        title="创建下载任务"
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
          onFinish={handleSubmit}
        >
          <Form.Item
            label="任务名称"
            name="name"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="请输入任务名称" />
          </Form.Item>
          
          <Form.Item
            label="目标群组"
            name="group_id"
            rules={[{ required: true, message: '请选择目标群组' }]}
          >
            <Select placeholder="请选择群组">
              {groups.map(group => (
                <Select.Option key={group.id} value={group.id}>
                  {group.title}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            label="过滤规则"
            name="rule_id"
            rules={[{ required: true, message: '请选择过滤规则' }]}
          >
            <Select placeholder="请选择规则">
              {rules.filter(rule => rule.is_active).map(rule => (
                <Select.Option key={rule.id} value={rule.id}>
                  {rule.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            label="下载路径"
            name="download_path"
            rules={[{ required: true, message: '请输入下载路径' }]}
            initialValue="./downloads"
          >
            <Input placeholder="请输入下载路径" />
          </Form.Item>
          
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setIsModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                创建任务
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Downloads;