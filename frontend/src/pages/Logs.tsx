import React from 'react';
import { 
  Card, 
  Select, 
  Button, 
  Space, 
  List, 
  Tag, 
  Typography,
  Row,
  Col,
  Statistic,
  Input,
  DatePicker,
  Tabs,
  Modal,
  Form,
  Radio,
  Checkbox,
  Popconfirm,
  Tooltip,
  Badge,
  Empty
} from 'antd';
import { 
  DeleteOutlined, 
  ReloadOutlined, 
  SearchOutlined,
  FileTextOutlined,
  BugOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  DownloadOutlined,
  FilterOutlined,
  ClearOutlined,
  ExportOutlined
} from '@ant-design/icons';
import { LogEntry } from '../types';
import { useLogStore, useGlobalStore } from '../store';
import { logApi } from '../services/apiService';
import { subscribeToLogs, webSocketService } from '../services/websocket';
import { message } from 'antd';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const Logs: React.FC = () => {
  const [messageApi, contextHolder] = message.useMessage();
  const { addLog, clearLogs } = useLogStore();
  const { setLoading, setError } = useGlobalStore();
  const [filteredLogs, setFilteredLogs] = React.useState<LogEntry[]>([]);
  const [levelFilter, setLevelFilter] = React.useState<'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | ''>('');
  const [searchText, setSearchText] = React.useState<string>('');
  const [timeRange, setTimeRange] = React.useState<[string, string] | null>(null);
  const [taskLogs, setTaskLogs] = React.useState<LogEntry[]>([]);
  const [systemLogs, setSystemLogs] = React.useState<LogEntry[]>([]);
  const [logStats, setLogStats] = React.useState<any>(null);
  const [exportModalVisible, setExportModalVisible] = React.useState(false);
  const [selectedLogs, setSelectedLogs] = React.useState<number[]>([]);
  const [pagination, setPagination] = React.useState({ current: 1, pageSize: 20, total: 0 });
  const [activeTab, setActiveTab] = React.useState<string>('realtime');
  const [exportForm] = Form.useForm();
  const [autoRefresh, setAutoRefresh] = React.useState<boolean>(true);
  const [refreshInterval, setRefreshInterval] = React.useState<NodeJS.Timeout | null>(null);
  const [loadingError, setLoadingError] = React.useState<string | null>(null);
  const [retryCount, setRetryCount] = React.useState(0);

  const loadLogs = React.useCallback(async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const params = {
        level: levelFilter || undefined,
        search: searchText || undefined,
        start_time: timeRange?.[0] || undefined,
        end_time: timeRange?.[1] || undefined,
        skip: (page - 1) * pageSize,
        limit: pageSize
      };

      // 根据当前标签加载不同类型的日志
      switch (activeTab) {
        case 'task':
          const taskLogsResponse = await logApi.getTaskLogs(params);
          setTaskLogs(taskLogsResponse);
          break;
        case 'system':
          const systemLogsResponse = await logApi.getSystemLogs(params);
          setSystemLogs(systemLogsResponse);
          break;
        default:
          // 实时日志
          const logsResponse = await logApi.getLogs(params);
          setFilteredLogs(logsResponse.logs);
          setPagination(prev => ({
            ...prev,
            current: logsResponse.page,
            total: logsResponse.total
          }));
          break;
      }

      // 加载日志统计
      const stats = await logApi.getLogStats({
        start_time: timeRange?.[0] || undefined,
        end_time: timeRange?.[1] || undefined
      });
      setLogStats(stats);
      
      // 成功加载后重置错误状态
      setLoadingError(null);
      setRetryCount(0);
      
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '加载日志失败';
      setLoadingError(errorMsg);
      setError(errorMsg);
      
      // 只在非用户主动触发的情况下显示错误消息
      if (retryCount < 3) {
        console.warn(`日志加载失败，将自动重试 (${retryCount + 1}/3):`, error);
        setRetryCount(prev => prev + 1);
        // 延迟重试
        setTimeout(() => {
          loadLogs(page, pageSize);
        }, 2000);
      } else {
        messageApi.error('加载日志失败，请检查网络连接');
        console.error('加载日志失败:', error);
      }
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, levelFilter, searchText, timeRange, activeTab, messageApi, retryCount]);

  // 初始加载
  React.useEffect(() => {
    // 首次加载时强制加载日志，不依赖其他状态
    const initialLoad = async () => {
      setLoading(true);
      try {
        const logsResponse = await logApi.getLogs({
          skip: 0,
          limit: 20
        });
        setFilteredLogs(logsResponse.logs);
        setPagination(prev => ({
          ...prev,
          current: logsResponse.page,
          total: logsResponse.total
        }));

        // 加载日志统计
        const stats = await logApi.getLogStats();
        setLogStats(stats);
        
      } catch (error) {
        setError('加载日志失败');
        messageApi.error('加载日志失败');
        console.error('加载日志失败:', error);
      } finally {
        setLoading(false);
      }
    };
    
    initialLoad();
    
    // 确保WebSocket连接已建立
    if (!webSocketService.isConnected()) {
      console.log('启动WebSocket连接...');
      webSocketService.connect();
    }
    
    // 订阅实时日志
    const unsubscribe = subscribeToLogs((logData) => {
      console.log('收到实时日志:', logData);
      addLog(logData);
      // 实时日志到达时，如果在实时日志标签页且没有筛选条件，更新列表
      if (activeTab === 'realtime' && !levelFilter && !searchText && !timeRange) {
        setFilteredLogs(prev => [logData, ...prev].slice(0, pagination.pageSize));
      }
    });
    
    return unsubscribe;
  }, [setLoading, setError, messageApi, addLog, activeTab, levelFilter, searchText, timeRange, pagination]); // 移除 loadLogs 依赖

  // 自动刷新
  React.useEffect(() => {
    if (autoRefresh && activeTab === 'realtime') {
      const interval = setInterval(() => {
        // 只有在没有筛选条件时才自动刷新，避免干扰用户筛选操作
        if (!levelFilter && !searchText && !timeRange) {
          loadLogs(pagination.current, pagination.pageSize);
        }
      }, 10000); // 每10秒刷新一次
      setRefreshInterval(interval);
      return () => clearInterval(interval);
    } else if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
  }, [autoRefresh, activeTab, levelFilter, searchText, timeRange, loadLogs, pagination, refreshInterval]);

  // 筛选参数变化时重新加载
  React.useEffect(() => {
    if (activeTab === 'realtime' && (levelFilter || searchText || timeRange)) {
      // 只有在实时日志标签页且有筛选条件时才重新加载
      loadLogs(1, pagination.pageSize); // 重置到第一页
    } else if (activeTab !== 'realtime') {
      // 非实时日志标签页总是重新加载
      loadLogs(1, pagination.pageSize);
    }
  }, [levelFilter, searchText, timeRange, activeTab, loadLogs, pagination.pageSize]);


  const handleClearLogs = async (type: 'task' | 'system' | 'all') => {
    try {
      const response = await logApi.clearLogs(type);
      if (response.success) {
        messageApi.success(`成功清除${response.cleared_count}条日志`);
        if (type === 'task') {
          setTaskLogs([]);
        } else if (type === 'system') {
          setSystemLogs([]);
        } else {
          setTaskLogs([]);
          setSystemLogs([]);
          clearLogs();
        }
        loadLogs(); // 重新加载
      }
    } catch (error) {
      setError('清除日志失败');
      messageApi.error('清除日志失败');
      console.error('清除日志失败:', error);
    }
  };

  const handleExportLogs = async (values: any) => {
    try {
      const params = {
        type: values.type || 'all',
        level: values.level || undefined,
        search: searchText || undefined,
        start_time: timeRange?.[0] || undefined,
        end_time: timeRange?.[1] || undefined,
        format: values.format || 'json'
      };
      
      const response = await logApi.exportLogs(params);
      
      // 下载文件
      const link = document.createElement('a');
      link.href = response.download_url;
      link.download = response.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      messageApi.success(`成功导出日志文件: ${response.filename}`);
      setExportModalVisible(false);
    } catch (error) {
      messageApi.error('导出日志失败');
      console.error('导出日志失败:', error);
    }
  };

  const handleBatchDeleteLogs = async () => {
    if (selectedLogs.length === 0) {
      messageApi.warning('请选择要删除的日志');
      return;
    }
    
    try {
      const response = await logApi.deleteLogs(selectedLogs);
      if (response.success) {
        messageApi.success(`成功删除${response.deleted_count}条日志`);
        setSelectedLogs([]);
        loadLogs();
      }
    } catch (error) {
      messageApi.error('批量删除日志失败');
      console.error('批量删除日志失败:', error);
    }
  };

  const handleTimeRangeChange = (dates: any) => {
    if (dates && dates.length === 2) {
      setTimeRange([
        dates[0].format('YYYY-MM-DD HH:mm:ss'),
        dates[1].format('YYYY-MM-DD HH:mm:ss')
      ]);
    } else {
      setTimeRange(null);
    }
  };

  const clearFilters = () => {
    setLevelFilter('');
    setSearchText('');
    setTimeRange(null);
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR': return '#f5222d';
      case 'WARNING': return '#faad14';
      case 'INFO': return '#1890ff';
      case 'DEBUG': return '#52c41a';
      default: return '#666';
    }
  };

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'ERROR': return <CloseCircleOutlined style={{ color: '#f5222d' }} />;
      case 'WARNING': return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'INFO': return <InfoCircleOutlined style={{ color: '#1890ff' }} />;
      case 'DEBUG': return <BugOutlined style={{ color: '#52c41a' }} />;
      default: return <FileTextOutlined style={{ color: '#666' }} />;
    }
  };

  const renderLogItem = (log: LogEntry) => (
    <List.Item key={log.id}>
      <div style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {getLevelIcon(log.level)}
            <Tag color={getLevelColor(log.level)}>{log.level}</Tag>
            {log.task_id && (
              <Tag color="purple">任务ID: {log.task_id}</Tag>
            )}
          </div>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {new Date(log.created_at).toLocaleString()}
          </Text>
        </div>
        
        <div style={{ marginBottom: 8 }}>
          <Text>{log.message}</Text>
        </div>
        
        {log.details && (
          <div style={{ 
            background: '#f5f5f5', 
            padding: '8px', 
            borderRadius: '4px',
            fontSize: '12px',
            fontFamily: 'monospace'
          }}>
            <pre>{JSON.stringify(log.details, null, 2)}</pre>
          </div>
        )}
      </div>
    </List.Item>
  );

  const errorCount = logStats?.error_count || 0;
  const warningCount = logStats?.warning_count || 0;
  const infoCount = logStats?.info_count || 0;
  const debugCount = logStats?.debug_count || 0;

  return (
    <div>
      {contextHolder}
      
      {/* 错误状态显示 */}
      {loadingError && (
        <Card 
          style={{ marginBottom: 16, borderColor: '#ff4d4f' }}
          size="small"
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
              <Text type="danger">日志加载失败: {loadingError}</Text>
              {retryCount > 0 && (
                <Text type="secondary">({retryCount}/3 次重试)</Text>
              )}
            </div>
            <Button 
              size="small" 
              type="primary" 
              onClick={() => {
                setLoadingError(null);
                setRetryCount(0);
                loadLogs(pagination.current, pagination.pageSize);
              }}
            >
              重新加载
            </Button>
          </div>
        </Card>
      )}
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={2}>日志查看</Title>
          {logStats && (
            <Text type="secondary">
              总计 {logStats.total_logs} 条日志 | 任务日志 {logStats.task_log_count} 条 | 系统日志 {logStats.system_log_count} 条
            </Text>
          )}
        </div>
        <Space>
          <Tooltip title="自动刷新">
            <Checkbox 
              checked={autoRefresh} 
              onChange={(e) => setAutoRefresh(e.target.checked)}
            >
              自动刷新
            </Checkbox>
          </Tooltip>
          <Button icon={<ExportOutlined />} onClick={() => setExportModalVisible(true)}>
            导出日志
          </Button>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={() => {
              // 强制刷新当前标签页的数据
              if (activeTab === 'realtime') {
                loadLogs(pagination.current, pagination.pageSize);
              } else {
                loadLogs(1, 20); // 其他标签页重置到第一页
              }
            }}
          >
            刷新
          </Button>
          <Popconfirm
            title="确定要清除所有日志吗？"
            description="此操作不可恢复"
            onConfirm={() => handleClearLogs('all')}
            okText="确定"
            cancelText="取消"
          >
            <Button danger icon={<ClearOutlined />}>
              清除所有
            </Button>
          </Popconfirm>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="错误日志"
              value={errorCount}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="警告日志"
              value={warningCount}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="信息日志"
              value={infoCount}
              prefix={<InfoCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="调试日志"
              value={debugCount}
              prefix={<BugOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 过滤器 */}
      <Card 
        style={{ marginBottom: 16 }}
        title={
          <Space>
            <FilterOutlined />
            筛选条件
            {(levelFilter || searchText || timeRange) && (
              <Badge count={[levelFilter, searchText, timeRange].filter(Boolean).length} />
            )}
          </Space>
        }
        extra={
          <Button 
            size="small" 
            onClick={clearFilters}
            disabled={!levelFilter && !searchText && !timeRange}
          >
            清除筛选
          </Button>
        }
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={6}>
            <Input.Search
              placeholder="搜索日志内容"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
              prefix={<SearchOutlined />}
            />
          </Col>
          <Col xs={24} sm={6}>
            <Select
              style={{ width: '100%' }}
              placeholder="选择日志级别"
              value={levelFilter}
              onChange={setLevelFilter}
              allowClear
            >
              <Select.Option value="ERROR">
                <Space>
                  <CloseCircleOutlined style={{ color: '#f5222d' }} />
                  ERROR
                </Space>
              </Select.Option>
              <Select.Option value="WARNING">
                <Space>
                  <WarningOutlined style={{ color: '#faad14' }} />
                  WARNING
                </Space>
              </Select.Option>
              <Select.Option value="INFO">
                <Space>
                  <InfoCircleOutlined style={{ color: '#1890ff' }} />
                  INFO
                </Space>
              </Select.Option>
              <Select.Option value="DEBUG">
                <Space>
                  <BugOutlined style={{ color: '#52c41a' }} />
                  DEBUG
                </Space>
              </Select.Option>
            </Select>
          </Col>
          <Col xs={24} sm={8}>
            <RangePicker 
              style={{ width: '100%' }}
              showTime
              placeholder={['开始时间', '结束时间']}
              onChange={handleTimeRangeChange}
              allowClear
            />
          </Col>
          <Col xs={24} sm={4}>
            {selectedLogs.length > 0 && (
              <Popconfirm
                title={`确定要删除选中的 ${selectedLogs.length} 条日志吗？`}
                onConfirm={handleBatchDeleteLogs}
                okText="确定"
                cancelText="取消"
              >
                <Button danger size="small" icon={<DeleteOutlined />}>
                  删除选中 ({selectedLogs.length})
                </Button>
              </Popconfirm>
            )}
          </Col>
        </Row>
      </Card>

      {/* 日志列表 */}
      <Tabs 
        activeKey={activeTab} 
        onChange={setActiveTab}
        items={[
          {
            label: (
              <Badge count={(filteredLogs || []).length} showZero>
                <Space>
                  实时日志
                  {autoRefresh && activeTab === 'realtime' && <Badge status="processing" />}
                </Space>
              </Badge>
            ),
            key: 'realtime',
            children: (
              <Card 
                title={`实时日志 (${(filteredLogs || []).length})`}
                extra={
                  <Space>
                    <Button 
                      type="text" 
                      danger 
                      icon={<DeleteOutlined />}
                      onClick={() => clearLogs()}
                    >
                      清除
                    </Button>
                  </Space>
                }
              >
                {(filteredLogs || []).length === 0 ? (
                  <Empty description="暂无日志数据" />
                ) : (
                  <List
                    dataSource={filteredLogs}
                    renderItem={(item) => (
                      <List.Item
                        key={item.id}
                        actions={[
                          <Button
                            type="link"
                            danger
                            size="small"
                            onClick={() => {
                              setSelectedLogs([item.id]);
                              handleBatchDeleteLogs();
                            }}
                            icon={<DeleteOutlined />}
                          >
                            删除
                          </Button>
                        ]}
                      >
                        <div style={{ width: '100%' }}>
                          <Checkbox
                            checked={selectedLogs.includes(item.id)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedLogs(prev => [...prev, item.id]);
                              } else {
                                setSelectedLogs(prev => prev.filter(id => id !== item.id));
                              }
                            }}
                            style={{ marginRight: 8 }}
                          />
                          <div style={{ display: 'inline-block', width: 'calc(100% - 24px)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                {getLevelIcon(item.level)}
                                <Tag color={getLevelColor(item.level)}>{item.level}</Tag>
                                {item.task_id && (
                                  <Tag color="purple">任务ID: {item.task_id}</Tag>
                                )}
                              </div>
                              <Text type="secondary" style={{ fontSize: '12px' }}>
                                {new Date(item.created_at).toLocaleString()}
                              </Text>
                            </div>
                            
                            <div style={{ marginBottom: 8 }}>
                              <Text>{item.message}</Text>
                            </div>
                            
                            {item.details && (
                              <div style={{ 
                                background: '#f5f5f5', 
                                padding: '8px', 
                                borderRadius: '4px',
                                fontSize: '12px',
                                fontFamily: 'monospace'
                              }}>
                                <pre>{JSON.stringify(item.details, null, 2)}</pre>
                              </div>
                            )}
                          </div>
                        </div>
                      </List.Item>
                    )}
                    pagination={{
                      current: pagination.current,
                      pageSize: pagination.pageSize,
                      total: pagination.total,
                      showSizeChanger: true,
                      showQuickJumper: true,
                      showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
                      onChange: (page, pageSize) => {
                        setPagination(prev => ({ ...prev, current: page, pageSize: pageSize || prev.pageSize }));
                        loadLogs(page, pageSize);
                      },
                    }}
                  />
                )}
              </Card>
            )
          }
          ,
          {
            label: (
              <Badge count={(taskLogs || []).length} showZero>
                任务日志
              </Badge>
            ),
            key: 'task',
            children: (
              <Card 
                title={`任务日志 (${(taskLogs || []).length})`}
                extra={
                  <Button 
                    type="text" 
                    danger 
                    icon={<DeleteOutlined />}
                    onClick={() => handleClearLogs('task')}
                  >
                    清除
                  </Button>
                }
              >
                {(taskLogs || []).length === 0 ? (
                  <Empty description="暂无任务日志" />
                ) : (
                  <List
                    dataSource={taskLogs}
                    renderItem={renderLogItem}
                    pagination={{
                      pageSize: 20,
                      showSizeChanger: true,
                      showQuickJumper: true,
                      showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
                    }}
                  />
                )}
              </Card>
            )
          },
          {
            label: (
              <Badge count={(systemLogs || []).length} showZero>
                系统日志
              </Badge>
            ),
            key: 'system',
            children: (
              <Card 
                title={`系统日志 (${(systemLogs || []).length})`}
                extra={
                  <Button 
                    type="text" 
                    danger 
                    icon={<DeleteOutlined />}
                    onClick={() => handleClearLogs('system')}
                  >
                    清除
                  </Button>
                }
              >
                {(systemLogs || []).length === 0 ? (
                  <Empty description="暂无系统日志" />
                ) : (
                  <List
                    dataSource={systemLogs}
                    renderItem={renderLogItem}
                    pagination={{
                      pageSize: 20,
                      showSizeChanger: true,
                      showQuickJumper: true,
                      showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
                    }}
                  />
                )}
              </Card>
            )
          }
        ]}
      />

      {/* 导出日志模态框 */}
      <Modal
        title="导出日志"
        open={exportModalVisible}
        onCancel={() => setExportModalVisible(false)}
        footer={null}
      >
        <Form
          form={exportForm}
          layout="vertical"
          onFinish={handleExportLogs}
        >
          <Form.Item
            label="日志类型"
            name="type"
            initialValue="all"
          >
            <Radio.Group>
              <Radio value="all">全部日志</Radio>
              <Radio value="task">任务日志</Radio>
              <Radio value="system">系统日志</Radio>
            </Radio.Group>
          </Form.Item>
          
          <Form.Item
            label="日志级别"
            name="level"
          >
            <Select placeholder="选择日志级别（可选）" allowClear>
              <Select.Option value="ERROR">ERROR</Select.Option>
              <Select.Option value="WARNING">WARNING</Select.Option>
              <Select.Option value="INFO">INFO</Select.Option>
              <Select.Option value="DEBUG">DEBUG</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            label="导出格式"
            name="format"
            initialValue="json"
          >
            <Radio.Group>
              <Radio value="json">JSON</Radio>
              <Radio value="csv">CSV</Radio>
              <Radio value="txt">TXT</Radio>
            </Radio.Group>
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                <DownloadOutlined />
                导出
              </Button>
              <Button onClick={() => setExportModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Logs;