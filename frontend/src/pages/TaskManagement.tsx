import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Popconfirm,
  message,
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  Row,
  Col,
  Statistic,
  Progress,
  Tooltip,
  Typography,
  Alert,
  Drawer,
  List,
  Badge,
  Spin,
  Empty,
  Switch,
  Dropdown,
  Menu
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  FilterOutlined,
  EyeOutlined,
  SettingOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
  DownOutlined
} from '@ant-design/icons';
import { taskApi, telegramApi, ruleApi, logApi } from '../services/apiService';
import { DownloadTask, TelegramGroup, FilterRule, LogEntry } from '../types';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

// 任务状态颜色映射
const getStatusColor = (status: string) => {
  const colorMap: Record<string, string> = {
    pending: 'orange',
    running: 'blue',
    completed: 'green',
    failed: 'red',
    paused: 'warning'
  };
  return colorMap[status] || 'default';
};

// 任务状态图标映射
const getStatusIcon = (status: string) => {
  const iconMap: Record<string, React.ReactNode> = {
    pending: <ClockCircleOutlined />,
    running: <PlayCircleOutlined spin />,
    completed: <CheckCircleOutlined />,
    failed: <ExclamationCircleOutlined />,
    paused: <PauseCircleOutlined />
  };
  return iconMap[status] || <ClockCircleOutlined />;
};

const TaskManagement: React.FC = () => {
  // 状态管理
  const [tasks, setTasks] = useState<DownloadTask[]>([]);
  const [groups, setGroups] = useState<TelegramGroup[]>([]);
  const [rules, setRules] = useState<FilterRule[]>([]);
  const [taskStats, setTaskStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [selectedTask, setSelectedTask] = useState<DownloadTask | null>(null);
  
  // 模态框状态
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [taskDetailVisible, setTaskDetailVisible] = useState(false);
  const [taskLogsVisible, setTaskLogsVisible] = useState(false);
  
  // 表单和过滤
  const [form] = Form.useForm();
  const [filterForm] = Form.useForm();
  const [filters, setFilters] = useState<any>({});
  const [autoRefresh, setAutoRefresh] = useState(false);
  
  // 日志相关
  const [taskLogs, setTaskLogs] = useState<LogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  // 加载数据
  const loadTasks = useCallback(async () => {
    try {
      setLoading(true);
      const [tasksData, statsData] = await Promise.all([
        taskApi.getTasks(filters),
        taskApi.getTaskStats()
      ]);
      setTasks(tasksData);
      setTaskStats(statsData);
    } catch (error: any) {
      message.error(`加载任务失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const loadGroups = useCallback(async () => {
    try {
      const groupsData = await telegramApi.getAllGroups();
      setGroups(groupsData);
    } catch (error: any) {
      message.error(`加载群组失败: ${error.message}`);
    }
  }, []);

  const loadRules = useCallback(async () => {
    try {
      const rulesData = await ruleApi.getRules();
      setRules(rulesData);
    } catch (error: any) {
      message.error(`加载规则失败: ${error.message}`);
    }
  }, []);

  const loadTaskLogs = useCallback(async (taskId: number) => {
    try {
      setLogsLoading(true);
      const logsData = await logApi.getTaskLogs({ task_id: taskId, limit: 100 });
      setTaskLogs(logsData);
    } catch (error: any) {
      message.error(`加载任务日志失败: ${error.message}`);
    } finally {
      setLogsLoading(false);
    }
  }, []);

  // 任务操作
  const handleStartTask = async (taskId: number) => {
    try {
      await taskApi.startTask(taskId);
      message.success('任务启动成功');
      loadTasks();
    } catch (error: any) {
      message.error(`启动任务失败: ${error.message}`);
    }
  };

  const handlePauseTask = async (taskId: number) => {
    try {
      await taskApi.pauseTask(taskId);
      message.success('任务暂停成功');
      loadTasks();
    } catch (error: any) {
      message.error(`暂停任务失败: ${error.message}`);
    }
  };

  const handleStopTask = async (taskId: number) => {
    try {
      await taskApi.stopTask(taskId);
      message.success('任务停止成功');
      loadTasks();
    } catch (error: any) {
      message.error(`停止任务失败: ${error.message}`);
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    try {
      await taskApi.deleteTask(taskId);
      message.success('任务删除成功');
      loadTasks();
    } catch (error: any) {
      message.error(`删除任务失败: ${error.message}`);
    }
  };

  const handleCreateTask = async (values: any) => {
    try {
      await taskApi.createTask(values);
      message.success('任务创建成功');
      setCreateModalVisible(false);
      form.resetFields();
      loadTasks();
    } catch (error: any) {
      message.error(`创建任务失败: ${error.message}`);
    }
  };

  const handleViewTaskDetail = (task: DownloadTask) => {
    setSelectedTask(task);
    setTaskDetailVisible(true);
  };

  const handleViewTaskLogs = (task: DownloadTask) => {
    setSelectedTask(task);
    loadTaskLogs(task.id);
    setTaskLogsVisible(true);
  };

  const handleFilter = (values: any) => {
    setFilters(values);
  };

  const handleResetFilter = () => {
    filterForm.resetFields();
    setFilters({});
  };

  // 自动刷新
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(() => {
        loadTasks();
      }, 5000); // 每5秒刷新一次
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh, loadTasks]);

  // 初始化加载
  useEffect(() => {
    loadTasks();
    loadGroups();
    loadRules();
  }, [loadTasks, loadGroups, loadRules]);

  // 表格列定义
  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (text: string, record: DownloadTask) => (
        <Space>
          <Text strong>{text}</Text>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewTaskDetail(record)}
          />
        </Space>
      ),
    },
    {
      title: '群组',
      dataIndex: 'group_id',
      key: 'group_id',
      render: (groupId: number) => {
        const group = groups.find(g => g.id === groupId);
        return group ? (
          <Tooltip title={group.title}>
            <Text ellipsis style={{ maxWidth: 120 }}>
              {group.title}
            </Text>
          </Tooltip>
        ) : groupId;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)} icon={getStatusIcon(status)}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number, record: DownloadTask) => (
        <div style={{ minWidth: 120 }}>
          <Progress
            percent={progress}
            size="small"
            status={record.status === 'failed' ? 'exception' : 'active'}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.downloaded_messages}/{record.total_messages || 0}
          </Text>
        </div>
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
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewTaskDetail(record)}
            />
          </Tooltip>
          <Tooltip title="查看日志">
            <Button
              size="small"
              icon={<FileTextOutlined />}
              onClick={() => handleViewTaskLogs(record)}
            />
          </Tooltip>
          
          {record.status === 'pending' && (
            <Tooltip title="立即执行">
              <Button
                size="small"
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => handleStartTask(record.id)}
              >
                执行
              </Button>
            </Tooltip>
          )}
          
          {record.status === 'running' && (
            <>
              <Tooltip title="暂停任务">
                <Button
                  size="small"
                  icon={<PauseCircleOutlined />}
                  onClick={() => handlePauseTask(record.id)}
                />
              </Tooltip>
              <Tooltip title="停止任务">
                <Button
                  size="small"
                  danger
                  icon={<StopOutlined />}
                  onClick={() => handleStopTask(record.id)}
                />
              </Tooltip>
            </>
          )}
          
          {record.status === 'paused' && (
            <Tooltip title="继续任务">
              <Button
                size="small"
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => handleStartTask(record.id)}
              />
            </Tooltip>
          )}
          
          {!['running'].includes(record.status) && (
            <Popconfirm
              title="确定删除这个任务吗？"
              onConfirm={() => handleDeleteTask(record.id)}
              okText="删除"
              cancelText="取消"
            >
              <Tooltip title="删除任务">
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  // 批量操作菜单
  const batchActionMenu = (
    <Menu>
      <Menu.Item key="start" icon={<PlayCircleOutlined />}>
        批量启动
      </Menu.Item>
      <Menu.Item key="pause" icon={<PauseCircleOutlined />}>
        批量暂停
      </Menu.Item>
      <Menu.Item key="stop" icon={<StopOutlined />}>
        批量停止
      </Menu.Item>
      <Menu.Divider />
      <Menu.Item key="delete" danger icon={<DeleteOutlined />}>
        批量删除
      </Menu.Item>
    </Menu>
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2}>任务管理</Title>
        <Space>
          <Text type="secondary">自动刷新</Text>
          <Switch
            checked={autoRefresh}
            onChange={setAutoRefresh}
            size="small"
          />
        </Space>
      </div>

      {/* 统计卡片 */}
      {taskStats && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="总任务"
                value={taskStats.total}
                prefix={<SettingOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="运行中"
                value={taskStats.running}
                prefix={<PlayCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="已完成"
                value={taskStats.completed}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#13c2c2' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="失败"
                value={taskStats.failed}
                prefix={<ExclamationCircleOutlined />}
                valueStyle={{ color: '#f5222d' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 操作栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 16 }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            创建任务
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadTasks}
            loading={loading}
          >
            刷新
          </Button>
          <Dropdown overlay={batchActionMenu}>
            <Button>
              批量操作 <DownOutlined />
            </Button>
          </Dropdown>
        </Space>

        {/* 过滤器 */}
        <Form
          form={filterForm}
          layout="inline"
          onFinish={handleFilter}
          style={{ marginBottom: 16 }}
        >
          <Form.Item name="group_id">
            <Select
              placeholder="选择群组"
              style={{ width: 200 }}
              allowClear
            >
              {groups.map(group => (
                <Option key={group.id} value={group.id}>
                  {group.title}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="status">
            <Select
              placeholder="任务状态"
              style={{ width: 120 }}
              allowClear
            >
              <Option value="pending">待执行</Option>
              <Option value="running">运行中</Option>
              <Option value="completed">已完成</Option>
              <Option value="failed">失败</Option>
              <Option value="paused">已暂停</Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SearchOutlined />}
              >
                筛选
              </Button>
              <Button onClick={handleResetFilter}>
                重置
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {/* 任务列表 */}
      <Card>
        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个任务`,
          }}
        />
      </Card>

      {/* 创建任务模态框 */}
      <Modal
        title="创建下载任务"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateTask}
        >
          <Form.Item
            name="name"
            label="任务名称"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="输入任务名称" />
          </Form.Item>
          <Form.Item
            name="group_id"
            label="目标群组"
            rules={[{ required: true, message: '请选择群组' }]}
          >
            <Select placeholder="选择群组">
              {groups.map(group => (
                <Option key={group.id} value={group.id}>
                  {group.title}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="rule_id"
            label="过滤规则"
            rules={[{ required: true, message: '请选择规则' }]}
          >
            <Select placeholder="选择规则">
              {rules.map(rule => (
                <Option key={rule.id} value={rule.id}>
                  {rule.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="download_path"
            label="下载路径"
            rules={[{ required: true, message: '请输入下载路径' }]}
          >
            <Input placeholder="输入下载路径，如: /downloads/task1" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                创建任务
              </Button>
              <Button onClick={() => {
                setCreateModalVisible(false);
                form.resetFields();
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 任务详情抽屉 */}
      <Drawer
        title="任务详情"
        placement="right"
        width={600}
        open={taskDetailVisible}
        onClose={() => setTaskDetailVisible(false)}
      >
        {selectedTask && (
          <div>
            <Card title="基本信息" style={{ marginBottom: 16 }}>
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Text strong>任务ID: </Text>
                  <Text>{selectedTask.id}</Text>
                </Col>
                <Col span={12}>
                  <Text strong>任务名称: </Text>
                  <Text>{selectedTask.name}</Text>
                </Col>
                <Col span={12}>
                  <Text strong>群组ID: </Text>
                  <Text>{selectedTask.group_id}</Text>
                </Col>
                <Col span={12}>
                  <Text strong>规则ID: </Text>
                  <Text>{selectedTask.rule_id}</Text>
                </Col>
                <Col span={12}>
                  <Text strong>状态: </Text>
                  <Tag color={getStatusColor(selectedTask.status)} icon={getStatusIcon(selectedTask.status)}>
                    {selectedTask.status.toUpperCase()}
                  </Tag>
                </Col>
                <Col span={12}>
                  <Text strong>进度: </Text>
                  <Text>{selectedTask.progress}%</Text>
                </Col>
                <Col span={24}>
                  <Text strong>下载路径: </Text>
                  <Text code>{selectedTask.download_path}</Text>
                </Col>
              </Row>
            </Card>

            <Card title="执行统计" style={{ marginBottom: 16 }}>
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Statistic
                    title="总消息数"
                    value={selectedTask.total_messages || 0}
                    prefix={<FileTextOutlined />}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="已下载"
                    value={selectedTask.downloaded_messages || 0}
                    prefix={<CheckCircleOutlined />}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Col>
              </Row>
              <Progress
                percent={selectedTask.progress}
                status={selectedTask.status === 'failed' ? 'exception' : 'active'}
                style={{ marginTop: 16 }}
              />
            </Card>

            <Card title="时间信息">
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <div>
                  <Text strong>创建时间: </Text>
                  <Text>{new Date(selectedTask.created_at).toLocaleString()}</Text>
                </div>
                {selectedTask.updated_at && (
                  <div>
                    <Text strong>更新时间: </Text>
                    <Text>{new Date(selectedTask.updated_at).toLocaleString()}</Text>
                  </div>
                )}
                {selectedTask.completed_at && (
                  <div>
                    <Text strong>完成时间: </Text>
                    <Text>{new Date(selectedTask.completed_at).toLocaleString()}</Text>
                  </div>
                )}
                {selectedTask.error_message && (
                  <Alert
                    message="错误信息"
                    description={selectedTask.error_message}
                    type="error"
                    showIcon
                  />
                )}
              </Space>
            </Card>
          </div>
        )}
      </Drawer>

      {/* 任务日志抽屉 */}
      <Drawer
        title="任务执行日志"
        placement="right"
        width={800}
        open={taskLogsVisible}
        onClose={() => setTaskLogsVisible(false)}
      >
        {selectedTask && (
          <div>
            <Alert
              message={`任务 "${selectedTask.name}" 的执行日志`}
              type="info"
              style={{ marginBottom: 16 }}
              showIcon
            />
            
            <Spin spinning={logsLoading}>
              {taskLogs.length > 0 ? (
                <List
                  dataSource={taskLogs}
                  renderItem={(log) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={
                          <Badge
                            color={
                              log.level === 'ERROR' ? 'red' :
                              log.level === 'WARNING' ? 'orange' :
                              log.level === 'INFO' ? 'blue' : 'default'
                            }
                          />
                        }
                        title={
                          <Space>
                            <Tag color={
                              log.level === 'ERROR' ? 'red' :
                              log.level === 'WARNING' ? 'orange' :
                              log.level === 'INFO' ? 'blue' : 'default'
                            }>
                              {log.level}
                            </Tag>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {new Date(log.created_at || log.timestamp).toLocaleString()}
                            </Text>
                          </Space>
                        }
                        description={
                          <div>
                            <Text>{log.message}</Text>
                            {log.details && (
                              <div style={{ marginTop: 8 }}>
                                <Text code style={{ fontSize: 12 }}>
                                  {JSON.stringify(log.details, null, 2)}
                                </Text>
                              </div>
                            )}
                          </div>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="暂无日志数据" />
              )}
            </Spin>
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default TaskManagement;