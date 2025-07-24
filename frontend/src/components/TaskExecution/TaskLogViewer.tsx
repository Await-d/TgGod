import React, { useState, useEffect } from 'react';
import {
  Card,
  List,
  Badge,
  Tag,
  Typography,
  Space,
  Button,
  Select,
  Input,
  DatePicker,
  Row,
  Col,
  Empty,
  Spin,
  Alert,
  Tooltip,
  message,
  Modal
} from 'antd';
import {
  ReloadOutlined,
  SearchOutlined,
  FilterOutlined,
  DownloadOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  BugOutlined,
  EyeOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import { logApi, taskApi } from '../../services/apiService';
import { LogEntry, DownloadTask } from '../../types';

const { Text, Title } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;
const { Search } = Input;

interface TaskLogViewerProps {
  taskId?: number;
  height?: number;
  showFilters?: boolean;
  autoRefresh?: boolean;
}

const TaskLogViewer: React.FC<TaskLogViewerProps> = ({ 
  taskId, 
  height = 400,
  showFilters = true,
  autoRefresh = false 
}) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [tasks, setTasks] = useState<DownloadTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<number | undefined>(taskId);
  const [filters, setFilters] = useState<any>({});
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);
  const [logDetailVisible, setLogDetailVisible] = useState(false);

  // 获取任务日志
  const loadLogs = async () => {
    try {
      setLoading(true);
      const params = {
        ...filters,
        task_id: selectedTaskId,
        limit: 100
      };
      
      const logsData = await logApi.getTaskLogs(params);
      setLogs(logsData);
    } catch (error: any) {
      message.error(`加载日志失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 获取任务列表
  const loadTasks = async () => {
    try {
      const tasksData = await taskApi.getTasks({ limit: 100 });
      setTasks(tasksData);
    } catch (error: any) {
      message.error(`加载任务列表失败: ${error.message}`);
    }
  };

  // 获取日志级别图标
  const getLogLevelIcon = (level: string) => {
    const iconMap: Record<string, React.ReactNode> = {
      ERROR: <ExclamationCircleOutlined style={{ color: '#f5222d' }} />,
      WARNING: <WarningOutlined style={{ color: '#fa8c16' }} />,
      INFO: <InfoCircleOutlined style={{ color: '#1890ff' }} />,
      DEBUG: <BugOutlined style={{ color: '#666' }} />
    };
    return iconMap[level] || <InfoCircleOutlined />;
  };

  // 获取日志级别颜色
  const getLogLevelColor = (level: string) => {
    const colorMap: Record<string, string> = {
      ERROR: 'red',
      WARNING: 'orange', 
      INFO: 'blue',
      DEBUG: 'default'
    };
    return colorMap[level] || 'default';
  };

  // 处理筛选
  const handleFilter = (values: any) => {
    setFilters(values);
  };

  // 处理任务选择
  const handleTaskChange = (taskId: number) => {
    setSelectedTaskId(taskId);
  };

  // 查看日志详情
  const handleViewLogDetail = (log: LogEntry) => {
    setSelectedLog(log);
    setLogDetailVisible(true);
  };

  // 清除日志
  const handleClearLogs = async () => {
    Modal.confirm({
      title: '清除任务日志',
      content: '确定要清除当前任务的所有日志吗？此操作不可恢复。',
      okText: '确定',
      cancelText: '取消',
      onOk: async () => {
        try {
          await logApi.clearLogs('task');
          message.success('日志清除成功');
          loadLogs();
        } catch (error: any) {
          message.error(`清除日志失败: ${error.message}`);
        }
      }
    });
  };

  // 自动刷新
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (autoRefresh) {
      interval = setInterval(loadLogs, 5000); // 每5秒刷新
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh, selectedTaskId, filters]);

  // 初始化加载
  useEffect(() => {
    loadTasks();
  }, []);

  useEffect(() => {
    if (selectedTaskId) {
      loadLogs();
    }
  }, [selectedTaskId, filters]);

  return (
    <div>
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <BugOutlined style={{ marginRight: 8 }} />
            任务执行日志
            {selectedTaskId && (
              <Badge 
                count={logs.length} 
                style={{ marginLeft: 8 }}
                overflowCount={999}
              />
            )}
          </div>
        }
        extra={
          <Space>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={loadLogs}
              loading={loading}
            >
              刷新
            </Button>
            {logs.length > 0 && (
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={handleClearLogs}
              >
                清除
              </Button>
            )}
          </Space>
        }
        size="small"
      >
        {/* 筛选器 */}
        {showFilters && (
          <div style={{ marginBottom: 16 }}>
            <Row gutter={8}>
              <Col xs={24} sm={8}>
                <Select
                  placeholder="选择任务"
                  style={{ width: '100%' }}
                  value={selectedTaskId}
                  onChange={handleTaskChange}
                  allowClear
                >
                  {tasks.map(task => (
                    <Option key={task.id} value={task.id}>
                      {task.name}
                    </Option>
                  ))}
                </Select>
              </Col>
              <Col xs={24} sm={6}>
                <Select
                  placeholder="日志级别"
                  style={{ width: '100%' }}
                  onChange={(level) => handleFilter({ ...filters, level })}
                  allowClear
                >
                  <Option value="ERROR">错误</Option>
                  <Option value="WARNING">警告</Option>
                  <Option value="INFO">信息</Option>
                  <Option value="DEBUG">调试</Option>
                </Select>
              </Col>
              <Col xs={24} sm={10}>
                <Search
                  placeholder="搜索日志内容"
                  onSearch={(search) => handleFilter({ ...filters, search })}
                  allowClear
                />
              </Col>
            </Row>
          </div>
        )}

        {/* 日志列表 */}
        <div style={{ height, overflowY: 'auto' }}>
          <Spin spinning={loading}>
            {!selectedTaskId ? (
              <Alert
                message="请选择一个任务查看其执行日志"
                type="info"
                showIcon
              />
            ) : logs.length > 0 ? (
              <List
                size="small"
                dataSource={logs}
                renderItem={(log) => (
                  <List.Item
                    style={{
                      padding: '8px 0',
                      borderBottom: '1px solid #f0f0f0'
                    }}
                    actions={[
                      <Tooltip title="查看详情">
                        <Button
                          type="link"
                          size="small"
                          icon={<EyeOutlined />}
                          onClick={() => handleViewLogDetail(log)}
                        />
                      </Tooltip>
                    ]}
                  >
                    <List.Item.Meta
                      avatar={getLogLevelIcon(log.level)}
                      title={
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <Space>
                            <Tag color={getLogLevelColor(log.level)}>
                              {log.level}
                            </Tag>
                            <Text style={{ fontSize: 12, color: '#666' }}>
                              {new Date(log.timestamp).toLocaleString()}
                            </Text>
                          </Space>
                        </div>
                      }
                      description={
                        <div>
                          <Text ellipsis style={{ fontSize: 13 }}>
                            {log.message}
                          </Text>
                          {log.details && (
                            <Text type="secondary" style={{ fontSize: 11 }}>
                              {' '}[有详细信息]
                            </Text>
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
      </Card>

      {/* 日志详情模态框 */}
      <Modal
        title="日志详情"
        open={logDetailVisible}
        onCancel={() => setLogDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setLogDetailVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {selectedLog && (
          <div>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Row gutter={16}>
                <Col span={8}>
                  <Text strong>日志级别:</Text>
                </Col>
                <Col span={16}>
                  <Tag color={getLogLevelColor(selectedLog.level)}>
                    {selectedLog.level}
                  </Tag>
                </Col>
              </Row>
              
              <Row gutter={16}>
                <Col span={8}>
                  <Text strong>时间:</Text>
                </Col>
                <Col span={16}>
                  <Text>{new Date(selectedLog.created_at || selectedLog.timestamp).toLocaleString()}</Text>
                </Col>
              </Row>
              
              {selectedLog.task_id && (
                <Row gutter={16}>
                  <Col span={8}>
                    <Text strong>任务ID:</Text>
                  </Col>
                  <Col span={16}>
                    <Text>{selectedLog.task_id}</Text>
                  </Col>
                </Row>
              )}
              
              <Row gutter={16}>
                <Col span={8} style={{ alignSelf: 'flex-start' }}>
                  <Text strong>消息:</Text>
                </Col>
                <Col span={16}>
                  <Text style={{ whiteSpace: 'pre-wrap' }}>{selectedLog.message}</Text>
                </Col>
              </Row>
              
              {selectedLog.details && (
                <Row gutter={16}>
                  <Col span={8} style={{ alignSelf: 'flex-start' }}>
                    <Text strong>详细信息:</Text>
                  </Col>
                  <Col span={16}>
                    <pre style={{
                      background: '#f5f5f5',
                      padding: 12,
                      borderRadius: 4,
                      fontSize: 12,
                      lineHeight: 1.4,
                      maxHeight: 300,
                      overflow: 'auto'
                    }}>
                      {JSON.stringify(selectedLog.details, null, 2)}
                    </pre>
                  </Col>
                </Row>
              )}
            </Space>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default TaskLogViewer;