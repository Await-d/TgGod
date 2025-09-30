import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Alert,
  Button,
  Card,
  Badge,
  Space,
  Typography,
  Progress,
  Row,
  Col,
  Spin,
  Tag,
  Modal,
  List,
  Statistic,
  // Tooltip,  // 未使用，已注释
  // Divider   // 未使用，已注释
} from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  MonitorOutlined,
  GlobalOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { useGlobalStore } from '../../store';
import { webSocketService } from '../../services/websocket';
import { serviceHealthApi } from '../../services/apiService';
import {
  ServiceHealthEntry,
  ServiceHealthResponse,
  ServiceStatusSnapshotResponse,
  ServiceHealthCheckResponse,
  ServicesHealthData,
} from '../../types';

const { Text /* Title */ } = Typography; // Title 暂时未使用

type DisplayStatus = 'healthy' | 'warning' | 'degraded' | 'unhealthy' | 'unknown';

interface ServiceHealthDisplay {
  key: string;
  name: string;
  status: DisplayStatus;
  message: string;
  lastCheck: Date | null;
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
  const { setConnectionStatus, setError } = useGlobalStore();

  // Service health states
  const [services, setServices] = useState<ServiceHealthDisplay[]>([]);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [detailsVisible, setDetailsVisible] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [overallStatus, setOverallStatus] = useState<DisplayStatus>('unknown');
  const [serviceCounts, setServiceCounts] = useState({ healthy: 0, warning: 0, error: 0 });

  const serviceNameMap: Record<string, string> = useMemo(() => ({
    ffmpeg: 'FFmpeg 工具',
    fonts: '字体资源',
    python_deps: 'Python 依赖',
    system_tools: '系统工具',
    system_monitoring: '系统监控组件',
    disk_space: '磁盘空间',
    memory: '内存监控',
    cpu: 'CPU 监控',
    network: '网络状态',
    task_execution: '任务执行服务',
    task_execution_service: '任务执行服务',
    telegram: 'Telegram 服务',
    database: '数据库服务',
    file_system: '文件系统服务',
  }), []);

  const normalizeStatus = useCallback((status?: string, isHealthy?: boolean): DisplayStatus => {
    const raw = (status || '').toLowerCase();

    if (raw === 'healthy') return 'healthy';
    if (raw === 'warning' || raw === 'degraded') return 'warning';
    if (raw === 'error' || raw === 'unhealthy') return 'unhealthy';
    if (isHealthy === true) return 'healthy';
    if (isHealthy === false) return 'unhealthy';
    return 'unknown';
  }, []);

  const clampPercent = useCallback((value?: number): number | undefined => {
    if (value === undefined) return undefined;
    return Math.max(0, Math.min(100, Math.round(value)));
  }, []);

  const extractSystemMetrics = useCallback((servicesMap: Record<string, ServiceHealthEntry>): SystemMetrics | null => {
    const toNumber = (value: unknown): number | undefined => {
      const num = Number(value);
      return Number.isFinite(num) ? num : undefined;
    };

    const cpuInfo = servicesMap.cpu?.details || servicesMap.cpu;
    const memoryInfo = servicesMap.memory?.details || servicesMap.memory;
    const diskInfo = servicesMap.disk_space?.details || servicesMap.disk_space;
    const networkInfo = servicesMap.network?.details || servicesMap.network;
    const taskInfo = servicesMap.task_execution_service?.details || servicesMap.task_execution?.details || servicesMap.task_execution;

    const cpuUsage = clampPercent(
      toNumber(cpuInfo?.cpu_percent ?? cpuInfo?.usage_percent ?? cpuInfo?.value)
    );
    const memoryUsage = clampPercent(
      toNumber(memoryInfo?.usage_percent ?? memoryInfo?.used_percent ?? memoryInfo?.value)
    );
    const diskUsage = clampPercent(
      toNumber(diskInfo?.usage_percent ?? diskInfo?.used_percent ?? diskInfo?.value)
    );

    const activeConnections = toNumber(networkInfo?.connections ?? networkInfo?.active_connections);
    const queuedTasks = toNumber(taskInfo?.queueSize ?? taskInfo?.queued_tasks ?? taskInfo?.pendingTasks);
    const incoming = toNumber(networkInfo?.bytes_recv ?? networkInfo?.incoming) || 0;
    const outgoing = toNumber(networkInfo?.bytes_sent ?? networkInfo?.outgoing) || 0;

    const hasMetrics = cpuUsage !== undefined || memoryUsage !== undefined || diskUsage !== undefined || activeConnections !== undefined || queuedTasks !== undefined;

    if (!hasMetrics) {
      return null;
    }

    return {
      cpu: cpuUsage ?? 0,
      memory: memoryUsage ?? 0,
      disk: diskUsage ?? 0,
      network: {
        incoming,
        outgoing,
      },
      activeConnections: activeConnections ?? 0,
      queuedTasks: queuedTasks ?? 0,
    };
  }, [clampPercent]);

  const augmentWithWebSocket = useCallback((list: ServiceHealthDisplay[]): ServiceHealthDisplay[] => {
    const connected = webSocketService.isConnected();
    const websocketEntry: ServiceHealthDisplay = {
      key: 'websocket',
      name: 'WebSocket 连接',
      status: connected ? 'healthy' : 'warning',
      message: connected ? '实时通信正常' : 'WebSocket 连接不稳定',
      lastCheck: new Date(),
      responseTime: connected ? 0 : undefined,
      details: {
        connected,
      },
    };

    const exists = list.findIndex(item => item.key === websocketEntry.key);
    if (exists >= 0) {
      const next = [...list];
      next[exists] = websocketEntry;
      return next;
    }

    return [...list, websocketEntry];
  }, []);

  const transformServices = useCallback((
    servicesMap: Record<string, ServiceHealthEntry>,
    defaultLastCheck?: string
  ): ServiceHealthDisplay[] => (
    Object.entries(servicesMap || {}).map(([key, value]) => {
      const status = normalizeStatus(value?.status, value?.is_healthy);

      const message =
        value?.status_message ||
        value?.message ||
        (value?.is_healthy === true ? '运行正常' : value?.is_healthy === false ? '检测到异常' : '状态未知');

      const lastCheck = value?.last_checked
        ? new Date(value.last_checked)
        : defaultLastCheck
          ? new Date(defaultLastCheck)
          : null;

      const displayName = serviceNameMap[key] || value?.service_name || key;

      return {
        key,
        name: displayName,
        status,
        message,
        lastCheck,
        responseTime: value?.response_time_ms,
        uptime: typeof value?.details?.uptime === 'string' ? value.details.uptime : undefined,
        version: value?.details?.version,
        details: value?.details,
      };
    })
  ), [normalizeStatus, serviceNameMap]);

  const fetchServiceHealth = useCallback(async ({ force = false, showLoader = false }: { force?: boolean; showLoader?: boolean } = {}) => {
    if (showLoader) {
      setLoading(true);
    }

    if (force) {
      setRefreshing(true);
    }

    try {
      let servicesData: ServicesHealthData | undefined;
      let statusSnapshot: ServiceStatusSnapshotResponse | null = null;

      if (force) {
        const response: ServiceHealthCheckResponse = await serviceHealthApi.forceHealthCheck();
        servicesData = response.data;
      } else {
        statusSnapshot = await serviceHealthApi.getCurrentStatus();
        servicesData = statusSnapshot.data?.details;
        if (!servicesData || !servicesData.services || Object.keys(servicesData.services).length === 0) {
          const detailed: ServiceHealthResponse = await serviceHealthApi.getServicesHealth();
          servicesData = detailed.data;
        }
      }

      if (!servicesData) {
        throw new Error('服务健康数据为空');
      }

      const list = transformServices(servicesData.services || {}, servicesData.check_time);
      const augmentedList = augmentWithWebSocket(list);
      const augmentedCounts = augmentedList.reduce(
        (acc, service) => {
          if (service.status === 'healthy') acc.healthy += 1;
          else if (service.status === 'warning' || service.status === 'degraded') acc.warning += 1;
          else if (service.status === 'unhealthy') acc.error += 1;
          return acc;
        },
        { healthy: 0, warning: 0, error: 0 }
      );

      setServices(augmentedList);
      setServiceCounts(augmentedCounts);

      const metrics = extractSystemMetrics(servicesData.services || {});
      setSystemMetrics(metrics);

      const overall = normalizeStatus(
        servicesData.overall_status || statusSnapshot?.data?.status,
        servicesData.overall_status ? servicesData.overall_status === 'healthy' : undefined
      );
      setOverallStatus(overall);

      const checkTime = servicesData.check_time || statusSnapshot?.data?.last_check;
      setLastUpdate(checkTime ? new Date(checkTime) : new Date());

      setConnectionStatus(webSocketService.isConnected() ? 'connected' : 'disconnected');
      setError(null);
    } catch (error) {
      console.error('获取服务健康状态失败:', error);
      setError('获取服务健康状态失败');
    } finally {
      if (force) {
        setRefreshing(false);
      }
      if (showLoader) {
        setLoading(false);
      }
    }
  }, [augmentWithWebSocket, extractSystemMetrics, normalizeStatus, setConnectionStatus, setError, transformServices]);

  // Refresh all service statuses
  const refreshStatus = useCallback(async () => {
    await fetchServiceHealth({ force: true });
  }, [fetchServiceHealth]);

  // Initialize on mount
  useEffect(() => {
    fetchServiceHealth({ showLoader: true });

    const interval = setInterval(() => {
      fetchServiceHealth();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchServiceHealth]);

  // Status indicators
  const getStatusColor = (status: DisplayStatus) => {
    switch (status) {
      case 'healthy': return '#52c41a';
      case 'warning':
      case 'degraded':
        return '#faad14';
      case 'unhealthy': return '#ff4d4f';
      default: return '#d9d9d9';
    }
  };

  const getStatusIcon = (status: DisplayStatus) => {
    switch (status) {
      case 'healthy': return <CheckCircleOutlined style={{ color: getStatusColor(status) }} />;
      case 'warning':
      case 'degraded':
        return <WarningOutlined style={{ color: getStatusColor(status) }} />;
      case 'unhealthy': return <ExclamationCircleOutlined style={{ color: getStatusColor(status) }} />;
      default: return <LoadingOutlined style={{ color: getStatusColor(status) }} />;
    }
  };

  const getAlertStatus = () => {
    switch (overallStatus) {
      case 'healthy':
        return 'success';
      case 'warning':
      case 'degraded':
        return 'warning';
      case 'unhealthy':
        return 'error';
      default:
        return 'info';
    }
  };

  const getOverallMessage = () => {
    if (serviceCounts.error > 0) {
      return `${serviceCounts.error} 个服务需要立即处理`;
    }
    if (serviceCounts.warning > 0) {
      return `${serviceCounts.warning} 个服务存在警告`;
    }
    if (serviceCounts.healthy > 0) {
      return '所有系统正常运行';
    }
    return '暂无服务状态数据';
  };

  if (loading) {
    return (
      <Card className={className} style={style}>
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <Text type="secondary">正在加载系统状态...</Text>
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
          type={getAlertStatus()}
          showIcon
          message={
            <Space>
              <Text strong>系统状态</Text>
              <Badge
                count={serviceCounts.healthy}
                style={{ backgroundColor: '#52c41a' }}
              />
              <Text type="secondary">健康</Text>
              {serviceCounts.warning > 0 && (
                <>
                  <Badge
                    count={serviceCounts.warning}
                    style={{ backgroundColor: '#faad14' }}
                  />
                  <Text type="secondary">降级</Text>
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
              详情
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
        type={getAlertStatus()}
        showIcon
        message={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <Text strong>生产系统状态</Text>
              <Tag color={(() => {
                const alertStatus = getAlertStatus();
                if (alertStatus === 'success') return 'green';
                if (alertStatus === 'warning') return 'orange';
                if (alertStatus === 'error') return 'red';
                return 'default';
              })()}>
                {getOverallMessage()}
              </Tag>
            </Space>
            <Space>
              {lastUpdate && (
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  最后更新: {lastUpdate.toLocaleTimeString()}
                </Text>
              )}
              <Button
                size="small"
                icon={<ReloadOutlined />}
                loading={refreshing}
                onClick={refreshStatus}
              >
                刷新
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
                      运行时间: {service.uptime}
                    </Text>
                  </div>
                )}

                {service.version && (
                  <div>
                    <Text type="secondary" style={{ fontSize: '11px' }}>
                      版本: {service.version}
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
              <Text strong>系统指标</Text>
            </Space>
          }
          style={{ marginTop: 16 }}
          size="small"
        >
          <Row gutter={[16, 16]}>
            <Col xs={12} md={6}>
              <Statistic
                title="CPU使用率"
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
                title="内存使用率"
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
                title="活跃连接"
                value={systemMetrics.activeConnections}
                prefix={<GlobalOutlined />}
              />
            </Col>

            <Col xs={12} md={6}>
              <Statistic
                title="队列任务"
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
        title="详细服务信息"
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
                          响应: {service.responseTime || '无'}ms
                        </Text>
                      </Col>
                      <Col span={6}>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          运行时间: {service.uptime || '无'}
                        </Text>
                      </Col>
                      <Col span={6}>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          版本: {service.version || '无'}
                        </Text>
                      </Col>
                      <Col span={6}>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      最后检查: {service.lastCheck ? service.lastCheck.toLocaleTimeString() : '未知'}
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
