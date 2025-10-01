import React, { useState, useEffect, useCallback } from 'react';
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
  Row,
  Col,
  Empty,
  Spin,
  Tooltip,
  message,
  Modal,
  Divider
} from 'antd';
import {
  ReloadOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  BugOutlined,
  EyeOutlined,
  DeleteOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import { logApi } from '../../services/apiService';
import { LogEntry } from '../../types';
import './SystemLogViewer.css';

const { Text } = Typography;
const { Option } = Select;
const { Search } = Input;

interface SystemLogViewerProps {
  height?: number;
  showFilters?: boolean;
  autoRefresh?: boolean;
  logType?: 'all' | 'system' | 'task';
}

const SystemLogViewer: React.FC<SystemLogViewerProps> = ({ 
  height = 500,
  showFilters = true,
  autoRefresh = false,
  logType = 'all'
}) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<any>({});
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);
  const [logDetailVisible, setLogDetailVisible] = useState(false);
  const [currentLogType, setCurrentLogType] = useState<'all' | 'system' | 'task'>(logType);

  // 获取日志
  const loadLogs = useCallback(async () => {
    try {
      setLoading(true);

      let logsData: LogEntry[] = [];

      if (currentLogType === 'all') {
        // 获取最近的混合日志
        logsData = await logApi.getRecentLogs(100, 'all');
      } else if (currentLogType === 'system') {
        // 获取系统日志
        logsData = await logApi.getSystemLogs({
          ...filters,
          limit: 100
        });
      } else if (currentLogType === 'task') {
        // 获取任务日志
        logsData = await logApi.getTaskLogs({
          ...filters,
          limit: 100
        });
      }

      setLogs(logsData);
    } catch (error: any) {
      console.error('加载日志失败:', error);
      message.error(`加载日志失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [currentLogType, filters]);

  // 获取日志级别图标
  const getLogLevelIcon = (level: string) => {
    const iconMap: Record<string, React.ReactNode> = {
      ERROR: <ExclamationCircleOutlined className="system-log-level-error" />,
      WARNING: <WarningOutlined className="system-log-level-warning" />,
      INFO: <InfoCircleOutlined className="system-log-level-info" />,
      DEBUG: <BugOutlined className="system-log-level-debug" />
    };
    return iconMap[level] || <InfoCircleOutlined className="system-log-level-default" />;
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

  // 获取日志类型标签
  const getLogTypeTag = (log: LogEntry) => {
    if ('task_id' in log && log.task_id) {
      return <Tag color="green">任务</Tag>;
    } else if ('module' in log) {
      return <Tag color="purple">系统</Tag>;
    }
    return <Tag color="blue">未知</Tag>;
  };

  // 处理筛选
  const handleFilter = (values: any) => {
    setFilters(values);
  };

  // 查看日志详情
  const handleViewLogDetail = (log: LogEntry) => {
    setSelectedLog(log);
    setLogDetailVisible(true);
  };

  // 清除日志
  const handleClearLogs = async () => {
    Modal.confirm({
      title: '清除日志',
      content: `确定要清除所有${currentLogType === 'all' ? '' : currentLogType}日志吗？此操作不可恢复。`,
      okText: '确定',
      cancelText: '取消',
      onOk: async () => {
        try {
          await logApi.clearLogs(currentLogType === 'all' ? 'all' : currentLogType);
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
      interval = setInterval(loadLogs, 10000); // 每10秒刷新
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh, loadLogs]);

  // 初始化加载
  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  return (
    <div>
      <Card
        title={
          <div className="system-log-header">
            <FileTextOutlined className="system-log-header-icon" />
            系统运行日志
            {logs.length > 0 && (
              <Badge 
                count={logs.length} 
                className="system-log-header-badge"
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
          <div className="system-log-filter-bar">
            <Row gutter={8}>
              <Col xs={24} sm={6}>
                <Select
                  placeholder="日志类型"
                  className="system-log-filter-select"
                  value={currentLogType}
                  onChange={setCurrentLogType}
                >
                  <Option value="all">全部日志</Option>
                  <Option value="system">系统日志</Option>
                  <Option value="task">任务日志</Option>
                </Select>
              </Col>
              <Col xs={24} sm={6}>
                <Select
                  placeholder="日志级别"
                  className="system-log-filter-select"
                  onChange={(level) => handleFilter({ ...filters, level })}
                  allowClear
                >
                  <Option value="ERROR">错误</Option>
                  <Option value="WARNING">警告</Option>
                  <Option value="INFO">信息</Option>
                  <Option value="DEBUG">调试</Option>
                </Select>
              </Col>
              <Col xs={24} sm={12}>
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
        <div className="system-log-list" style={{ height }}>
          <Spin spinning={loading}>
            {logs.length > 0 ? (
              <List
                size="small"
                dataSource={logs}
                renderItem={(log) => (
                  <List.Item className="system-log-item"
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
                        <div className="system-log-item-header">
                          <Space>
                            {getLogTypeTag(log)}
                            <Tag color={getLogLevelColor(log.level)}>
                              {log.level}
                            </Tag>
                            {'task_id' in log && log.task_id && (
                              <Tag color="cyan">
                                任务#{log.task_id}
                              </Tag>
                            )}
                            {'module' in log && (log as any).module && (
                              <Tag color="geekblue">
                                {(log as any).module}
                              </Tag>
                            )}
                            <Text className="system-log-item-time">
                              {new Date(log.created_at || log.timestamp).toLocaleString()}
                            </Text>
                          </Space>
                        </div>
                      }
                      description={
                        <div>
                          <div>
                            <Text ellipsis className="system-log-item-message">
                              {log.message}
                            </Text>
                            {((log.details && Object.keys(log.details).length > 0) || 
                              ('function' in log && (log as any).function)) && (
                              <Text type="secondary" className="system-log-item-extra">
                                {' '}[有详细信息]
                              </Text>
                            )}
                          </div>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty 
                description="暂无日志数据" 
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
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
            <Space direction="vertical" size="middle" className="system-log-detail-content">
              <Row gutter={16}>
                <Col span={8}>
                  <Text strong>日志类型:</Text>
                </Col>
                <Col span={16}>
                  {getLogTypeTag(selectedLog)}
                </Col>
              </Row>
              
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
              
              {'task_id' in selectedLog && selectedLog.task_id && (
                <Row gutter={16}>
                  <Col span={8}>
                    <Text strong>任务ID:</Text>
                  </Col>
                  <Col span={16}>
                    <Text>{selectedLog.task_id}</Text>
                  </Col>
                </Row>
              )}
              
              {'module' in selectedLog && (selectedLog as any).module && (
                <Row gutter={16}>
                  <Col span={8}>
                    <Text strong>模块:</Text>
                  </Col>
                  <Col span={16}>
                    <Text>{(selectedLog as any).module}</Text>
                  </Col>
                </Row>
              )}
              
              {'function' in selectedLog && (selectedLog as any).function && (
                <Row gutter={16}>
                  <Col span={8}>
                    <Text strong>函数:</Text>
                  </Col>
                  <Col span={16}>
                    <Text>{(selectedLog as any).function}</Text>
                  </Col>
                </Row>
              )}
              
              <Divider />
              
              <Row gutter={16}>
                <Col span={8} className="system-log-detail-label">
                  <Text strong>消息:</Text>
                </Col>
                <Col span={16}>
                  <Text className="system-log-detail-message">{selectedLog.message}</Text>
                </Col>
              </Row>
              
              {selectedLog.details && Object.keys(selectedLog.details).length > 0 && (
                <Row gutter={16}>
                  <Col span={8} className="system-log-detail-label">
                    <Text strong>详细信息:</Text>
                  </Col>
                  <Col span={16}>
                    <pre className="system-log-detail-json">
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

export default SystemLogViewer;
