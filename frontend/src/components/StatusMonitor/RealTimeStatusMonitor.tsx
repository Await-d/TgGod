/**
 * Real-Time Status Monitor Component
 *
 * Comprehensive enterprise-level status monitoring interface that provides
 * complete visibility into system health, service status, and performance metrics.
 *
 * Features:
 * - Live service status dashboard
 * - System performance metrics
 * - Interactive error reporting
 * - Service recovery controls
 * - Maintenance mode indicators
 * - Real-time notifications
 *
 * @author TgGod Team
 * @version 1.0.0
 */

import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Badge,
  Progress,
  Table,
  Tag,
  Button,
  Tooltip,
  Alert,
  Statistic,
  Space,
  Typography,
  Modal,
  List,
  Divider,
  Switch,
  notification
} from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
  SyncOutlined,
  ReloadOutlined,
  SettingOutlined,
  InfoCircleOutlined,
  DisconnectOutlined,
  WifiOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  CloudOutlined,
  MonitorOutlined,
  ToolOutlined
} from '@ant-design/icons';
import { useRealTimeStatus, useSystemHealth } from '../../hooks/useRealTimeStatus';
import { ServiceStatus, ServicePriority } from '../../services/realTimeStatusService';
import './RealTimeStatusMonitor.css';

const { Title, Text } = Typography;

interface RealTimeStatusMonitorProps {
  /**
   * Whether to show the detailed view by default
   */
  showDetailsDefault?: boolean;

  /**
   * Custom title for the monitor
   */
  title?: string;

  /**
   * Whether to show system metrics
   */
  showMetrics?: boolean;

  /**
   * Whether to show service recovery controls
   */
  showRecoveryControls?: boolean;

  /**
   * Custom CSS class name
   */
  className?: string;
}

const RealTimeStatusMonitor: React.FC<RealTimeStatusMonitorProps> = ({
  showDetailsDefault = false,
  title = "System Status Monitor",
  showMetrics = true,
  showRecoveryControls = true,
  className
}) => {
  const [showDetails, setShowDetails] = useState(showDetailsDefault);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);

  const {
    isConnected,
    currentStatus,
    reconnect,
    showServiceRecovery,
    setAutoRetry,
    formatUptime,
    formatResponseTime,
    getStatusColor
  } = useRealTimeStatus({
    autoConnect: true,
    autoReconnect: autoRefreshEnabled,
    onConnectionChange: (connected) => {
      if (!connected) {
        notification.warning({
          message: 'Connection Lost',
          description: 'Real-time monitoring disconnected',
          duration: 4.5,
        });
      }
    },
    onCriticalAlert: (services) => {
      Modal.error({
        title: 'Critical System Alert',
        content: `Critical services offline: ${services.map(s => s.name).join(', ')}`,
        width: 500,
      });
    }
  });

  const {
    healthSummary,
    systemMetrics,
    criticalServices,
    warningServices,
    healthyServices,
    healthPercentage,
    isSystemHealthy,
    hasCriticalIssues
  } = useSystemHealth();

  /**
   * Get service icon based on service name
   */
  const getServiceIcon = (serviceName: string) => {
    const iconMap: Record<string, React.ReactNode> = {
      telegram_service: <CloudOutlined />,
      database: <DatabaseOutlined />,
      task_execution: <ThunderboltOutlined />,
      media_downloader: <CloudOutlined />,
      websocket_manager: <WifiOutlined />,
      file_organizer: <ToolOutlined />,
      network: <WifiOutlined />,
      filesystem: <MonitorOutlined />
    };
    return iconMap[serviceName] || <SettingOutlined />;
  };

  /**
   * Get priority color for UI display
   */
  const getPriorityColor = (priority: ServicePriority): string => {
    switch (priority) {
      case ServicePriority.CRITICAL:
        return '#ff4d4f';
      case ServicePriority.HIGH:
        return '#faad14';
      case ServicePriority.MEDIUM:
        return '#1890ff';
      case ServicePriority.LOW:
        return '#52c41a';
      default:
        return '#d9d9d9';
    }
  };

  /**
   * Handle service recovery action
   */
  const handleServiceRecovery = (serviceName: string) => {
    if (showRecoveryControls) {
      showServiceRecovery(serviceName);
    }
  };

  /**
   * Handle auto-refresh toggle
   */
  const handleAutoRefreshToggle = (enabled: boolean) => {
    setAutoRefreshEnabled(enabled);
    setAutoRetry(enabled);
    notification.info({
      message: 'Auto-refresh ' + (enabled ? 'Enabled' : 'Disabled'),
      description: enabled
        ? 'Automatic reconnection and refresh enabled'
        : 'Manual refresh required for updates',
      duration: 3,
    });
  };

  // Service table columns
  const serviceColumns = [
    {
      title: 'Service',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Space>
          {getServiceIcon(name)}
          <Text strong>{name.replace('_', ' ').toUpperCase()}</Text>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: ServiceStatus, record: any) => {
        const color = getStatusColor(status);
        const icon = status === ServiceStatus.HEALTHY ? <CheckCircleOutlined /> :
                    status === ServiceStatus.ERROR ? <ExclamationCircleOutlined /> :
                    status === ServiceStatus.WARNING ? <WarningOutlined /> :
                    <SyncOutlined spin />;

        return (
          <Tag color={color} icon={icon}>
            {status.toUpperCase()}
          </Tag>
        );
      },
    },
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: ServicePriority) => (
        <Tag color={getPriorityColor(priority)}>
          {priority.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Health Score',
      dataIndex: 'health_score',
      key: 'health_score',
      render: (score: number) => (
        <Progress
          percent={Math.round(score * 100)}
          size="small"
          status={score > 0.8 ? 'success' : score > 0.5 ? 'active' : 'exception'}
          showInfo={false}
          style={{ width: 80 }}
        />
      ),
    },
    {
      title: 'Response Time',
      dataIndex: 'response_time',
      key: 'response_time',
      render: (time: number) => (
        <Text type={time > 1000 ? 'danger' : time > 500 ? 'warning' : 'success'}>
          {formatResponseTime(time)}
        </Text>
      ),
    },
    {
      title: 'Uptime',
      dataIndex: 'uptime',
      key: 'uptime',
      render: (uptime: number) => (
        <Tooltip title={`${uptime.toFixed(0)} seconds`}>
          <Text>{formatUptime(uptime)}</Text>
        </Tooltip>
      ),
    },
    {
      title: 'Message',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
      render: (message: string) => (
        <Tooltip title={message}>
          <Text>{message}</Text>
        </Tooltip>
      ),
    },
    ...(showRecoveryControls ? [{
      title: 'Actions',
      key: 'actions',
      render: (record: any) => (
        <Space>
          {record.status === ServiceStatus.ERROR && (
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => handleServiceRecovery(record.name)}
            >
              Recover
            </Button>
          )}
          <Button
            size="small"
            icon={<InfoCircleOutlined />}
            onClick={() => {
              Modal.info({
                title: `Service Details: ${record.name}`,
                width: 600,
                content: (
                  <div>
                    <p><strong>Status:</strong> {record.status}</p>
                    <p><strong>Priority:</strong> {record.priority}</p>
                    <p><strong>Health Score:</strong> {(record.health_score * 100).toFixed(1)}%</p>
                    <p><strong>Error Count:</strong> {record.error_count}</p>
                    <p><strong>Recovery Attempts:</strong> {record.recovery_attempts}</p>
                    <p><strong>Last Check:</strong> {new Date(record.last_check).toLocaleString()}</p>
                    <p><strong>Dependencies:</strong> {record.dependencies.join(', ') || 'None'}</p>
                    {record.metrics && Object.keys(record.metrics).length > 0 && (
                      <div>
                        <p><strong>Metrics:</strong></p>
                        <pre style={{ fontSize: '12px', background: '#f5f5f5', padding: '8px' }}>
                          {JSON.stringify(record.metrics, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ),
              });
            }}
          >
            Details
          </Button>
        </Space>
      ),
    }] : []),
  ];

  // Get service data for table
  const serviceData = currentStatus
    ? Object.values(currentStatus.services).map((service, index) => ({
        ...service,
        key: index,
      }))
    : [];

  return (
    <div className={`real-time-status-monitor ${className || ''}`}>
      {/* Header */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            {title}
          </Title>
        </Col>
        <Col>
          <Space>
            <Switch
              checked={autoRefreshEnabled}
              onChange={handleAutoRefreshToggle}
              checkedChildren="Auto"
              unCheckedChildren="Manual"
            />
            <Button
              icon={isConnected ? <WifiOutlined /> : <DisconnectOutlined />}
              type={isConnected ? 'default' : 'primary'}
              onClick={reconnect}
              disabled={isConnected}
            >
              {isConnected ? 'Connected' : 'Reconnect'}
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={() => setShowDetails(!showDetails)}
            >
              {showDetails ? 'Simple View' : 'Detailed View'}
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Connection Status Alert */}
      {!isConnected && (
        <Alert
          message="Real-time Connection Lost"
          description="Status updates are not available. Click reconnect to restore real-time monitoring."
          type="warning"
          showIcon
          action={
            <Button size="small" danger onClick={reconnect}>
              Reconnect Now
            </Button>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Maintenance Mode Alert */}
      {currentStatus?.maintenance_mode && (
        <Alert
          message="System in Maintenance Mode"
          description={currentStatus.maintenance?.message || 'System maintenance is in progress'}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          action={
            currentStatus.maintenance?.eta && (
              <Text type="secondary">ETA: {currentStatus.maintenance.eta}</Text>
            )
          }
        />
      )}

      {/* Critical Issues Alert */}
      {hasCriticalIssues && (
        <Alert
          message="Critical System Issues Detected"
          description={`${criticalServices.length} critical service(s) offline. Immediate attention required.`}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button type="primary" danger size="small">
              View Details
            </Button>
          }
        />
      )}

      {/* System Health Overview */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Overall Health"
              value={healthPercentage}
              suffix="%"
              valueStyle={{
                color: isSystemHealthy ? '#3f8600' : hasCriticalIssues ? '#cf1322' : '#fa8c16'
              }}
              prefix={
                isSystemHealthy ? <CheckCircleOutlined /> :
                hasCriticalIssues ? <ExclamationCircleOutlined /> :
                <WarningOutlined />
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Healthy Services"
              value={healthyServices.length}
              suffix={`/ ${healthSummary?.total_services || 0}`}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Critical Issues"
              value={criticalServices.length}
              valueStyle={{ color: criticalServices.length > 0 ? '#cf1322' : '#3f8600' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Active Connections"
              value={systemMetrics?.active_connections || 0}
              prefix={<WifiOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* System Metrics */}
      {showMetrics && systemMetrics && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} md={8}>
            <Card title="CPU Usage" size="small">
              <Progress
                percent={Math.round(systemMetrics.cpu_percent)}
                status={systemMetrics.cpu_percent > 80 ? 'exception' : 'normal'}
                strokeColor={systemMetrics.cpu_percent > 80 ? '#ff4d4f' : '#52c41a'}
              />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card title="Memory Usage" size="small">
              <Progress
                percent={Math.round(systemMetrics.memory_percent)}
                status={systemMetrics.memory_percent > 85 ? 'exception' : 'normal'}
                strokeColor={systemMetrics.memory_percent > 85 ? '#ff4d4f' : '#52c41a'}
              />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card title="Disk Usage" size="small">
              <Progress
                percent={Math.round(systemMetrics.disk_percent)}
                status={systemMetrics.disk_percent > 90 ? 'exception' : 'normal'}
                strokeColor={systemMetrics.disk_percent > 90 ? '#ff4d4f' : '#52c41a'}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Service Status Table */}
      <Card
        title="Service Status"
        extra={
          <Badge
            count={serviceData.length}
            style={{ backgroundColor: '#52c41a' }}
            title="Total Services"
          />
        }
      >
        <Table
          columns={serviceColumns}
          dataSource={serviceData}
          pagination={false}
          size={showDetails ? 'middle' : 'small'}
          scroll={{ x: showDetails ? 1200 : 800 }}
          loading={!currentStatus && isConnected}
          locale={{
            emptyText: isConnected ? 'No service data available' : 'Not connected to monitoring service'
          }}
        />
      </Card>

      {/* Quick Actions */}
      {showDetails && (
        <Card title="Quick Actions" style={{ marginTop: 16 }}>
          <Space wrap>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => window.location.reload()}
            >
              Refresh Page
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={() => {
                Modal.info({
                  title: 'Monitoring Settings',
                  content: 'Advanced monitoring settings will be available in future updates.',
                });
              }}
            >
              Settings
            </Button>
            <Button
              icon={<InfoCircleOutlined />}
              onClick={() => {
                Modal.info({
                  title: 'System Information',
                  width: 600,
                  content: (
                    <div>
                      <p><strong>Last Update:</strong> {currentStatus ? new Date(currentStatus.timestamp).toLocaleString() : 'Never'}</p>
                      <p><strong>Monitoring Active:</strong> {isConnected ? 'Yes' : 'No'}</p>
                      <p><strong>Auto-Refresh:</strong> {autoRefreshEnabled ? 'Enabled' : 'Disabled'}</p>
                      <p><strong>System Uptime:</strong> {systemMetrics ? formatUptime(systemMetrics.uptime) : 'Unknown'}</p>
                      {systemMetrics?.load_average && (
                        <p><strong>Load Average:</strong> {systemMetrics.load_average.map(l => l.toFixed(2)).join(', ')}</p>
                      )}
                    </div>
                  ),
                });
              }}
            >
              System Info
            </Button>
          </Space>
        </Card>
      )}
    </div>
  );
};

export default RealTimeStatusMonitor;