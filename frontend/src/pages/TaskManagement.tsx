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
  Menu,
  InputNumber,
  Collapse,
  TimePicker
} from 'antd';
import dayjs from 'dayjs';
import { useIsMobile } from '../hooks/useMobileGestures';
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
  DownOutlined,
  EditOutlined
} from '@ant-design/icons';
import { taskApi, telegramApi, ruleApi, logApi } from '../services/apiService';
import { DownloadTask, TelegramGroup, FilterRule, LogEntry, TaskScheduleForm, ScheduleConfig } from '../types';

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
  const isMobile = useIsMobile();

  // 状态管理
  const [tasks, setTasks] = useState<DownloadTask[]>([]);
  const [groups, setGroups] = useState<TelegramGroup[]>([]);
  const [rules, setRules] = useState<FilterRule[]>([]);
  const [taskStats, setTaskStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [selectedTask, setSelectedTask] = useState<DownloadTask | null>(null);

  // 模态框状态
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [taskDetailVisible, setTaskDetailVisible] = useState(false);
  const [taskLogsVisible, setTaskLogsVisible] = useState(false);

  // 表单和过滤
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();
  const [filterForm] = Form.useForm();

  // 调度表单状态
  const [taskType, setTaskType] = useState<'once' | 'recurring'>('once');
  const [scheduleType, setScheduleType] = useState<string>('');
  const [editTaskType, setEditTaskType] = useState<'once' | 'recurring'>('once');
  const [editScheduleType, setEditScheduleType] = useState<string>('');

  // 重置调度表单状态
  const resetScheduleState = () => {
    setTaskType('once');
    setScheduleType('');
  };

  const resetEditScheduleState = () => {
    setEditTaskType('once');
    setEditScheduleType('');
  };
  const [filters, setFilters] = useState<any>({});
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [operatingTasks, setOperatingTasks] = useState<Set<number>>(new Set());

  // 批量操作相关状态
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchOperating, setBatchOperating] = useState(false);

  // 日志相关
  const [taskLogs, setTaskLogs] = useState<LogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [systemStatus, setSystemStatus] = useState<{
    isTaskServiceAvailable: boolean;
    message?: string;
  }>({ isTaskServiceAvailable: true });

  // 加载数据
  const loadTasks = useCallback(async () => {
    try {
      setLoading(true);
      console.log('开始加载任务数据，过滤条件:', filters);
      const [tasksData, statsData] = await Promise.all([
        taskApi.getTasks(filters),
        taskApi.getTaskStats()
      ]);
      console.log('任务数据加载成功:', tasksData);
      console.log('任务统计加载成功:', statsData);
      setTasks(tasksData);
      setTaskStats(statsData);
    } catch (error: any) {
      console.error('加载任务失败，错误详情:', error);
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
      console.log('开始加载规则数据...');
      const rulesData = await ruleApi.getRules();
      console.log('规则数据加载成功:', rulesData);
      setRules(rulesData);
    } catch (error: any) {
      message.error(`加载规则失败: ${error.message}`);
      console.error('规则加载错误详情:', error);
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
      setOperatingTasks(prev => new Set(prev).add(taskId));
      setSystemStatus({ isTaskServiceAvailable: true });
      await taskApi.startTask(taskId);
      message.success('任务启动成功');
      loadTasks();
    } catch (error: any) {
      console.error('启动任务失败:', error);

      // 检查是否是服务不可用的错误
      if (error.message.includes('服务不可用') || error.message.includes('连接')) {
        setSystemStatus({
          isTaskServiceAvailable: false,
          message: '任务执行服务暂时不可用，可能正在使用模拟模式'
        });
        message.warning(`任务启动: ${error.message}，已切换到模拟模式`);
      } else {
        message.error(`启动任务失败: ${error.message}`);
      }
    } finally {
      setOperatingTasks(prev => {
        const newSet = new Set(prev);
        newSet.delete(taskId);
        return newSet;
      });
    }
  };

  const handlePauseTask = async (taskId: number) => {
    try {
      setOperatingTasks(prev => new Set(prev).add(taskId));
      await taskApi.pauseTask(taskId);
      message.success('任务暂停成功');
      loadTasks();
    } catch (error: any) {
      console.error('暂停任务失败:', error);
      if (error.message.includes('服务不可用') || error.message.includes('连接')) {
        message.warning(`任务暂停: ${error.message}，使用模拟模式`);
      } else {
        message.error(`暂停任务失败: ${error.message}`);
      }
    } finally {
      setOperatingTasks(prev => {
        const newSet = new Set(prev);
        newSet.delete(taskId);
        return newSet;
      });
    }
  };

  const handleStopTask = async (taskId: number) => {
    try {
      setOperatingTasks(prev => new Set(prev).add(taskId));
      await taskApi.stopTask(taskId);
      message.success('任务停止成功');
      loadTasks();
    } catch (error: any) {
      console.error('停止任务失败:', error);
      if (error.message.includes('服务不可用') || error.message.includes('连接')) {
        message.warning(`任务停止: ${error.message}，使用模拟模式`);
      } else {
        message.error(`停止任务失败: ${error.message}`);
      }
    } finally {
      setOperatingTasks(prev => {
        const newSet = new Set(prev);
        newSet.delete(taskId);
        return newSet;
      });
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    try {
      setOperatingTasks(prev => new Set(prev).add(taskId));
      await taskApi.deleteTask(taskId);
      message.success('任务删除成功');
      loadTasks();
    } catch (error: any) {
      message.error(`删除任务失败: ${error.message}`);
    } finally {
      setOperatingTasks(prev => {
        const newSet = new Set(prev);
        newSet.delete(taskId);
        return newSet;
      });
    }
  };

  // 批量操作处理函数
  const handleBatchOperation = async (action: string) => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要操作的任务');
      return;
    }

    setBatchOperating(true);
    const selectedTaskIds = selectedRowKeys as number[];
    const successTasks: number[] = [];
    const failedTasks: number[] = [];

    try {
      for (const taskId of selectedTaskIds) {
        try {
          switch (action) {
            case 'start':
              await taskApi.startTask(taskId);
              successTasks.push(taskId);
              break;
            case 'pause':
              await taskApi.pauseTask(taskId);
              successTasks.push(taskId);
              break;
            case 'stop':
              await taskApi.stopTask(taskId);
              successTasks.push(taskId);
              break;
            case 'delete':
              await taskApi.deleteTask(taskId);
              successTasks.push(taskId);
              break;
          }
        } catch (error) {
          console.error(`批量操作 ${action} 失败，任务ID: ${taskId}`, error);
          failedTasks.push(taskId);
        }
      }

      // 显示结果
      if (successTasks.length > 0) {
        const actionName = {
          start: '启动',
          pause: '暂停',
          stop: '停止',
          delete: '删除'
        }[action] || action;
        message.success(`成功${actionName}了 ${successTasks.length} 个任务`);
      }

      if (failedTasks.length > 0) {
        const actionName = {
          start: '启动',
          pause: '暂停',
          stop: '停止',
          delete: '删除'
        }[action] || action;
        message.error(`${failedTasks.length} 个任务${actionName}失败`);
      }

      // 清空选择并重新加载
      setSelectedRowKeys([]);
      loadTasks();
    } finally {
      setBatchOperating(false);
    }
  };

  // 行选择配置
  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[]) => {
      setSelectedRowKeys(newSelectedRowKeys);
    },
    onSelectAll: (selected: boolean, selectedRows: DownloadTask[], changeRows: DownloadTask[]) => {
      if (selected) {
        // 选中所有可操作的任务
        const allSelectableKeys = tasks.map(task => task.id);
        setSelectedRowKeys(allSelectableKeys);
      } else {
        setSelectedRowKeys([]);
      }
    },
    onSelect: (record: DownloadTask, selected: boolean) => {
      if (selected) {
        setSelectedRowKeys(prev => [...prev, record.id]);
      } else {
        setSelectedRowKeys(prev => prev.filter(key => key !== record.id));
      }
    },
    getCheckboxProps: (record: DownloadTask) => ({
      disabled: operatingTasks.has(record.id), // 正在操作的任务不能选择
    }),
  };

  const handleCreateTask = async (values: any) => {
    try {
      console.log('开始创建任务，原始表单数据:', values);
      // 处理时间范围数据
      const taskData = { ...values };
      if (values.time_range && values.time_range.length >= 1) {
        // 开始时间（必填）
        if (values.time_range[0]) {
          taskData.date_from = values.time_range[0].toISOString();
        }
        // 结束时间（可选）
        if (values.time_range[1]) {
          taskData.date_to = values.time_range[1].toISOString();
        }
        delete taskData.time_range;
      }

      // 处理调度配置数据
      if (values.task_type === 'recurring' && values.schedule_type && values.schedule_config) {
        // 处理时间字段 - 将moment对象转换为字符串
        if (values.schedule_config.time) {
          taskData.schedule_config = {
            ...values.schedule_config,
            time: values.schedule_config.time.format('HH:mm')
          };
        }
      } else if (values.task_type === 'once') {
        // 一次性任务，清除调度相关字段
        taskData.task_type = 'once';
        delete taskData.schedule_type;
        delete taskData.schedule_config;
        delete taskData.max_runs;
      }

      console.log('处理后的任务数据:', taskData);

      const result = await taskApi.createTask(taskData);
      console.log('任务创建成功，返回数据:', result);
      message.success('任务创建成功');
      setCreateModalVisible(false);
      form.resetFields();
      resetScheduleState();
      loadTasks();
    } catch (error: any) {
      console.error('创建任务失败，错误详情:', error);
      message.error(`创建任务失败: ${error.message}`);
    }
  };

  const handleEditTask = (task: DownloadTask) => {
    console.log('开始编辑任务:', task);
    setSelectedTask(task);
    
    // 设置表单数据
    const formData: any = {
      name: task.name,
      group_id: task.group_id,
      rule_ids: task.rules ? task.rules.map(r => r.rule_id) : [],
      download_path: task.download_path,
      task_type: task.task_type || 'once',
      schedule_type: task.schedule_type,
      schedule_config: task.schedule_config,
      max_runs: task.max_runs
    };

    // 处理时间范围
    if (task.date_from || task.date_to) {
      const timeRange = [];
      if (task.date_from) {
        timeRange.push(dayjs(task.date_from));
      }
      if (task.date_to) {
        timeRange.push(dayjs(task.date_to));
      }
      formData.time_range = timeRange;
    }

    // 处理调度配置中的时间
    if (task.schedule_config && task.schedule_config.time) {
      formData.schedule_config = {
        ...task.schedule_config,
        time: dayjs(task.schedule_config.time, 'HH:mm')
      };
    }

    editForm.setFieldsValue(formData);
    setEditTaskType(task.task_type || 'once');
    setEditScheduleType(task.schedule_type || '');
    setEditModalVisible(true);
  };

  const handleUpdateTask = async (values: any) => {
    if (!selectedTask) return;
    
    try {
      console.log('开始更新任务，原始表单数据:', values);
      // 处理时间范围数据
      const taskData = { ...values };
      if (values.time_range && values.time_range.length >= 1) {
        // 开始时间（必填）
        if (values.time_range[0]) {
          taskData.date_from = values.time_range[0].toISOString();
        }
        // 结束时间（可选）
        if (values.time_range[1]) {
          taskData.date_to = values.time_range[1].toISOString();
        }
        delete taskData.time_range;
      }

      // 处理调度配置数据
      if (values.task_type === 'recurring' && values.schedule_type && values.schedule_config) {
        // 处理时间字段 - 将moment对象转换为字符串
        if (values.schedule_config.time) {
          taskData.schedule_config = {
            ...values.schedule_config,
            time: values.schedule_config.time.format('HH:mm')
          };
        }
      } else if (values.task_type === 'once') {
        // 一次性任务，清除调度相关字段
        taskData.task_type = 'once';
        taskData.schedule_type = null;
        taskData.schedule_config = null;
        taskData.max_runs = null;
      }

      console.log('处理后的任务数据:', taskData);

      const result = await taskApi.updateTask(selectedTask.id, taskData);
      console.log('任务更新成功，返回数据:', result);
      message.success('任务更新成功');
      setEditModalVisible(false);
      editForm.resetFields();
      resetEditScheduleState();
      setSelectedTask(null);
      loadTasks();
    } catch (error: any) {
      console.error('更新任务失败，错误详情:', error);
      message.error(`更新任务失败: ${error.message}`);
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
  }, []); // 移除函数依赖，只在组件首次加载时执行

  // 表格列定义
  const columns = [
    ...(!isMobile ? [{
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    }] : []),
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (text: string, record: DownloadTask) => (
        <div>
          <div>
            <Text strong>{text}</Text>
            {!isMobile && (
              <Button
                type="link"
                size="small"
                icon={<EyeOutlined />}
                onClick={() => handleViewTaskDetail(record)}
              />
            )}
          </div>
          {isMobile && (
            <div style={{ fontSize: '12px', color: '#666', marginTop: 4 }}>
              <div>
                <Text type="secondary">ID: {record.id}</Text>
                <Text type="secondary" style={{ marginLeft: 8 }}>
                  {groups.find(g => g.id === record.group_id)?.title || '未知群组'}
                </Text>
              </div>
              <div style={{ marginTop: 2 }}>
                <Text type="secondary">
                  {!record.task_type || record.task_type === 'once' ? '一次性任务' :
                    record.schedule_type ? `循环任务 (${{ 'interval': '间隔', 'daily': '每日', 'weekly': '每周', 'monthly': '每月', 'cron': 'Cron' }[record.schedule_type] || record.schedule_type
                      })` : '循环任务'}
                </Text>
                {record.next_run_time && record.status === 'pending' && (
                  <Text type="secondary" style={{ marginLeft: 8 }}>
                    下次: {new Date(record.next_run_time).toLocaleString().split(' ')[1]}
                  </Text>
                )}
              </div>
            </div>
          )}
        </div>
      ),
    },
    ...(!isMobile ? [{
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
    }] : []),
    {
      title: isMobile ? '状态/进度' : '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string, record: DownloadTask) => (
        <div>
          <div style={{ marginBottom: isMobile ? 8 : 0 }}>
            <Tag color={getStatusColor(status)} icon={getStatusIcon(status)}>
              {isMobile ? status : status.toUpperCase()}
            </Tag>
          </div>
          {isMobile && (
            <div style={{ minWidth: 100 }}>
              <Progress
                percent={record.progress}
                size="small"
                status={record.status === 'failed' ? 'exception' : 'active'}
              />
              <Text type="secondary" style={{ fontSize: 11 }}>
                {record.downloaded_messages}/{record.total_messages || 0}
              </Text>
            </div>
          )}
        </div>
      ),
    },
    ...(!isMobile ? [{
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
    }] : []),
    ...(!isMobile ? [{
      title: '时间范围',
      key: 'time_range',
      width: 180,
      render: (text: any, record: DownloadTask) => {
        if (record.date_from || record.date_to) {
          return (
            <div style={{ fontSize: 12, lineHeight: '1.2' }}>
              <div>开始: {record.date_from ? new Date(record.date_from).toLocaleString() : '不限'}</div>
              <div>结束: {record.date_to ? new Date(record.date_to).toLocaleString() : '一直有效'}</div>
            </div>
          );
        }
        return <Text type="secondary">无限制</Text>;
      },
    }] : []),
    ...(!isMobile ? [{
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (text: string) => (
        <Text style={{ fontSize: 12 }}>
          {new Date(text).toLocaleString()}
        </Text>
      ),
    }] : []),
    ...(!isMobile ? [{
      title: '调度信息',
      key: 'schedule_info',
      width: 200,
      render: (text: string, record: DownloadTask) => {
        const renderScheduleType = () => {
          if (!record.task_type || record.task_type === 'once') {
            return <Text type="secondary">一次性任务</Text>;
          }

          if (record.task_type === 'recurring' && record.schedule_type) {
            const scheduleTypeMap: Record<string, string> = {
              'interval': '间隔执行',
              'daily': '每日执行',
              'weekly': '每周执行',
              'monthly': '每月执行',
              'cron': 'Cron表达式'
            };

            return (
              <div style={{ fontSize: 12 }}>
                <div>
                  <Tag color="blue">
                    {scheduleTypeMap[record.schedule_type] || record.schedule_type}
                  </Tag>
                </div>
                {record.run_count !== undefined && record.max_runs && (
                  <div style={{ color: '#666', marginTop: 2 }}>
                    {record.run_count}/{record.max_runs} 次
                  </div>
                )}
              </div>
            );
          }

          return <Text type="secondary">循环任务</Text>;
        };

        const renderNextRunTime = () => {
          if (record.status === 'completed') {
            return <Text type="secondary">已完成</Text>;
          }
          if (record.status === 'failed') {
            return <Text type="danger">执行失败</Text>;
          }
          if (record.status === 'running') {
            return <Text type="success">正在执行</Text>;
          }
          if (record.status === 'paused') {
            return <Text type="warning">已暂停</Text>;
          }

          if (record.next_run_time) {
            return (
              <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
                下次: {new Date(record.next_run_time).toLocaleString()}
              </div>
            );
          }

          return record.task_type === 'once' ?
            <Text type="secondary" style={{ fontSize: 11 }}>待执行</Text> :
            <Text type="secondary" style={{ fontSize: 11 }}>待安排</Text>;
        };

        return (
          <div>
            {renderScheduleType()}
            {renderNextRunTime()}
          </div>
        );
      },
    }] : []),
    {
      title: '操作',
      key: 'actions',
      width: isMobile ? 100 : undefined,
      render: (_: any, record: DownloadTask) => (
        <Space size="small" direction={isMobile ? "vertical" : "horizontal"}>
          {isMobile ? (
            <Dropdown
              overlay={
                <Menu>
                  <Menu.Item key="detail" icon={<EyeOutlined />} onClick={() => handleViewTaskDetail(record)}>
                    查看详情
                  </Menu.Item>
                  <Menu.Item key="logs" icon={<FileTextOutlined />} onClick={() => handleViewTaskLogs(record)}>
                    查看日志
                  </Menu.Item>
                  {!['running'].includes(record.status) && (
                    <Menu.Item key="edit" icon={<EditOutlined />} onClick={() => handleEditTask(record)}>
                      编辑任务
                    </Menu.Item>
                  )}
                  {record.status === 'pending' && (
                    <Menu.Item
                      key="start"
                      icon={<PlayCircleOutlined />}
                      onClick={() => handleStartTask(record.id)}
                      disabled={operatingTasks.has(record.id)}
                    >
                      {operatingTasks.has(record.id) ? '启动中...' : '立即执行'}
                    </Menu.Item>
                  )}
                  {record.status === 'running' && (
                    <>
                      <Menu.Item
                        key="pause"
                        icon={<PauseCircleOutlined />}
                        onClick={() => handlePauseTask(record.id)}
                        disabled={operatingTasks.has(record.id)}
                      >
                        {operatingTasks.has(record.id) ? '暂停中...' : '暂停任务'}
                      </Menu.Item>
                      <Menu.Item
                        key="stop"
                        icon={<StopOutlined />}
                        onClick={() => handleStopTask(record.id)}
                        disabled={operatingTasks.has(record.id)}
                      >
                        {operatingTasks.has(record.id) ? '停止中...' : '停止任务'}
                      </Menu.Item>
                    </>
                  )}
                  {record.status === 'paused' && (
                    <Menu.Item
                      key="resume"
                      icon={<PlayCircleOutlined />}
                      onClick={() => handleStartTask(record.id)}
                      disabled={operatingTasks.has(record.id)}
                    >
                      {operatingTasks.has(record.id) ? '恢复中...' : '继续任务'}
                    </Menu.Item>
                  )}
                  {!['running'].includes(record.status) && (
                    <Menu.Item key="delete" danger icon={<DeleteOutlined />}>
                      <Popconfirm
                        title="确定删除这个任务吗？"
                        onConfirm={() => handleDeleteTask(record.id)}
                        okText="删除"
                        cancelText="取消"
                      >
                        删除任务
                      </Popconfirm>
                    </Menu.Item>
                  )}
                </Menu>
              }
              trigger={['click']}
            >
              <Button size="small" icon={<SettingOutlined />}>
                操作
              </Button>
            </Dropdown>
          ) : (
            <>
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

              {!['running'].includes(record.status) && (
                <Tooltip title="编辑任务">
                  <Button
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => handleEditTask(record)}
                  />
                </Tooltip>
              )}

              {record.status === 'pending' && (
                <Tooltip title="立即执行">
                  <Button
                    size="small"
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    loading={operatingTasks.has(record.id)}
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
                      loading={operatingTasks.has(record.id)}
                      onClick={() => handlePauseTask(record.id)}
                    />
                  </Tooltip>
                  <Tooltip title="停止任务">
                    <Button
                      size="small"
                      danger
                      icon={<StopOutlined />}
                      loading={operatingTasks.has(record.id)}
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
                    loading={operatingTasks.has(record.id)}
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
                      loading={operatingTasks.has(record.id)}
                    />
                  </Tooltip>
                </Popconfirm>
              )}
            </>
          )}
        </Space>
      ),
    },
  ];

  // 批量操作菜单
  const batchActionMenu = (
    <Menu onClick={({ key }) => {
      if (key === 'delete') {
        Modal.confirm({
          title: '确认批量删除',
          content: `确定要删除选中的 ${selectedRowKeys.length} 个任务吗？此操作不可撤销。`,
          okText: '删除',
          okType: 'danger',
          cancelText: '取消',
          onOk: () => handleBatchOperation('delete'),
        });
      } else {
        handleBatchOperation(key);
      }
    }}>
      <Menu.Item key="start" icon={<PlayCircleOutlined />} disabled={batchOperating}>
        批量启动 {selectedRowKeys.length > 0 && `(${selectedRowKeys.length})`}
      </Menu.Item>
      <Menu.Item key="pause" icon={<PauseCircleOutlined />} disabled={batchOperating}>
        批量暂停 {selectedRowKeys.length > 0 && `(${selectedRowKeys.length})`}
      </Menu.Item>
      <Menu.Item key="stop" icon={<StopOutlined />} disabled={batchOperating}>
        批量停止 {selectedRowKeys.length > 0 && `(${selectedRowKeys.length})`}
      </Menu.Item>
      <Menu.Divider />
      <Menu.Item key="delete" danger icon={<DeleteOutlined />} disabled={batchOperating}>
        批量删除 {selectedRowKeys.length > 0 && `(${selectedRowKeys.length})`}
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

      {/* 系统状态指示器 */}
      {!systemStatus.isTaskServiceAvailable && (
        <Alert
          message="系统提示"
          description={systemStatus.message || "任务执行服务暂时不可用，当前使用模拟模式进行测试"}
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" onClick={() => setSystemStatus({ isTaskServiceAvailable: true })}>
              知道了
            </Button>
          }
        />
      )}

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

          {/* 快捷执行按钮 */}
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => {
              const pendingTasks = tasks.filter(task => task.status === 'pending').map(task => task.id);
              if (pendingTasks.length === 0) {
                message.info('没有待执行的任务');
                return;
              }
              setSelectedRowKeys(pendingTasks);
              handleBatchOperation('start');
            }}
            disabled={!tasks.some(task => task.status === 'pending') || batchOperating}
          >
            启动所有待执行任务
          </Button>

          <Button
            icon={<PauseCircleOutlined />}
            onClick={() => {
              const runningTasks = tasks.filter(task => task.status === 'running').map(task => task.id);
              if (runningTasks.length === 0) {
                message.info('没有运行中的任务');
                return;
              }
              setSelectedRowKeys(runningTasks);
              handleBatchOperation('pause');
            }}
            disabled={!tasks.some(task => task.status === 'running') || batchOperating}
          >
            暂停所有运行中任务
          </Button>

          <Dropdown overlay={batchActionMenu}>
            <Button
              disabled={selectedRowKeys.length === 0}
              loading={batchOperating}
            >
              批量操作 {selectedRowKeys.length > 0 && `(${selectedRowKeys.length})`} <DownOutlined />
            </Button>
          </Dropdown>

          {selectedRowKeys.length > 0 && (
            <Button
              size="small"
              onClick={() => setSelectedRowKeys([])}
            >
              取消选择
            </Button>
          )}
        </Space>

        {/* 过滤器 */}
        <Form
          form={filterForm}
          layout={isMobile ? "vertical" : "inline"}
          onFinish={handleFilter}
          style={{ marginBottom: 16 }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={8}>
              <Form.Item name="group_id" label={isMobile ? "选择群组" : undefined}>
                <Select
                  placeholder="选择群组"
                  style={{ width: '100%' }}
                  allowClear
                  showSearch
                  filterOption={(input, option) => {
                    if (!option || !input) return false;
                    const label = option.label || option.children;
                    if (typeof label === 'string') {
                      return label.toLowerCase().includes(input.toLowerCase());
                    }
                    return false;
                  }}
                >
                  {groups.map(group => (
                    <Option key={group.id} value={group.id}>
                      {group.title}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item name="status" label={isMobile ? "任务状态" : undefined}>
                <Select
                  placeholder="任务状态"
                  style={{ width: '100%' }}
                  allowClear
                >
                  <Option value="pending">待执行</Option>
                  <Option value="running">运行中</Option>
                  <Option value="completed">已完成</Option>
                  <Option value="failed">失败</Option>
                  <Option value="paused">已暂停</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={24} md={8}>
              <Form.Item label={isMobile ? " " : undefined}>
                <Space style={{ width: '100%', justifyContent: isMobile ? 'center' : 'flex-start' }}>
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
            </Col>
          </Row>
        </Form>
      </Card>

      {/* 任务列表 */}
      <Card>
        {selectedRowKeys.length > 0 && (
          <Alert
            message={`已选择 ${selectedRowKeys.length} 个任务`}
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            action={
              <Space>
                <Button size="small" onClick={() => setSelectedRowKeys([])}>
                  取消选择
                </Button>
              </Space>
            }
          />
        )}

        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="id"
          loading={loading}
          rowSelection={rowSelection}
          scroll={isMobile ? { x: 600 } : undefined}
          pagination={{
            showSizeChanger: !isMobile,
            showQuickJumper: !isMobile,
            showTotal: (total) => `共 ${total} 个任务`,
            pageSize: isMobile ? 5 : 10,
            size: isMobile ? 'small' : 'default',
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
          resetScheduleState();
        }}
        footer={null}
        width={isMobile ? '95%' : 600}
        style={isMobile ? { top: 20 } : undefined}
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
            <Select
              placeholder="选择群组"
              showSearch
              filterOption={(input, option) => {
                if (!option || !input) return false;
                const label = option.label || option.children;
                if (typeof label === 'string') {
                  return label.toLowerCase().includes(input.toLowerCase());
                }
                return false;
              }}
              optionFilterProp="children"
            >
              {groups.map(group => (
                <Option key={group.id} value={group.id}>
                  {group.title}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="rule_ids"
            label="过滤规则"
            rules={[{ required: true, message: '请选择至少一个规则' }]}
          >
            <Select 
              mode="multiple" 
              placeholder="选择规则（可多选）"
              showSearch
              filterOption={(input, option) =>
                String(option?.children || '').toLowerCase().includes(input.toLowerCase())
              }
            >
              {rules.map(rule => (
                <Option key={rule.id} value={rule.id}>
                  {rule.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="time_range"
            label="时间范围过滤"
            help="设置消息的时间范围。结束时间可不填，表示从开始时间一直有效"
          >
            <RangePicker
              showTime
              placeholder={['开始时间', '结束时间(可选)']}
              style={{ width: '100%' }}
              allowEmpty={[false, true]}
            />
          </Form.Item>
          <Form.Item
            name="download_path"
            label="下载路径"
            rules={[{ required: true, message: '请输入下载路径' }]}
          >
            <Input placeholder="输入下载路径，如: /downloads/task1" />
          </Form.Item>

          {/* 调度配置 */}
          <Collapse size="small" ghost>
            <Collapse.Panel header="调度配置" key="schedule">
              <Form.Item
                name="task_type"
                label="任务类型"
                initialValue="once"
              >
                <Select
                  value={taskType}
                  onChange={(value) => {
                    setTaskType(value);
                    if (value === 'once') {
                      setScheduleType('');
                      form.setFieldsValue({
                        schedule_type: undefined,
                        schedule_config: undefined,
                        max_runs: undefined
                      });
                    }
                  }}
                >
                  <Option value="once">一次性任务</Option>
                  <Option value="recurring">循环任务</Option>
                </Select>
              </Form.Item>

              {taskType === 'recurring' && (
                <>
                  <Form.Item
                    name="schedule_type"
                    label="调度类型"
                    rules={[{ required: taskType === 'recurring', message: '请选择调度类型' }]}
                  >
                    <Select
                      placeholder="选择调度类型"
                      value={scheduleType}
                      onChange={setScheduleType}
                    >
                      <Option value="interval">间隔执行</Option>
                      <Option value="daily">每日执行</Option>
                      <Option value="weekly">每周执行</Option>
                      <Option value="monthly">每月执行</Option>
                      <Option value="cron">Cron表达式</Option>
                    </Select>
                  </Form.Item>

                  {scheduleType === 'interval' && (
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          name={['schedule_config', 'interval']}
                          label="间隔数值"
                          rules={[{ required: true, message: '请输入间隔数值' }]}
                        >
                          <InputNumber min={1} placeholder="1" style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          name={['schedule_config', 'unit']}
                          label="时间单位"
                          initialValue="hours"
                        >
                          <Select>
                            <Option value="minutes">分钟</Option>
                            <Option value="hours">小时</Option>
                            <Option value="days">天</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                    </Row>
                  )}

                  {scheduleType === 'daily' && (
                    <Form.Item
                      name={['schedule_config', 'time']}
                      label="执行时间"
                      rules={[{ required: true, message: '请选择执行时间' }]}
                    >
                      <TimePicker format="HH:mm" placeholder="选择时间" style={{ width: '100%' }} />
                    </Form.Item>
                  )}

                  {scheduleType === 'weekly' && (
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          name={['schedule_config', 'day_of_week']}
                          label="星期几"
                          rules={[{ required: true, message: '请选择星期几' }]}
                        >
                          <Select placeholder="选择星期几">
                            <Option value={1}>星期一</Option>
                            <Option value={2}>星期二</Option>
                            <Option value={3}>星期三</Option>
                            <Option value={4}>星期四</Option>
                            <Option value={5}>星期五</Option>
                            <Option value={6}>星期六</Option>
                            <Option value={0}>星期日</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          name={['schedule_config', 'time']}
                          label="执行时间"
                          rules={[{ required: true, message: '请选择执行时间' }]}
                        >
                          <TimePicker format="HH:mm" placeholder="选择时间" style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>
                  )}

                  {scheduleType === 'monthly' && (
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          name={['schedule_config', 'day_of_month']}
                          label="每月第几天"
                          rules={[{ required: true, message: '请输入日期' }]}
                        >
                          <InputNumber min={1} max={31} placeholder="1" style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          name={['schedule_config', 'time']}
                          label="执行时间"
                          rules={[{ required: true, message: '请选择执行时间' }]}
                        >
                          <TimePicker format="HH:mm" placeholder="选择时间" style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>
                  )}

                  {scheduleType === 'cron' && (
                    <Form.Item
                      name={['schedule_config', 'cron_expression']}
                      label="Cron表达式"
                      rules={[{ required: true, message: '请输入Cron表达式' }]}
                      help="格式: 秒 分 时 日 月 周"
                    >
                      <Input placeholder="0 0 9 * * *" />
                    </Form.Item>
                  )}

                  <Form.Item
                    name="max_runs"
                    label="最大执行次数"
                    help="留空表示无限制"
                  >
                    <InputNumber min={1} placeholder="不限制" style={{ width: '100%' }} />
                  </Form.Item>
                </>
              )}
            </Collapse.Panel>
          </Collapse>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                创建任务
              </Button>
              <Button onClick={() => {
                setCreateModalVisible(false);
                form.resetFields();
                resetScheduleState();
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑任务模态框 */}
      <Modal
        title="编辑下载任务"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          editForm.resetFields();
          resetEditScheduleState();
          setSelectedTask(null);
        }}
        footer={null}
        width={isMobile ? '95%' : 600}
        style={isMobile ? { top: 20 } : undefined}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleUpdateTask}
        >
          <Form.Item
            name="name"
            label="任务名称"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="输入任务名称" />
          </Form.Item>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="group_id"
                label="目标群组"
                rules={[{ required: true, message: '请选择群组' }]}
              >
                <Select 
                  placeholder="选择群组"
                  showSearch
                  filterOption={(input, option) =>
                    String(option?.children || '').toLowerCase().includes(input.toLowerCase())
                  }
                >
                  {groups.map(group => (
                    <Option key={group.id} value={group.id}>
                      {group.title}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="rule_ids"
                label="过滤规则"
                rules={[{ required: true, message: '请选择至少一个规则' }]}
              >
                <Select 
                  mode="multiple"
                  placeholder="选择规则（可多选）"
                  showSearch
                  filterOption={(input, option) =>
                    String(option?.children || '').toLowerCase().includes(input.toLowerCase())
                  }
                >
                  {rules.map(rule => (
                    <Option key={rule.id} value={rule.id}>
                      {rule.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item
            name="time_range"
            label="时间范围过滤"
            help="设置消息的时间范围。结束时间可不填，表示从开始时间一直有效"
          >
            <RangePicker
              showTime
              placeholder={['开始时间', '结束时间(可选)']}
              style={{ width: '100%' }}
              allowEmpty={[false, true]}
            />
          </Form.Item>
          <Form.Item
            name="download_path"
            label="下载路径"
            rules={[{ required: true, message: '请输入下载路径' }]}
          >
            <Input placeholder="输入下载路径，如: /downloads/task1" />
          </Form.Item>

          {/* 调度配置 */}
          <Collapse size="small" ghost>
            <Collapse.Panel header="调度配置" key="schedule">
              <Form.Item
                name="task_type"
                label="任务类型"
                initialValue="once"
              >
                <Select
                  value={editTaskType}
                  onChange={(value) => {
                    setEditTaskType(value);
                    if (value === 'once') {
                      setEditScheduleType('');
                      editForm.setFieldsValue({
                        schedule_type: undefined,
                        schedule_config: undefined,
                        max_runs: undefined
                      });
                    }
                  }}
                >
                  <Option value="once">一次性任务</Option>
                  <Option value="recurring">循环任务</Option>
                </Select>
              </Form.Item>

              {editTaskType === 'recurring' && (
                <>
                  <Form.Item
                    name="schedule_type"
                    label="调度类型"
                    rules={[{ required: editTaskType === 'recurring', message: '请选择调度类型' }]}
                  >
                    <Select
                      placeholder="选择调度类型"
                      value={editScheduleType}
                      onChange={setEditScheduleType}
                    >
                      <Option value="interval">间隔执行</Option>
                      <Option value="daily">每日执行</Option>
                      <Option value="weekly">每周执行</Option>
                      <Option value="monthly">每月执行</Option>
                      <Option value="cron">Cron表达式</Option>
                    </Select>
                  </Form.Item>

                  {editScheduleType === 'interval' && (
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          name={['schedule_config', 'interval']}
                          label="间隔数值"
                          rules={[{ required: true, message: '请输入间隔数值' }]}
                        >
                          <InputNumber min={1} placeholder="1" style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          name={['schedule_config', 'unit']}
                          label="时间单位"
                          initialValue="hours"
                        >
                          <Select>
                            <Option value="minutes">分钟</Option>
                            <Option value="hours">小时</Option>
                            <Option value="days">天</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                    </Row>
                  )}

                  {editScheduleType === 'daily' && (
                    <Form.Item
                      name={['schedule_config', 'time']}
                      label="执行时间"
                      rules={[{ required: true, message: '请选择执行时间' }]}
                    >
                      <TimePicker format="HH:mm" placeholder="选择时间" style={{ width: '100%' }} />
                    </Form.Item>
                  )}

                  {editScheduleType === 'weekly' && (
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          name={['schedule_config', 'day_of_week']}
                          label="星期几"
                          rules={[{ required: true, message: '请选择星期几' }]}
                        >
                          <Select placeholder="选择星期几">
                            <Option value={1}>星期一</Option>
                            <Option value={2}>星期二</Option>
                            <Option value={3}>星期三</Option>
                            <Option value={4}>星期四</Option>
                            <Option value={5}>星期五</Option>
                            <Option value={6}>星期六</Option>
                            <Option value={0}>星期日</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          name={['schedule_config', 'time']}
                          label="执行时间"
                          rules={[{ required: true, message: '请选择执行时间' }]}
                        >
                          <TimePicker format="HH:mm" placeholder="选择时间" style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>
                  )}

                  {editScheduleType === 'monthly' && (
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          name={['schedule_config', 'day_of_month']}
                          label="每月第几天"
                          rules={[{ required: true, message: '请输入日期' }]}
                        >
                          <InputNumber min={1} max={31} placeholder="1" style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          name={['schedule_config', 'time']}
                          label="执行时间"
                          rules={[{ required: true, message: '请选择执行时间' }]}
                        >
                          <TimePicker format="HH:mm" placeholder="选择时间" style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>
                  )}

                  {editScheduleType === 'cron' && (
                    <Form.Item
                      name={['schedule_config', 'cron_expression']}
                      label="Cron表达式"
                      rules={[{ required: true, message: '请输入Cron表达式' }]}
                      help="格式: 秒 分 时 日 月 周"
                    >
                      <Input placeholder="0 0 9 * * *" />
                    </Form.Item>
                  )}

                  <Form.Item
                    name="max_runs"
                    label="最大执行次数"
                    help="留空表示无限制"
                  >
                    <InputNumber min={1} placeholder="不限制" style={{ width: '100%' }} />
                  </Form.Item>
                </>
              )}
            </Collapse.Panel>
          </Collapse>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                更新任务
              </Button>
              <Button onClick={() => {
                setEditModalVisible(false);
                editForm.resetFields();
                resetEditScheduleState();
                setSelectedTask(null);
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
        width={isMobile ? '95%' : 600}
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
                  <Text strong>关联规则: </Text>
                  <Space direction="vertical" size="small">
                    {selectedTask.rules?.map((rule, index) => (
                      <Tag key={rule.rule_id} color={rule.is_active ? 'blue' : 'default'}>
                        {rule.rule_name}
                        {rule.priority > 0 && (
                          <Badge count={rule.priority} style={{ backgroundColor: '#52c41a', marginLeft: 4 }} />
                        )}
                      </Tag>
                    )) || <Text type="secondary">无关联规则</Text>}
                  </Space>
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
                {(selectedTask.date_from || selectedTask.date_to) && (
                  <Col span={24}>
                    <Text strong>时间范围: </Text>
                    <Text>
                      {selectedTask.date_from ? new Date(selectedTask.date_from).toLocaleString() : '不限'}
                      {' - '}
                      {selectedTask.date_to ? new Date(selectedTask.date_to).toLocaleString() : '一直有效'}
                    </Text>
                  </Col>
                )}
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
        width={isMobile ? '95%' : 800}
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