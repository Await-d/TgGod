import React from 'react';
import { Row, Col, Card, Statistic, Progress, Button, List, Typography, Badge } from 'antd';
import { 
  TeamOutlined, 
  MessageOutlined, 
  DownloadOutlined, 
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { useStatisticsStore, useTaskStore, useLogStore } from '../store';
import { apiService } from '../services/api';

const { Title, Text } = Typography;

const Dashboard: React.FC = () => {
  const { statistics, setStatistics } = useStatisticsStore();
  const { tasks, setTasks } = useTaskStore();
  const { logs } = useLogStore();
  const [loading, setLoading] = React.useState(false);

  const loadData = React.useCallback(async () => {
    setLoading(true);
    try {
      // 加载统计数据
      // const statsResponse = await apiService.get('/telegram/groups');
      // TODO: 实现统计数据API
      
      // 加载任务数据
      const tasksResponse = await apiService.get('/task/tasks');
      if (tasksResponse.success && tasksResponse.data) {
        setTasks(Array.isArray(tasksResponse.data) ? tasksResponse.data : []);
      }
      
      // 模拟统计数据
      setStatistics({
        total_groups: 5,
        total_messages: 1250,
        total_downloads: 23,
        active_tasks: 2,
        storage_used: 1024 * 1024 * 512, // 512MB
        today_downloads: 8
      });
    } catch (error) {
      console.error('加载数据失败:', error);
    } finally {
      setLoading(false);
    }
  }, [setTasks, setStatistics]);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running': return <PlayCircleOutlined style={{ color: '#52c41a' }} />;
      case 'paused': return <PauseCircleOutlined style={{ color: '#faad14' }} />;
      case 'completed': return <CheckCircleOutlined style={{ color: '#1890ff' }} />;
      case 'failed': return <ExclamationCircleOutlined style={{ color: '#f5222d' }} />;
      default: return <PlayCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const recentLogs = logs.slice(0, 10);

  return (
    <div>
      <Title level={2}>仪表板</Title>
      
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总群组数"
              value={statistics?.total_groups || 0}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总消息数"
              value={statistics?.total_messages || 0}
              prefix={<MessageOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="下载任务"
              value={statistics?.total_downloads || 0}
              prefix={<DownloadOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="今日下载"
              value={statistics?.today_downloads || 0}
              prefix={<DownloadOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* 活跃任务 */}
        <Col xs={24} lg={12}>
          <Card 
            title="活跃任务" 
            extra={
              <Button type="link" onClick={loadData} loading={loading}>
                刷新
              </Button>
            }
          >
            <List
              dataSource={tasks.filter(task => task.status === 'running').slice(0, 5)}
              renderItem={(task) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={getStatusIcon(task.status)}
                    title={task.name}
                    description={
                      <div>
                        <Progress 
                          percent={task.progress} 
                          size="small"
                          status={task.status === 'failed' ? 'exception' : 'active'}
                        />
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          {task.downloaded_messages}/{task.total_messages} 条消息
                        </Text>
                      </div>
                    }
                  />
                </List.Item>
              )}
              locale={{ emptyText: '暂无活跃任务' }}
            />
          </Card>
        </Col>

        {/* 最近日志 */}
        <Col xs={24} lg={12}>
          <Card title="最近日志">
            <List
              dataSource={recentLogs}
              renderItem={(log) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={
                      <Badge 
                        color={
                          log.level === 'ERROR' ? '#f5222d' :
                          log.level === 'WARNING' ? '#faad14' :
                          log.level === 'INFO' ? '#1890ff' : '#52c41a'
                        }
                      />
                    }
                    title={
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>{log.message}</Text>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          {new Date(log.created_at).toLocaleTimeString()}
                        </Text>
                      </div>
                    }
                    description={
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {log.level}
                      </Text>
                    }
                  />
                </List.Item>
              )}
              locale={{ emptyText: '暂无日志' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 存储使用情况 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="存储使用情况">
            <Row gutter={[16, 16]}>
              <Col xs={24} md={12}>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Text>已使用存储空间</Text>
                    <Text strong>
                      {formatFileSize(statistics?.storage_used || 0)}
                    </Text>
                  </div>
                  <Progress 
                    percent={Math.round((statistics?.storage_used || 0) / (1024 * 1024 * 1024) * 100)} 
                    strokeColor="#1890ff"
                  />
                </div>
              </Col>
              <Col xs={24} md={12}>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Text>活跃任务进度</Text>
                    <Text strong>
                      {statistics?.active_tasks || 0} 个任务
                    </Text>
                  </div>
                  <Progress 
                    percent={statistics?.active_tasks ? 100 : 0} 
                    strokeColor="#52c41a"
                  />
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;