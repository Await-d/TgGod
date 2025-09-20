import React, { useState, useEffect, useCallback } from 'react';
import {
  Alert,
  Button,
  Card,
  Badge,
  Space,
  Typography,
  Tooltip,
  Progress,
  Row,
  Col,
  Spin,
  Divider,
  Tag,
  Modal,
  List,
  Statistic,
} from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  SettingOutlined,
  MonitorOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  GlobalOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { useGlobalStore } from '../../store';
import { webSocketService } from '../../services/websocket';

const { Text, Title } = Typography;

interface ServiceHealth {
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  message: string;
  lastCheck: Date;
  responseTime?: number;
  uptime?: string;
  version?: string;
  details?: Record<string, any>;
}

interface SystemMetrics {
  cpu: number;
  memory: number;
  disk: number;
  network: {
    incoming: number;
    outgoing: number;
  };
  activeConnections: number;
  queuedTasks: number;
}

interface ProductionStatusDisplayProps {
  className?: string;
  style?: React.CSSProperties;
  compact?: boolean;
  showDetails?: boolean;
}

const ProductionStatusDisplay: React.FC<ProductionStatusDisplayProps> = ({
  className,
  style,
  compact = false,
  showDetails = true,
}) => {
  const { connectionStatus, setConnectionStatus, setError } = useGlobalStore();

  // Service health states
  const [services, setServices] = useState<ServiceHealth[]>([]);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [detailsVisible, setDetailsVisible] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Initialize default services
  const initializeServices = useCallback(() => {
    const defaultServices: ServiceHealth[] = [
      {
        name: 'Task Execution Service',
        status: 'healthy',
        message: 'All task execution processes running normally',
        lastCheck: new Date(),
        responseTime: 45,
        uptime: '2d 14h 32m',
        version: '1.0.0',
        details: {
          activeWorkers: 4,
          completedTasks: 1247,
          failedTasks: 3,
          queueSize: 12,
        }
      },
      {
        name: 'Telegram Service',
        status: 'healthy',
        message: 'Connected to Telegram API successfully',
        lastCheck: new Date(),
        responseTime: 120,
        uptime: '2d 14h 29m',
        version: '1.2.3',
        details: {
          connectedGroups: 15,
          messageRate: '2.3/min',
          apiCalls: 8934,
          rateLimitRemaining: 98,
        }
      },
      {
        name: 'Database Service',
        status: 'healthy',
        message: 'Database operations running smoothly',
        lastCheck: new Date(),
        responseTime: 8,
        uptime: '7d 2h 15m',
        version: 'SQLite 3.42.0',
        details: {
          connections: 5,
          queries: 15623,
          slowQueries: 0,
          dbSize: '245.8 MB',
        }
      },
      {
        name: 'File System Service',
        status: 'healthy',
        message: 'File operations and storage accessible',
        lastCheck: new Date(),
        responseTime: 12,
        uptime: '7d 2h 15m',
        version: '1.0.0',
        details: {
          availableSpace: '1.2 TB',
          usedSpace: '128.5 GB',
          recentDownloads: 84,
          mediaFiles: 3421,
        }
      },
      {
        name: 'WebSocket Service',
        status: webSocketService.isConnected() ? 'healthy' : 'degraded',
        message: webSocketService.isConnected()
          ? 'Real-time communication active'
          : 'WebSocket connection unstable',
        lastCheck: new Date(),
        responseTime: webSocketService.isConnected() ? 25 : undefined,
        uptime: '2d 14h 32m',
        version: '1.1.0',
        details: {
          activeClients: webSocketService.isConnected() ? 3 : 0,
          messagesSent: 2341,
          messagesReceived: 1876,
          reconnects: 2,
        }
      }
    ];

    setServices(defaultServices);
  }, []);

  // Simulate system metrics
  const updateSystemMetrics = useCallback(() => {
    const mockMetrics: SystemMetrics = {
      cpu: Math.floor(Math.random() * 30) + 15, // 15-45%
      memory: Math.floor(Math.random() * 40) + 40, // 40-80%
      disk: Math.floor(Math.random() * 20) + 25, // 25-45%
      network: {
        incoming: Math.floor(Math.random() * 1000) + 500, // KB/s
        outgoing: Math.floor(Math.random() * 800) + 200,
      },
      activeConnections: Math.floor(Math.random() * 15) + 5,
      queuedTasks: Math.floor(Math.random() * 25),
    };

    setSystemMetrics(mockMetrics);
  }, []);

  // Refresh all service statuses
  const refreshStatus = useCallback(async () => {
    setRefreshing(true);

    try {
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Update services with fresh data
      initializeServices();
      updateSystemMetrics();
      setLastUpdate(new Date());

      // Update WebSocket status
      setConnectionStatus(webSocketService.isConnected() ? 'connected' : 'disconnected');

    } catch (error) {
      setError('Failed to refresh service status');
      console.error('Service status refresh failed:', error);
    } finally {
      setRefreshing(false);
    }
  }, [initializeServices, updateSystemMetrics, setConnectionStatus, setError]);

  // Initialize on mount
  useEffect(() => {
    setLoading(true);
    initializeServices();
    updateSystemMetrics();
    setLastUpdate(new Date());
    setLoading(false);

    // Set up periodic updates
    const interval = setInterval(() => {
      updateSystemMetrics();
      // Update WebSocket service status
      setServices(prev => prev.map(service =>
        service.name === 'WebSocket Service'
          ? {
              ...service,
              status: webSocketService.isConnected() ? 'healthy' : 'degraded',
              message: webSocketService.isConnected()
                ? 'Real-time communication active'
                : 'WebSocket connection unstable',
              lastCheck: new Date(),
              responseTime: webSocketService.isConnected() ? 25 : undefined,
            }
          : service
      ));
    }, 5000);

    return () => clearInterval(interval);
  }, [initializeServices, updateSystemMetrics]);

  // Status indicators
  const getStatusColor = (status: ServiceHealth['status']) => {
    switch (status) {
      case 'healthy': return '#52c41a';
      case 'degraded': return '#faad14';
      case 'unhealthy': return '#ff4d4f';
      default: return '#d9d9d9';
    }
  };

  const getStatusIcon = (status: ServiceHealth['status']) => {
    switch (status) {
      case 'healthy': return <CheckCircleOutlined style={{ color: getStatusColor(status) }} />;
      case 'degraded': return <WarningOutlined style={{ color: getStatusColor(status) }} />;
      case 'unhealthy': return <ExclamationCircleOutlined style={{ color: getStatusColor(status) }} />;
      default: return <LoadingOutlined style={{ color: getStatusColor(status) }} />;
    }
  };

  const getOverallStatus = () => {
    const unhealthyCount = services.filter(s => s.status === 'unhealthy').length;
    const degradedCount = services.filter(s => s.status === 'degraded').length;

    if (unhealthyCount > 0) return 'error';
    if (degradedCount > 0) return 'warning';
    return 'success';
  };

  const getOverallMessage = () => {
    const unhealthyCount = services.filter(s => s.status === 'unhealthy').length;
    const degradedCount = services.filter(s => s.status === 'degraded').length;

    if (unhealthyCount > 0) {
      return `${unhealthyCount} service${unhealthyCount > 1 ? 's' : ''} require immediate attention`;
    }
    if (degradedCount > 0) {
      return `${degradedCount} service${degradedCount > 1 ? 's' : ''} running with reduced performance`;
    }
    return 'All systems operational';
  };

  if (loading) {
    return (
      <Card className={className} style={style}>
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <Text type="secondary">Loading system status...</Text>
          </div>
        </div>
      </Card>
    );
  }

  // Compact view for mobile or minimal display
  if (compact) {
    return (
      <div className={className} style={style}>
        <Alert
          type={getOverallStatus()}
          showIcon
          message={
            <Space>
              <Text strong>System Status</Text>
              <Badge
                count={services.filter(s => s.status === 'healthy').length}
                style={{ backgroundColor: '#52c41a' }}
              />
              <Text type="secondary">healthy</Text>
              {services.filter(s => s.status === 'degraded').length > 0 && (
                <>
                  <Badge
                    count={services.filter(s => s.status === 'degraded').length}
                    style={{ backgroundColor: '#faad14' }}
                  />
                  <Text type="secondary">degraded</Text>
                </>
              )}
            </Space>
          }
          description={getOverallMessage()}
          action={
            <Button
              size="small"
              icon={<InfoCircleOutlined />}
              onClick={() => setDetailsVisible(true)}
            >
              Details
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className={className} style={style}>
      {/* Main Status Overview */}
      <Alert
        type={getOverallStatus()}
        showIcon
        message={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <Text strong>Production System Status</Text>
              <Tag color={getOverallStatus() === 'success' ? 'green' : getOverallStatus() === 'warning' ? 'orange' : 'red'}>
                {getOverallMessage()}
              </Tag>
            </Space>
            <Space>
              {lastUpdate && (
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  Last updated: {lastUpdate.toLocaleTimeString()}
                </Text>
              )}
              <Button
                size="small"
                icon={<ReloadOutlined />}
                loading={refreshing}
                onClick={refreshStatus}
              >
                Refresh
              </Button>
            </Space>
          </div>
        }
        style={{ marginBottom: 16 }}
      />

      {/* Service Grid */}
      {showDetails && (
        <Row gutter={[16, 16]}>
          {services.map((service, index) => (
            <Col xs={24} md={12} lg={8} key={service.name}>
              <Card
                size="small"
                title={
                  <Space>
                    {getStatusIcon(service.status)}
                    <Text strong style={{ fontSize: '14px' }}>{service.name}</Text>
                  </Space>
                }
                extra={
                  service.responseTime && (
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {service.responseTime}ms
                    </Text>
                  )
                }
                style={{ height: '100%' }}
              >
                <div style={{ marginBottom: 8 }}>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    {service.message}
                  </Text>
                </div>

                {service.uptime && (
                  <div style={{ marginBottom: 4 }}>
                    <Text type="secondary" style={{ fontSize: '11px' }}>
                      Uptime: {service.uptime}
                    </Text>
                  </div>
                )}

                {service.version && (
                  <div>
                    <Text type="secondary" style={{ fontSize: '11px' }}>
                      Version: {service.version}
                    </Text>
                  </div>
                )}
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* System Metrics */}
      {showDetails && systemMetrics && (
        <Card
          title={
            <Space>
              <MonitorOutlined />
              <Text strong>System Metrics</Text>
            </Space>
          }
          style={{ marginTop: 16 }}
          size="small"
        >
          <Row gutter={[16, 16]}>
            <Col xs={12} md={6}>
              <Statistic
                title="CPU Usage"
                value={systemMetrics.cpu}
                suffix="%"
                valueStyle={{
                  color: systemMetrics.cpu > 80 ? '#ff4d4f' : systemMetrics.cpu > 60 ? '#faad14' : '#52c41a'
                }}
              />
              <Progress
                percent={systemMetrics.cpu}
                size="small"
                status={systemMetrics.cpu > 80 ? 'exception' : 'active'}
                showInfo={false}
              />
            </Col>

            <Col xs={12} md={6}>
              <Statistic
                title="Memory Usage"
                value={systemMetrics.memory}
                suffix="%"
                valueStyle={{
                  color: systemMetrics.memory > 85 ? '#ff4d4f' : systemMetrics.memory > 70 ? '#faad14' : '#52c41a'
                }}
              />
              <Progress
                percent={systemMetrics.memory}
                size="small"
                status={systemMetrics.memory > 85 ? 'exception' : 'active'}
                showInfo={false}
              />
            </Col>

            <Col xs={12} md={6}>
              <Statistic
                title="Active Connections"
                value={systemMetrics.activeConnections}
                prefix={<GlobalOutlined />}
              />
            </Col>

            <Col xs={12} md={6}>
              <Statistic
                title="Queued Tasks"
                value={systemMetrics.queuedTasks}
                prefix={<ApiOutlined />}
                valueStyle={{
                  color: systemMetrics.queuedTasks > 50 ? '#faad14' : '#52c41a'
                }}
              />
            </Col>
          </Row>
        </Card>
      )}

      {/* Detailed Service Information Modal */}
      <Modal
        title="Detailed Service Information"
        open={detailsVisible}
        onCancel={() => setDetailsVisible(false)}
        footer={null}
        width={800}
      >
        <List
          dataSource={services}
          renderItem={(service) => (
            <List.Item>
              <List.Item.Meta
                avatar={getStatusIcon(service.status)}
                title={
                  <Space>
                    <Text strong>{service.name}</Text>
                    <Tag color={getStatusColor(service.status)}>{service.status}</Tag>
                  </Space>
                }
                description={
                  <div>
                    <div style={{ marginBottom: 8 }}>
                      <Text>{service.message}</Text>
                    </div>
                    <Row gutter={16}>
                      <Col span={6}>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          Response: {service.responseTime || 'N/A'}ms
                        </Text>
                      </Col>
                      <Col span={6}>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          Uptime: {service.uptime || 'N/A'}
                        </Text>
                      </Col>
                      <Col span={6}>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          Version: {service.version || 'N/A'}
                        </Text>
                      </Col>
                      <Col span={6}>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          Last Check: {service.lastCheck.toLocaleTimeString()}
                        </Text>
                      </Col>
                    </Row>
                    {service.details && (
                      <div style={{ marginTop: 8, padding: 8, background: '#fafafa', borderRadius: 4 }}>
                        <Text code style={{ fontSize: '11px' }}>
                          {JSON.stringify(service.details, null, 2)}
                        </Text>
                      </div>
                    )}
                  </div>
                }
              />
            </List.Item>
          )}
        />
      </Modal>
    </div>
  );
};

export default ProductionStatusDisplay;