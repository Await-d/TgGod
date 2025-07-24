import React, { useState, useEffect, useCallback } from 'react';
import { 
  Row, 
  Col, 
  Card, 
  Statistic, 
  Progress, 
  Button, 
  List, 
  Typography, 
  Badge, 
  Spin, 
  Alert,
  Table,
  Tag,
  Space,
  Tooltip,
  Empty,
  Divider
} from 'antd';
import { 
  TeamOutlined, 
  MessageOutlined, 
  DownloadOutlined, 
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  DatabaseOutlined,
  HddOutlined,
  FileTextOutlined,
  CloudDownloadOutlined,
  TrophyOutlined,
  ClockCircleOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import { dashboardApi } from '../services/apiService';

const { Title, Text } = Typography;

const Dashboard: React.FC = () => {
  // 状态管理
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 数据状态
  const [overviewData, setOverviewData] = useState<any>(null);
  const [groupsData, setGroupsData] = useState<any>(null);
  const [activityData, setActivityData] = useState<any>(null);
  const [downloadStats, setDownloadStats] = useState<any>(null);
  const [systemInfo, setSystemInfo] = useState<any>(null);

  // 加载所有数据
  const loadData = useCallback(async (forceRefresh: boolean = false) => {
    setLoading(true);
    setError(null);
    
    try {
      // 并行加载所有数据
      const [overview, groups, activity, downloads, system] = await Promise.allSettled([
        dashboardApi.getOverview(forceRefresh),
        dashboardApi.getGroupsSummary(10, forceRefresh),
        dashboardApi.getRecentActivity(24, 20, forceRefresh),
        dashboardApi.getDownloadStatistics(7, forceRefresh),
        dashboardApi.getSystemInfo(forceRefresh)
      ]);

      // 处理概览数据
      if (overview.status === 'fulfilled') {
        setOverviewData(overview.value);
      } else {
        console.error('获取概览数据失败:', overview.reason);
      }

      // 处理群组数据
      if (groups.status === 'fulfilled') {
        setGroupsData(groups.value);
      } else {
        console.error('获取群组数据失败:', groups.reason);
      }

      // 处理活动数据
      if (activity.status === 'fulfilled') {
        setActivityData(activity.value);
      } else {
        console.error('获取活动数据失败:', activity.reason);
      }

      // 处理下载统计
      if (downloads.status === 'fulfilled') {
        setDownloadStats(downloads.value);
      } else {
        console.error('获取下载统计失败:', downloads.reason);
      }

      // 处理系统信息
      if (system.status === 'fulfilled') {
        setSystemInfo(system.value);
      } else {
        console.error('获取系统信息失败:', system.reason);
      }

    } catch (error: any) {
      console.error('加载仪表盘数据失败:', error);
      setError(error.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  // 自动刷新数据
  useEffect(() => {
    loadData();
    
    // 设置定时刷新（每5分钟）
    const interval = setInterval(() => {
      loadData();
    }, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, [loadData]);

  // 工具函数
  const formatFileSize = (bytes: number) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatNumber = (num: number) => {
    if (!num) return '0';
    return num.toLocaleString();
  };

  const getMediaTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      photo: '#52c41a',
      video: '#1890ff',
      document: '#722ed1',
      audio: '#fa8c16'
    };
    return colors[type] || '#d9d9d9';
  };

  const renderStatCard = (title: string, value: any, icon: React.ReactNode, color: string, suffix?: string) => (
    <Card>
      <Statistic
        title={title}
        value={value}
        prefix={icon}
        suffix={suffix}
        valueStyle={{ color }}
      />
    </Card>
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2}>仪表板</Title>
        <Button 
          type="primary" 
          icon={<ReloadOutlined />}
          onClick={() => loadData(true)}
          loading={loading}
        >
          刷新数据
        </Button>
      </div>

      {error && (
        <Alert
          message="数据加载失败"
          description={error}
          type="error"
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 概览统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          {renderStatCard(
            "总群组数",
            overviewData?.basic_stats?.total_groups || 0,
            <TeamOutlined />,
            '#1890ff'
          )}
        </Col>
        <Col xs={24} sm={12} md={6}>
          {renderStatCard(
            "活跃群组",
            overviewData?.basic_stats?.active_groups || 0,
            <CheckCircleOutlined />,
            '#52c41a'
          )}
        </Col>
        <Col xs={24} sm={12} md={6}>
          {renderStatCard(
            "总消息数",
            formatNumber(overviewData?.basic_stats?.total_messages || 0),
            <MessageOutlined />,
            '#722ed1'
          )}
        </Col>
        <Col xs={24} sm={12} md={6}>
          {renderStatCard(
            "媒体消息",
            formatNumber(overviewData?.basic_stats?.media_messages || 0),
            <FileTextOutlined />,
            '#fa8c16'
          )}
        </Col>
      </Row>

      {/* 下载统计 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          {renderStatCard(
            "已下载媒体",
            formatNumber(overviewData?.download_stats?.downloaded_media || 0),
            <CloudDownloadOutlined />,
            '#13c2c2'
          )}
        </Col>
        <Col xs={24} sm={12} md={6}>
          {renderStatCard(
            "下载大小",
            formatFileSize(overviewData?.download_stats?.total_media_size || 0),
            <HddOutlined />,
            '#eb2f96'
          )}
        </Col>
        <Col xs={24} sm={12} md={6}>
          {renderStatCard(
            "下载中任务",
            overviewData?.download_stats?.downloading_tasks || 0,
            <DownloadOutlined />,
            '#f5222d'
          )}
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="下载完成率"
              value={overviewData?.download_stats?.download_completion_rate || 0}
              precision={1}
              suffix="%"
              prefix={<TrophyOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
            <Progress 
              percent={overviewData?.download_stats?.download_completion_rate || 0}
              size="small"
              strokeColor="#52c41a"
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 今日统计 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12}>
          <Card>
            <Statistic
              title="今日新消息"
              value={overviewData?.today_stats?.new_messages || 0}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12}>
          <Card>
            <Statistic
              title="今日新下载"
              value={overviewData?.today_stats?.new_downloads || 0}
              prefix={<DownloadOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* 群组摘要 */}
        <Col xs={24} lg={12}>
          <Card 
            title="群组摘要" 
            extra={
              <Space>
                <Text type="secondary">前10个活跃群组</Text>
              </Space>
            }
          >
            {loading ? (
              <Spin />
            ) : groupsData?.groups?.length > 0 ? (
              <List
                dataSource={groupsData.groups}
                renderItem={(group: any) => (
                  <List.Item>
                    <List.Item.Meta
                      title={
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Text strong>{group.title}</Text>
                          <Badge 
                            count={group.message_count} 
                            style={{ backgroundColor: '#52c41a' }}
                          />
                        </div>
                      }
                      description={
                        <Space>
                          <Text type="secondary">用户: {group.member_count || 'N/A'}</Text>
                          <Divider type="vertical" />
                          <Text type="secondary">
                            最后活动: {group.last_message_date ? 
                              new Date(group.last_message_date).toLocaleDateString() : 
                              'N/A'
                            }
                          </Text>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="暂无群组数据" />
            )}
          </Card>
        </Col>

        {/* 最近活动 */}
        <Col xs={24} lg={12}>
          <Card title="最近活动">
            {loading ? (
              <Spin />
            ) : activityData?.recent_activities?.length > 0 ? (
              <List
                dataSource={activityData.recent_activities}
                renderItem={(activity: any) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={
                        <Badge 
                          color={activity.activity_type === 'message' ? '#1890ff' : '#52c41a'}
                        />
                      }
                      title={
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Text>{activity.description}</Text>
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            {new Date(activity.timestamp).toLocaleTimeString()}
                          </Text>
                        </div>
                      }
                      description={
                        <Space>
                          <Tag color={activity.activity_type === 'message' ? 'blue' : 'green'}>
                            {activity.activity_type === 'message' ? '消息' : '下载'}
                          </Tag>
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            {activity.group_name}
                          </Text>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="暂无活动数据" />
            )}
          </Card>
        </Col>
      </Row>

      {/* 媒体类型分布 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="媒体类型分布">
            {overviewData?.media_distribution ? (
              <div>
                {Object.entries(overviewData.media_distribution).map(([type, count]: [string, any]) => (
                  <div key={type} style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                      <Text>{type}</Text>
                      <Text strong>{formatNumber(count)}</Text>
                    </div>
                    <Progress 
                      percent={Math.round((count / (Object.values(overviewData.media_distribution) as number[]).reduce((a: number, b: number) => a + b, 0)) * 100)}
                      strokeColor={getMediaTypeColor(type)}
                      size="small"
                    />
                  </div>
                ))}
              </div>
            ) : (
              <Empty description="暂无媒体分布数据" />
            )}
          </Card>
        </Col>

        {/* 系统信息 */}
        <Col xs={24} lg={12}>
          <Card title="系统信息">
            {systemInfo ? (
              <div>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Text>CPU 使用率</Text>
                    <Text strong>{systemInfo.cpu_usage?.toFixed(1) || 0}%</Text>
                  </div>
                  <Progress 
                    percent={systemInfo.cpu_usage || 0} 
                    strokeColor={systemInfo.cpu_usage > 80 ? '#f5222d' : '#52c41a'}
                    size="small"
                  />
                </div>
                
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Text>内存使用率</Text>
                    <Text strong>{systemInfo.memory_usage?.toFixed(1) || 0}%</Text>
                  </div>
                  <Progress 
                    percent={systemInfo.memory_usage || 0} 
                    strokeColor={systemInfo.memory_usage > 80 ? '#f5222d' : '#1890ff'}
                    size="small"
                  />
                </div>
                
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Text>磁盘使用率</Text>
                    <Text strong>{systemInfo.disk_usage?.toFixed(1) || 0}%</Text>
                  </div>
                  <Progress 
                    percent={systemInfo.disk_usage || 0} 
                    strokeColor={systemInfo.disk_usage > 90 ? '#f5222d' : '#722ed1'}
                    size="small"
                  />
                </div>

                <Divider />
                
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text type="secondary">总内存</Text>
                    <Text>{formatFileSize(systemInfo.total_memory || 0)}</Text>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text type="secondary">可用内存</Text>
                    <Text>{formatFileSize(systemInfo.available_memory || 0)}</Text>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text type="secondary">总磁盘空间</Text>
                    <Text>{formatFileSize(systemInfo.total_disk || 0)}</Text>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text type="secondary">可用磁盘空间</Text>
                    <Text>{formatFileSize(systemInfo.free_disk || 0)}</Text>
                  </div>
                </Space>
              </div>
            ) : (
              <Empty description="暂无系统信息" />
            )}
          </Card>
        </Col>
      </Row>

      {/* 下载统计图表 */}
      {downloadStats?.daily_stats?.length > 0 && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={24}>
            <Card title="下载趋势统计">
              <Table
                dataSource={downloadStats.daily_stats}
                columns={[
                  {
                    title: '日期',
                    dataIndex: 'date',
                    key: 'date',
                    render: (date: string) => new Date(date).toLocaleDateString()
                  },
                  {
                    title: '新下载数',
                    dataIndex: 'downloads_count',
                    key: 'downloads_count',
                    render: (count: number) => formatNumber(count)
                  },
                  {
                    title: '下载大小',
                    dataIndex: 'total_size',
                    key: 'total_size',
                    render: (size: number) => formatFileSize(size)
                  },
                  {
                    title: '完成率',
                    dataIndex: 'completion_rate',
                    key: 'completion_rate',
                    render: (rate: number) => (
                      <div style={{ minWidth: 120 }}>
                        <Progress 
                          percent={rate} 
                          size="small" 
                          format={(percent) => `${percent?.toFixed(1)}%`}
                        />
                      </div>
                    )
                  }
                ]}
                pagination={{ pageSize: 7, size: 'small' }}
                size="small"
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 数据更新时间 */}
      {overviewData?.last_updated && (
        <div style={{ textAlign: 'center', marginTop: 24, paddingTop: 16, borderTop: '1px solid #f0f0f0' }}>
          <Text type="secondary">
            数据更新时间: {new Date(overviewData.last_updated).toLocaleString()}
          </Text>
        </div>
      )}
    </div>
  );
};

export default Dashboard;