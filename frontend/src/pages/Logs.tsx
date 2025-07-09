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
  Tabs
} from 'antd';
import { 
  DeleteOutlined, 
  ReloadOutlined, 
  SearchOutlined,
  FileTextOutlined,
  BugOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import { LogEntry } from '../types';
import { useLogStore, useGlobalStore } from '../store';
import { apiService } from '../services/api';
import { subscribeToLogs } from '../services/websocket';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { TabPane } = Tabs;

const Logs: React.FC = () => {
  const { logs, addLog, clearLogs } = useLogStore();
  const { setLoading, setError } = useGlobalStore();
  const [filteredLogs, setFilteredLogs] = React.useState<LogEntry[]>([]);
  const [levelFilter, setLevelFilter] = React.useState<string>('');
  const [searchText, setSearchText] = React.useState<string>('');
  const [taskLogs, setTaskLogs] = React.useState<LogEntry[]>([]);
  const [systemLogs, setSystemLogs] = React.useState<LogEntry[]>([]);

  React.useEffect(() => {
    loadLogs();
    
    // 订阅实时日志
    const unsubscribe = subscribeToLogs((logData) => {
      addLog(logData);
    });
    
    return unsubscribe;
  }, []);

  React.useEffect(() => {
    // 过滤日志
    let filtered = logs;
    
    if (levelFilter) {
      filtered = filtered.filter(log => log.level === levelFilter);
    }
    
    if (searchText) {
      filtered = filtered.filter(log => 
        log.message.toLowerCase().includes(searchText.toLowerCase())
      );
    }
    
    setFilteredLogs(filtered);
  }, [logs, levelFilter, searchText]);

  const loadLogs = async () => {
    setLoading(true);
    try {
      // 加载任务日志
      const taskLogsResponse = await apiService.get<LogEntry[]>('/log/logs/task');
      if (taskLogsResponse.success && taskLogsResponse.data) {
        setTaskLogs(taskLogsResponse.data);
      }

      // 加载系统日志
      const systemLogsResponse = await apiService.get<LogEntry[]>('/log/logs/system');
      if (systemLogsResponse.success && systemLogsResponse.data) {
        setSystemLogs(systemLogsResponse.data);
      }
    } catch (error) {
      setError('加载日志失败');
      console.error('加载日志失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleClearLogs = async (type: 'task' | 'system') => {
    try {
      const response = await apiService.delete(`/log/logs/${type}`);
      if (response.success) {
        if (type === 'task') {
          setTaskLogs([]);
        } else {
          setSystemLogs([]);
        }
        clearLogs();
      }
    } catch (error) {
      setError('清除日志失败');
      console.error('清除日志失败:', error);
    }
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

  const errorCount = logs.filter(log => log.level === 'ERROR').length;
  const warningCount = logs.filter(log => log.level === 'WARNING').length;
  const infoCount = logs.filter(log => log.level === 'INFO').length;
  const debugCount = logs.filter(log => log.level === 'DEBUG').length;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={2}>日志查看</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadLogs}>
            刷新
          </Button>
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
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={8}>
            <Input.Search
              placeholder="搜索日志内容"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              prefix={<SearchOutlined />}
            />
          </Col>
          <Col xs={24} sm={8}>
            <Select
              style={{ width: '100%' }}
              placeholder="选择日志级别"
              value={levelFilter}
              onChange={setLevelFilter}
              allowClear
            >
              <Select.Option value="ERROR">ERROR</Select.Option>
              <Select.Option value="WARNING">WARNING</Select.Option>
              <Select.Option value="INFO">INFO</Select.Option>
              <Select.Option value="DEBUG">DEBUG</Select.Option>
            </Select>
          </Col>
          <Col xs={24} sm={8}>
            <RangePicker 
              style={{ width: '100%' }}
              showTime
              placeholder={['开始时间', '结束时间']}
            />
          </Col>
        </Row>
      </Card>

      {/* 日志列表 */}
      <Tabs defaultActiveKey="realtime">
        <TabPane tab="实时日志" key="realtime">
          <Card 
            title={`实时日志 (${filteredLogs.length})`}
            extra={
              <Button 
                type="text" 
                danger 
                icon={<DeleteOutlined />}
                onClick={() => clearLogs()}
              >
                清除
              </Button>
            }
          >
            <List
              dataSource={filteredLogs}
              renderItem={renderLogItem}
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
              }}
              locale={{ emptyText: '暂无日志' }}
            />
          </Card>
        </TabPane>
        
        <TabPane tab="任务日志" key="task">
          <Card 
            title={`任务日志 (${taskLogs.length})`}
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
            <List
              dataSource={taskLogs}
              renderItem={renderLogItem}
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
              }}
              locale={{ emptyText: '暂无任务日志' }}
            />
          </Card>
        </TabPane>
        
        <TabPane tab="系统日志" key="system">
          <Card 
            title={`系统日志 (${systemLogs.length})`}
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
            <List
              dataSource={systemLogs}
              renderItem={renderLogItem}
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
              }}
              locale={{ emptyText: '暂无系统日志' }}
            />
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default Logs;