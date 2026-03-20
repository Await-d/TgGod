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
  Table,
  Tag,
  Space,
  Tooltip,
  Empty,
  Divider
} from 'antd';
import { useIsMobile } from '../hooks/useMobileGestures';
import {
  TeamOutlined,
  MessageOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
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
import PageContainer from '../components/Layout/PageContainer';
import QuickTaskExecutor from '../components/TaskExecution/QuickTaskExecutor';
import TaskLogViewer from '../components/TaskExecution/TaskLogViewer';
import SystemLogViewer from '../components/SystemLog/SystemLogViewer';
import './Dashboard.css';

const { Text } = Typography;

const Dashboard: React.FC = () => {
  const isMobile = useIsMobile();

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
    <PageContainer
      title="仪表板"
      description="系统概览和统计数据"
      breadcrumb={[{ title: '仪表板' }]}
      loading={loading}
      error={error}
      onRetry={() => loadData(true)}
      extra={
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          onClick={() => loadData(true)}
          loading={loading}
          block={isMobile}
        >
          刷新数据
        </Button>
      }
    >
      {/* 概览统计卡片 */}
      <Row gutter={[16, 16]} className="dashboard-section grid-responsive">
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
      <Row gutter={[16, 16]} className="dashboard-section">
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
              className="dashboard-progress"
            />
          </Card>
        </Col>
      </Row>

      {/* 今日统计 */}
      <Row gutter={[16, 16]} className="dashboard-section">
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
            size={isMobile ? "small" : "default"}
            extra={
              <Space>
                <Text type="secondary">{isMobile ? "活跃群组" : "前10个活跃群组"}</Text>
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
                        <div className="dashboard-group-item-header">
                          <Text strong>{group.title}</Text>
                          <Badge 
                            count={group.message_count} 
                            className="dashboard-badge-success"
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
            size={isMobile ? "small" : "default"}
            extra={
              <div className="dashboard-activity-extra">
                <div className="dashboard-activity-dot" />
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
                    className={index === 0
                      ? 'dashboard-activity-item dashboard-activity-item-highlight'
                      : 'dashboard-activity-item'
                    }
                  >
                    <List.Item.Meta
                      avatar={
                        <Badge 
                          color={activity.activity_type === 'message' ? '#1890ff' : '#52c41a'}
                        />
                      }
                      title={
                        <div className="dashboard-activity-header">
                          <Text
                            className={index === 0
                              ? 'dashboard-activity-title dashboard-activity-title-highlight'
                              : 'dashboard-activity-title'
                            }
                          >
                            {activity.description}
                          </Text>
                          <Space className="dashboard-activity-meta">
                            {index === 0 && <Tag color="orange" className="dashboard-activity-new-tag">新</Tag>}
                            <Text type="secondary" className="dashboard-activity-time">
                              {new Date(activity.timestamp).toLocaleTimeString()}
                            </Text>
                          </Space>
                        </div>
                      }
                      description={
                        <Space className="dashboard-activity-description">
                          <Tag 
                            color={activity.activity_type === 'message' ? 'blue' : 'green'}
                            className="dashboard-activity-type-tag"
                          >
                            {activity.activity_type === 'message' ? '💬 消息' : '📥 下载'}
                          </Tag>
                          <Text type="secondary" className="dashboard-activity-group">
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
      <Row gutter={[16, 16]} className="dashboard-section-top">
        <Col xs={24} lg={12}>
          <Card title="媒体类型分布" size={isMobile ? "small" : "default"} extra={<BarChartOutlined />}>
            {overviewData?.media_distribution ? (
              <div>
                {Object.entries(overviewData.media_distribution).map(([type, count]: [string, any]) => {
                  const total = (Object.values(overviewData.media_distribution) as number[]).reduce((a: number, b: number) => a + b, 0);
                  const percentage = Math.round((count / total) * 100);
                  return (
                    <div key={type} className="dashboard-media-item">
                      <div className="dashboard-media-header">
                        <Space className="dashboard-media-label">
                          <div
                            className="dashboard-media-dot"
                            style={{ backgroundColor: getMediaTypeColor(type) }}
                          />
                          <Text>{type}</Text>
                        </Space>
                        <Space className="dashboard-media-stats">
                          <Text strong>{formatNumber(count)}</Text>
                          <Text type="secondary">({percentage}%)</Text>
                        </Space>
                      </div>
                      <Progress 
                        className="dashboard-media-progress"
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
          <Card title="系统信息" size={isMobile ? "small" : "default"}>
            {systemInfo ? (
              <div>
                <div className="dashboard-system-block">
                  <div className="dashboard-system-header">
                    <Text>CPU 使用率</Text>
                    <Text strong>{typeof systemInfo.cpu_usage === 'number' ? systemInfo.cpu_usage.toFixed(1) : (systemInfo.cpu_percent?.toFixed(1) || '0')}%</Text>
                  </div>
                  <Progress 
                    className="dashboard-system-progress"
                    percent={systemInfo.cpu_usage || systemInfo.cpu_percent || 0} 
                    strokeColor={(systemInfo.cpu_usage || systemInfo.cpu_percent || 0) > 80 ? '#f5222d' : '#52c41a'}
                    size="small"
                  />
                </div>
                
                <div className="dashboard-system-block">
                  <div className="dashboard-system-header">
                    <Text>内存使用率</Text>
                    <Text strong>{typeof systemInfo.memory_usage === 'number' ? systemInfo.memory_usage.toFixed(1) : (systemInfo.memory?.usage_percent?.toFixed(1) || '0')}%</Text>
                  </div>
                  <Progress 
                    className="dashboard-system-progress"
                    percent={systemInfo.memory_usage || systemInfo.memory?.usage_percent || 0} 
                    strokeColor={(systemInfo.memory_usage || systemInfo.memory?.usage_percent || 0) > 80 ? '#f5222d' : '#1890ff'}
                    size="small"
                  />
                </div>
                
                <div className="dashboard-system-block">
                  <div className="dashboard-system-header">
                    <Text>磁盘使用率</Text>
                    <Text strong>{typeof systemInfo.disk_usage_percent === 'number' ? systemInfo.disk_usage_percent.toFixed(1) : (systemInfo.disk_usage?.usage_percent?.toFixed(1) || '0')}%</Text>
                  </div>
                  <Progress 
                    className="dashboard-system-progress"
                    percent={systemInfo.disk_usage_percent || systemInfo.disk_usage?.usage_percent || 0} 
                    strokeColor={(systemInfo.disk_usage_percent || systemInfo.disk_usage?.usage_percent || 0) > 90 ? '#f5222d' : '#722ed1'}
                    size="small"
                  />
                </div>

                <Divider />
                
                <Space direction="vertical" size="small" className="dashboard-system-summary">
                  <div className="dashboard-system-summary-row">
                    <Text type="secondary">总内存</Text>
                    <Text>{formatFileSize(systemInfo.total_memory || 0)}</Text>
                  </div>
                  <div className="dashboard-system-summary-row">
                    <Text type="secondary">可用内存</Text>
                    <Text>{formatFileSize(systemInfo.available_memory || 0)}</Text>
                  </div>
                  <div className="dashboard-system-summary-row">
                    <Text type="secondary">总磁盘空间</Text>
                    <Text>{formatFileSize(systemInfo.total_disk || 0)}</Text>
                  </div>
                  <div className="dashboard-system-summary-row">
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
            <Card title="下载趋势图表" size={isMobile ? "small" : "default"} extra={<BarChartOutlined />}>
              <div style={{ height: isMobile ? 200 : 300, position: 'relative' }}>
                {/* 简单的折线图实现 */}
                <div style={{ display: 'flex', height: '100%', alignItems: 'end', padding: '20px 0' }}>
                  {downloadStats.daily_stats.slice(-7).map((stat: any, index: number) => {
                    const maxCount = Math.max(...downloadStats.daily_stats.map((s: any) => s.downloads_count || 0));
                    const height = maxCount > 0 ? (stat.downloads_count / maxCount) * (isMobile ? 120 : 200) : 0;
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
            <Card title="下载统计表格" size={isMobile ? "small" : "default"}>
              <div className="dashboard-table-wrapper">
                <Table
                  dataSource={downloadStats.daily_stats.slice(isMobile ? -3 : -5)}
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
                    ...(!isMobile ? [{
                      title: '大小',
                      dataIndex: 'total_size',
                      key: 'total_size',
                      render: (size: number) => formatFileSize(size)
                    }] : [])
                  ]}
                  pagination={false}
                  size="small"
                />
              </div>
            </Card>
          </Col>
        </Row>
      )}
      
      {/* 日志查看器 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={12}>
          <TaskLogViewer 
            height={isMobile ? 200 : 300}
            autoRefresh={true}
            showFilters={!isMobile}
          />
        </Col>
        <Col xs={24} xl={12}>
          <SystemLogViewer 
            height={isMobile ? 200 : 300}
            autoRefresh={true}
            showFilters={!isMobile}
            logType="system"
          />
        </Col>
      </Row>

      {/* 系统资源使用趋势 */}
      {systemInfo && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={24}>
            <Card title="系统资源监控" size={isMobile ? "small" : "default"} extra={<DatabaseOutlined />}>
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={8}>
                  <div style={{ textAlign: 'center', padding: isMobile ? '10px' : '20px' }}>
                    <div style={{ position: 'relative', display: 'inline-block' }}>
                      <Progress
                        type="circle"
                        percent={systemInfo.cpu_usage || systemInfo.cpu_percent || 0}
                        format={percent => (
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: isMobile ? '14px' : '16px', fontWeight: 'bold' }}>{percent?.toFixed(1)}%</div>
                            <div style={{ fontSize: isMobile ? '10px' : '12px', color: '#666' }}>CPU</div>
                          </div>
                        )}
                        strokeColor={(systemInfo.cpu_usage || systemInfo.cpu_percent || 0) > 80 ? '#ff4d4f' : '#52c41a'}
                        size={isMobile ? 80 : 120}
                      />
                    </div>
                  </div>
                </Col>
                
                <Col xs={24} sm={8}>
                  <div style={{ textAlign: 'center', padding: isMobile ? '10px' : '20px' }}>
                    <div style={{ position: 'relative', display: 'inline-block' }}>
                      <Progress
                        type="circle"
                        percent={systemInfo.memory_usage || systemInfo.memory?.usage_percent || 0}
                        format={percent => (
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: isMobile ? '14px' : '16px', fontWeight: 'bold' }}>{percent?.toFixed(1)}%</div>
                            <div style={{ fontSize: isMobile ? '10px' : '12px', color: '#666' }}>内存</div>
                          </div>
                        )}
                        strokeColor={(systemInfo.memory_usage || systemInfo.memory?.usage_percent || 0) > 80 ? '#ff4d4f' : '#1890ff'}
                        size={isMobile ? 80 : 120}
                      />
                    </div>
                  </div>
                </Col>
                
                <Col xs={24} sm={8}>
                  <div style={{ textAlign: 'center', padding: isMobile ? '10px' : '20px' }}>
                    <div style={{ position: 'relative', display: 'inline-block' }}>
                      <Progress
                        type="circle"
                        percent={systemInfo.disk_usage_percent || systemInfo.disk_usage?.usage_percent || 0}
                        format={percent => (
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: isMobile ? '14px' : '16px', fontWeight: 'bold' }}>{percent?.toFixed(1)}%</div>
                            <div style={{ fontSize: isMobile ? '10px' : '12px', color: '#666' }}>磁盘</div>
                          </div>
                        )}
                        strokeColor={(systemInfo.disk_usage_percent || systemInfo.disk_usage?.usage_percent || 0) > 90 ? '#ff4d4f' : '#722ed1'}
                        size={isMobile ? 80 : 120}
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
    </PageContainer>
  );
};

export default Dashboard;
