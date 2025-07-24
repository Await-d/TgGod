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
import QuickTaskExecutor from '../components/TaskExecution/QuickTaskExecutor';
import TaskLogViewer from '../components/TaskExecution/TaskLogViewer';

const { Title, Text } = Typography;

const Dashboard: React.FC = () => {
  // CSS animations
  React.useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
      }
      @keyframes ripple {
        0% { transform: scale(1); opacity: 1; }
        100% { transform: scale(2); opacity: 0; }
      }
    `;
    document.head.appendChild(style);
    return () => {
      document.head.removeChild(style);
    };
  }, []);
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
        {/* 快速任务执行 */}
        <Col xs={24} lg={8}>
          <QuickTaskExecutor onTaskCreated={() => loadData()} />
        </Col>
        
        {/* 群组摘要 */}
        <Col xs={24} lg={8}>
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
        <Col xs={24} lg={8}>
          <Card 
            title="实时活动" 
            extra={
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <div 
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    backgroundColor: '#52c41a',
                    marginRight: 8,
                    animation: 'pulse 2s infinite'
                  }}
                />
                <Text type="secondary">实时更新</Text>
              </div>
            }
          >
            {loading ? (
              <Spin />
            ) : activityData?.recent_activities?.length > 0 ? (
              <List
                dataSource={activityData.recent_activities}
                renderItem={(activity: any, index: number) => (
                  <List.Item
                    style={{
                      padding: '12px 0',
                      borderLeft: index === 0 ? '3px solid #1890ff' : 'none',
                      paddingLeft: index === 0 ? 12 : 0,
                      backgroundColor: index === 0 ? '#f6ffed' : 'transparent',
                      borderRadius: index === 0 ? 4 : 0,
                      marginBottom: index === 0 ? 8 : 0,
                      transition: 'all 0.3s ease'
                    }}
                  >
                    <List.Item.Meta
                      avatar={
                        <Badge 
                          color={activity.activity_type === 'message' ? '#1890ff' : '#52c41a'}
                        />
                      }
                      title={
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Text style={{ fontWeight: index === 0 ? 'bold' : 'normal' }}>
                            {activity.description}
                          </Text>
                          <Space>
                            {index === 0 && <Tag color="orange" style={{ fontSize: '10px', padding: '1px 4px' }}>新</Tag>}
                            <Text type="secondary" style={{ fontSize: '12px' }}>
                              {new Date(activity.timestamp).toLocaleTimeString()}
                            </Text>
                          </Space>
                        </div>
                      }
                      description={
                        <Space>
                          <Tag 
                            color={activity.activity_type === 'message' ? 'blue' : 'green'}
                            style={{ fontSize: '11px' }}
                          >
                            {activity.activity_type === 'message' ? '💬 消息' : '📥 下载'}
                          </Tag>
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            📁 {activity.group_name}
                          </Text>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty 
                description="暂无活动数据" 
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* 媒体类型分布图表 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="媒体类型分布" extra={<BarChartOutlined />}>
            {overviewData?.media_distribution ? (
              <div>
                {Object.entries(overviewData.media_distribution).map(([type, count]: [string, any]) => {
                  const total = (Object.values(overviewData.media_distribution) as number[]).reduce((a: number, b: number) => a + b, 0);
                  const percentage = Math.round((count / total) * 100);
                  return (
                    <div key={type} style={{ marginBottom: 16 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                        <Space>
                          <div 
                            style={{ 
                              width: 12, 
                              height: 12, 
                              borderRadius: '50%', 
                              backgroundColor: getMediaTypeColor(type) 
                            }}
                          />
                          <Text>{type}</Text>
                        </Space>
                        <Space>
                          <Text strong>{formatNumber(count)}</Text>
                          <Text type="secondary">({percentage}%)</Text>
                        </Space>
                      </div>
                      <Progress 
                        percent={percentage}
                        strokeColor={getMediaTypeColor(type)}
                        size="small"
                        showInfo={false}
                      />
                    </div>
                  );
                })}
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
                    <Text strong>{typeof systemInfo.cpu_usage === 'number' ? systemInfo.cpu_usage.toFixed(1) : (systemInfo.cpu_percent?.toFixed(1) || '0')}%</Text>
                  </div>
                  <Progress 
                    percent={systemInfo.cpu_usage || systemInfo.cpu_percent || 0} 
                    strokeColor={(systemInfo.cpu_usage || systemInfo.cpu_percent || 0) > 80 ? '#f5222d' : '#52c41a'}
                    size="small"
                  />
                </div>
                
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Text>内存使用率</Text>
                    <Text strong>{typeof systemInfo.memory_usage === 'number' ? systemInfo.memory_usage.toFixed(1) : (systemInfo.memory?.usage_percent?.toFixed(1) || '0')}%</Text>
                  </div>
                  <Progress 
                    percent={systemInfo.memory_usage || systemInfo.memory?.usage_percent || 0} 
                    strokeColor={(systemInfo.memory_usage || systemInfo.memory?.usage_percent || 0) > 80 ? '#f5222d' : '#1890ff'}
                    size="small"
                  />
                </div>
                
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Text>磁盘使用率</Text>
                    <Text strong>{typeof systemInfo.disk_usage_percent === 'number' ? systemInfo.disk_usage_percent.toFixed(1) : (systemInfo.disk_usage?.usage_percent?.toFixed(1) || '0')}%</Text>
                  </div>
                  <Progress 
                    percent={systemInfo.disk_usage_percent || systemInfo.disk_usage?.usage_percent || 0} 
                    strokeColor={(systemInfo.disk_usage_percent || systemInfo.disk_usage?.usage_percent || 0) > 90 ? '#f5222d' : '#722ed1'}
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

      {/* 下载趋势图表 */}
      {downloadStats?.daily_stats?.length > 0 && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={16}>
            <Card title="下载趋势图表" extra={<BarChartOutlined />}>
              <div style={{ height: 300, position: 'relative' }}>
                {/* 简单的折线图实现 */}
                <div style={{ display: 'flex', height: '100%', alignItems: 'end', padding: '20px 0' }}>
                  {downloadStats.daily_stats.slice(-7).map((stat: any, index: number) => {
                    const maxCount = Math.max(...downloadStats.daily_stats.map((s: any) => s.downloads_count || 0));
                    const height = maxCount > 0 ? (stat.downloads_count / maxCount) * 200 : 0;
                    return (
                      <div key={index} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '0 4px' }}>
                        <Tooltip title={`${new Date(stat.date).toLocaleDateString()}: ${stat.downloads_count} 下载`}>
                          <div
                            style={{
                              width: '80%',
                              height: `${height}px`,
                              backgroundColor: '#1890ff',
                              borderRadius: '4px 4px 0 0',
                              marginBottom: 8,
                              transition: 'all 0.3s ease',
                              cursor: 'pointer'
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.backgroundColor = '#40a9ff';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.backgroundColor = '#1890ff';
                            }}
                          />
                        </Tooltip>
                        <Text style={{ fontSize: '12px', textAlign: 'center' }}>
                          {new Date(stat.date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
                        </Text>
                        <Text style={{ fontSize: '10px', color: '#999' }}>
                          {stat.downloads_count}
                        </Text>
                      </div>
                    );
                  })}
                </div>
              </div>
            </Card>
          </Col>
          
          <Col xs={24} lg={8}>
            <Card title="下载统计表格">
              <Table
                dataSource={downloadStats.daily_stats.slice(-5)}
                columns={[
                  {
                    title: '日期',
                    dataIndex: 'date',
                    key: 'date',
                    render: (date: string) => new Date(date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
                  },
                  {
                    title: '下载数',
                    dataIndex: 'downloads_count',
                    key: 'downloads_count',
                    render: (count: number) => formatNumber(count)
                  },
                  {
                    title: '大小',
                    dataIndex: 'total_size',
                    key: 'total_size',
                    render: (size: number) => formatFileSize(size)
                  }
                ]}
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
        </Row>
      )}
      
      {/* 任务执行日志 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <TaskLogViewer 
            height={300}
            autoRefresh={true}
            showFilters={true}
          />
        </Col>
      </Row>

      {/* 系统资源使用趋势 */}
      {systemInfo && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={24}>
            <Card title="系统资源监控" extra={<DatabaseOutlined />}>
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={8}>
                  <div style={{ textAlign: 'center', padding: '20px' }}>
                    <div style={{ position: 'relative', display: 'inline-block' }}>
                      <Progress
                        type="circle"
                        percent={systemInfo.cpu_usage || systemInfo.cpu_percent || 0}
                        format={percent => (
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{percent?.toFixed(1)}%</div>
                            <div style={{ fontSize: '12px', color: '#666' }}>CPU</div>
                          </div>
                        )}
                        strokeColor={(systemInfo.cpu_usage || systemInfo.cpu_percent || 0) > 80 ? '#ff4d4f' : '#52c41a'}
                      />
                    </div>
                  </div>
                </Col>
                
                <Col xs={24} sm={8}>
                  <div style={{ textAlign: 'center', padding: '20px' }}>
                    <div style={{ position: 'relative', display: 'inline-block' }}>
                      <Progress
                        type="circle"
                        percent={systemInfo.memory_usage || systemInfo.memory?.usage_percent || 0}
                        format={percent => (
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{percent?.toFixed(1)}%</div>
                            <div style={{ fontSize: '12px', color: '#666' }}>内存</div>
                          </div>
                        )}
                        strokeColor={(systemInfo.memory_usage || systemInfo.memory?.usage_percent || 0) > 80 ? '#ff4d4f' : '#1890ff'}
                      />
                    </div>
                  </div>
                </Col>
                
                <Col xs={24} sm={8}>
                  <div style={{ textAlign: 'center', padding: '20px' }}>
                    <div style={{ position: 'relative', display: 'inline-block' }}>
                      <Progress
                        type="circle"
                        percent={systemInfo.disk_usage_percent || systemInfo.disk_usage?.usage_percent || 0}
                        format={percent => (
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{percent?.toFixed(1)}%</div>
                            <div style={{ fontSize: '12px', color: '#666' }}>磁盘</div>
                          </div>
                        )}
                        strokeColor={(systemInfo.disk_usage_percent || systemInfo.disk_usage?.usage_percent || 0) > 90 ? '#ff4d4f' : '#722ed1'}
                      />
                    </div>
                  </div>
                </Col>
              </Row>
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