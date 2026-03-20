/**
 * Real-Time Status Service for TgGod Frontend
 *
 * Provides comprehensive real-time status monitoring and user feedback system
 * with enterprise-level service information and actionable guidance.
 *
 * Features:
 * - Complete service status monitoring
 * - Real-time error reporting and recovery
 * - System performance metrics display
 * - Actionable user guidance
 * - Maintenance mode handling
 * - Service dependency visualization
 * - Auto-recovery notifications
 *
 * @author TgGod Team
 * @version 1.0.0
 */

import React from 'react';
import { webSocketService } from './websocket';
import { notification, Modal, Form, Input as AntInput, Switch } from 'antd';
import { realtimeControlApi } from './apiService';
import {
  ServiceStatus,
  ServicePriority,
  ServiceInfo,
  SystemMetrics,
  ProductionStatusData,
  ServiceHealthSummary,
  StatusUpdateCallback,
  ErrorReportCallback,
  SystemEventCallback,
} from '../types/realtime';

class RealTimeStatusService {
  private statusUpdateCallbacks: StatusUpdateCallback[] = [];
  private errorReportCallbacks: ErrorReportCallback[] = [];
  private systemEventCallbacks: SystemEventCallback[] = [];
  private currentStatus: ProductionStatusData | null = null;
  private connected = false;
  private autoRetryEnabled = true;
  private lastCriticalAlertKey: string | null = null;
  private lastCriticalAlertTime: number = 0;
  private criticalAlertCooldown: number = 300000; // 5分钟冷却时间
  private lastResourceWarningTimes: Map<string, number> = new Map();
  private resourceWarningCooldown: number = 60000; // 1分钟冷却时间

  constructor() {
    this.initializeWebSocketListeners();
  }

  /**
   * Initialize WebSocket listeners for real-time status updates
   */
  private initializeWebSocketListeners(): void {
    // Subscribe to status updates
    webSocketService.subscribe('status', (data: any) => {
      this.handleStatusUpdate(data);
    });

    // Subscribe to error reports
    webSocketService.subscribe('notification', (data: any) => {
      this.handleNotification(data);
    });

    // Subscribe to system events
    webSocketService.subscribe('system_event', (data: any) => {
      this.handleSystemEvent(data);
    });

    // Monitor WebSocket connection status
    this.monitorConnectionStatus();
  }

  /**
   * Monitor WebSocket connection status
   */
  private monitorConnectionStatus(): void {
    setInterval(() => {
      const isConnected = webSocketService.isConnected();

      if (this.connected !== isConnected) {
        this.connected = isConnected;
        this.handleConnectionStatusChange(isConnected);
      }
    }, 1000);
  }

  /**
   * Handle WebSocket connection status changes
   */
  private handleConnectionStatusChange(connected: boolean): void {
    if (connected) {
      // 连接成功时，关闭断开连接的提示
      notification.destroy('connection-lost');
      notification.success({
        key: 'connection-success',
        message: '实时连接已建立',
        description: '状态监控已启动',
        duration: 3,
      });
    } else {
      notification.warning({
        key: 'connection-lost',
        message: '实时连接已断开',
        description: '正在尝试重新连接…',
        duration: 0, // Persistent until reconnected
      });

      if (this.autoRetryEnabled) {
        this.attemptReconnection();
      }
    }
  }

  /**
   * Attempt to reconnect WebSocket
   */
  private attemptReconnection(): void {
    setTimeout(() => {
      if (!webSocketService.isConnected()) {
        webSocketService.connect();
      }
    }, 5000);
  }

  /**
   * Handle incoming status updates
   */
  private handleStatusUpdate(data: any): void {
    if (data.type === 'production_status') {
      this.currentStatus = data as ProductionStatusData;
      this.processStatusUpdate(data);

      // Notify all subscribers
      this.statusUpdateCallbacks.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error('Status update callback error:', error);
        }
      });
    }
  }

  /**
   * Process status update for automatic notifications
   */
  private processStatusUpdate(data: ProductionStatusData): void {
    // Check for critical service failures
    const criticalServices = Object.values(data.services).filter(
      service => service.priority === ServicePriority.CRITICAL &&
                service.status === ServiceStatus.ERROR
    );

    if (criticalServices.length > 0) {
      const alertKey = criticalServices
        .map(service => `${service.name}:${service.status}:${service.health_score}`)
        .sort()
        .join('|');

      const now = Date.now();
      const timeSinceLastAlert = now - this.lastCriticalAlertTime;

      // 只有在以下情况下才显示警告：
      // 1. 警告内容发生变化（不同的服务或状态）
      // 2. 距离上次警告已超过冷却时间（5分钟）
      if (this.lastCriticalAlertKey !== alertKey && timeSinceLastAlert > this.criticalAlertCooldown) {
        this.showCriticalServiceAlert(criticalServices);
        this.lastCriticalAlertKey = alertKey;
        this.lastCriticalAlertTime = now;
      }
    } else if (this.lastCriticalAlertKey) {
      // 所有关键服务已恢复，重置警告状态
      this.lastCriticalAlertKey = null;
      notification.success({
        key: 'service-recovery',
        message: '服务已恢复',
        description: '所有关键系统服务已恢复正常运行',
        duration: 4.5,
      });
    }

    // Check for maintenance mode changes
    if (data.maintenance_mode && data.maintenance) {
      this.showMaintenanceNotification(data.maintenance);
    }

    // Check system resource warnings
    if (data.system_metrics) {
      this.checkResourceWarnings(data.system_metrics);
    }
  }

  /**
   * Show critical service failure alert
   */
  private showCriticalServiceAlert(services: ServiceInfo[]): void {
    const serviceNames = services.map(s => s.name).join(', ');
    const serviceDetails = services.map(s => `• ${s.name}: ${s.message}`).join('\n');

    Modal.warning({
      title: '关键系统服务状态异常',
      content: `受影响的服务：${serviceNames}\n\n详细信息：\n${serviceDetails}\n\n系统功能可能受到影响，建议前往服务状态页面查看详情。`,
      okText: '查看服务状态',
      cancelText: '忽略',
      onOk: () => {
        // Navigate to service status page
        window.location.hash = '#/system-status';
      },
    });
  }

  /**
   * Show maintenance mode notification
   */
  private showMaintenanceNotification(maintenance: { message: string; eta?: string }): void {
    const description = maintenance.eta 
      ? `${maintenance.message}\n\nEstimated completion: ${maintenance.eta}`
      : maintenance.message;

    notification.info({
      message: '系统维护中',
      description,
      duration: 0, // Persistent during maintenance
      key: 'maintenance-mode',
    });
  }

  /**
   * Check for system resource warnings
   */
  private checkResourceWarnings(metrics: SystemMetrics): void {
    const now = Date.now();

    // CPU warning
    if (metrics.cpu_percent > 80) {
      const lastWarning = this.lastResourceWarningTimes.get('cpu') || 0;
      if (now - lastWarning > this.resourceWarningCooldown) {
        notification.warning({
          key: 'cpu-warning',
          message: 'CPU 使用率过高',
          description: `CPU 使用率已达 ${metrics.cpu_percent.toFixed(1)}%`,
          duration: 5,
        });
        this.lastResourceWarningTimes.set('cpu', now);
      }
    }

    // Memory warning
    if (metrics.memory_percent > 85) {
      const lastWarning = this.lastResourceWarningTimes.get('memory') || 0;
      if (now - lastWarning > this.resourceWarningCooldown) {
        notification.warning({
          key: 'memory-warning',
          message: '内存使用率过高',
          description: `内存使用率已达 ${metrics.memory_percent.toFixed(1)}%`,
          duration: 5,
        });
        this.lastResourceWarningTimes.set('memory', now);
      }
    }

    // Disk space warning
    if (metrics.disk_percent > 90) {
      const lastWarning = this.lastResourceWarningTimes.get('disk') || 0;
      if (now - lastWarning > this.resourceWarningCooldown) {
        notification.error({
          key: 'disk-warning',
          message: '磁盘空间告急',
          description: `磁盘使用率已达 ${metrics.disk_percent.toFixed(1)}%`,
          duration: 0, // 持续显示直到问题解决
        });
        this.lastResourceWarningTimes.set('disk', now);
      }
    }
  }

  /**
   * Handle incoming notifications
   */
  private handleNotification(data: any): void {
    const { title, type, duration, action } = data;
    const message = data.message;

    const notificationConfig: any = {
      message: title,
      description: message,
      duration: duration || 4.5,
    };

    if (action && action.label) {
      notificationConfig.btn = action.label;
    }

    if (type && type in notification && typeof notification[type as keyof typeof notification] === 'function') {
      (notification[type as keyof typeof notification] as Function)(notificationConfig);
    } else {
      notification.info(notificationConfig);
    }
  }

  /**
   * Handle system events
   */
  private handleSystemEvent(data: any): void {
    this.systemEventCallbacks.forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error('System event callback error:', error);
      }
    });

    // Handle specific system events
    switch (data.event) {
      case 'monitoring_started':
        notification.success({
          key: 'monitoring-started',
          message: 'Production Monitoring Active',
          description: 'Real-time system monitoring has been initialized',
          duration: 3,
        });
        break;

      case 'monitoring_stopped':
        notification.warning({
          key: 'monitoring-stopped',
          message: 'Production Monitoring Stopped',
          description: 'Real-time system monitoring has been disabled',
          duration: 5,
        });
        break;

      case 'maintenance_mode_changed':
        if (data.data.enabled) {
          this.showMaintenanceNotification(data.data);
        } else {
          notification.destroy('maintenance-mode');
          notification.success({
            key: 'maintenance-complete',
            message: 'Maintenance Complete',
            description: 'System maintenance has been completed',
            duration: 3,
          });
        }
        break;
    }
  }

  // Public API methods

  /**
   * Subscribe to status updates
   */
  public onStatusUpdate(callback: StatusUpdateCallback): () => void {
    this.statusUpdateCallbacks.push(callback);

    // Return unsubscribe function
    return () => {
      const index = this.statusUpdateCallbacks.indexOf(callback);
      if (index > -1) {
        this.statusUpdateCallbacks.splice(index, 1);
      }
    };
  }

  /**
   * Subscribe to error reports
   */
  public onErrorReport(callback: ErrorReportCallback): () => void {
    this.errorReportCallbacks.push(callback);

    return () => {
      const index = this.errorReportCallbacks.indexOf(callback);
      if (index > -1) {
        this.errorReportCallbacks.splice(index, 1);
      }
    };
  }

  /**
   * Subscribe to system events
   */
  public onSystemEvent(callback: SystemEventCallback): () => void {
    this.systemEventCallbacks.push(callback);

    return () => {
      const index = this.systemEventCallbacks.indexOf(callback);
      if (index > -1) {
        this.systemEventCallbacks.splice(index, 1);
      }
    };
  }

  /**
   * Get current system status
   */
  public getCurrentStatus(): ProductionStatusData | null {
    return this.currentStatus;
  }

  /**
   * Get service health summary
   */
  public getHealthSummary(): ServiceHealthSummary | null {
    if (!this.currentStatus) return null;

    const services = Object.values(this.currentStatus.services);
    const healthyServices = services.filter(s => s.status === ServiceStatus.HEALTHY).length;
    const errorServices = services.filter(s => s.status === ServiceStatus.ERROR).length;
    const criticalErrors = this.currentStatus.error_summary.critical_errors;

    let overallHealth: 'healthy' | 'warning' | 'critical';
    if (criticalErrors > 0 || errorServices > services.length * 0.5) {
      overallHealth = 'critical';
    } else if (errorServices > 0 || healthyServices < services.length) {
      overallHealth = 'warning';
    } else {
      overallHealth = 'healthy';
    }

    return {
      overall_health: overallHealth,
      total_services: services.length,
      healthy_services: healthyServices,
      error_services: errorServices,
      critical_errors: criticalErrors,
      average_health_score: services.reduce((sum, s) => sum + s.health_score, 0) / services.length,
      maintenance_mode: this.currentStatus.maintenance_mode
    };
  }

  /**
   * Get specific service status
   */
  public getServiceStatus(serviceName: string): ServiceInfo | null {
    if (!this.currentStatus) return null;
    return this.currentStatus.services[serviceName] || null;
  }

  /**
   * Get system metrics
   */
  public getSystemMetrics(): SystemMetrics | null {
    return this.currentStatus?.system_metrics || null;
  }

  /**
   * Check if real-time monitoring is connected
   */
  public isConnected(): boolean {
    return this.connected && webSocketService.isConnected();
  }

  /**
   * Force reconnection
   */
  public reconnect(): void {
    webSocketService.disconnect();
    setTimeout(() => {
      webSocketService.connect();
    }, 1000);
  }

  /**
   * Enable/disable auto-retry
   */
  public setAutoRetry(enabled: boolean): void {
    this.autoRetryEnabled = enabled;
  }

  /**
   * Show manual service recovery dialog
   */
  public showServiceRecovery(serviceName: string): void {
    const service = this.getServiceStatus(serviceName);
    if (!service) return;

    const content = `Current Status: ${service.status}\nError Count: ${service.error_count}\nLast Message: ${service.message}`;
    const recoveryContent = service.recovery_suggestion 
      ? `${content}\n\nRecovery Suggestion:\n${service.recovery_suggestion}\n\nWould you like to attempt service recovery?`
      : `${content}\n\nWould you like to attempt service recovery?`;

    Modal.confirm({
      title: `Recover Service: ${serviceName}`,
      content: recoveryContent,
      okText: 'Attempt Recovery',
      cancelText: 'Cancel',
      onOk: () => {
        this.attemptServiceRecovery(serviceName);
      },
    });
  }

  /**
   * Attempt service recovery (call backend API)
   */
  private async attemptServiceRecovery(serviceName: string): Promise<void> {
    try {
      notification.info({
        key: `recovery-${serviceName}`,
        message: 'Recovery Initiated',
        description: `Attempting to recover ${serviceName}...`,
        duration: 3,
      });

      const response = await realtimeControlApi.recoverService(serviceName);

      if (response.success) {
        notification.success({
          key: `recovery-success-${serviceName}`,
          message: 'Recovery Started',
          description: response.message || `${serviceName} recovery started`,
          duration: 4,
        });
      } else {
        notification.warning({
          key: `recovery-warning-${serviceName}`,
          message: 'Recovery Not Started',
          description: response.message || `${serviceName} recovery not started`,
          duration: 5,
        });
      }

    } catch (error) {
      notification.error({
        key: `recovery-failed-${serviceName}`,
        message: 'Recovery Failed',
        description: `Failed to initiate recovery for ${serviceName}`,
        duration: 5,
      });
    }
  }

  /**
   * Show system maintenance dialog
   */
  public showMaintenanceDialog(): void {
    const currentlyEnabled = !!this.currentStatus?.maintenance_mode;
    let formValues = {
      enabled: currentlyEnabled,
      reason: this.currentStatus?.maintenance?.message || '',
      eta: this.currentStatus?.maintenance?.eta || '',
    };

    const content = React.createElement(
      Form,
      { layout: 'vertical', style: { marginTop: 16 } },
      React.createElement(
        Form.Item,
        { label: '启用维护模式' },
        React.createElement(Switch, {
          defaultChecked: currentlyEnabled,
          onChange: (checked: boolean) => { formValues.enabled = checked; },
        })
      ),
      React.createElement(
        Form.Item,
        { label: '维护说明（可留空）' },
        React.createElement(AntInput, {
          defaultValue: formValues.reason,
          placeholder: '请输入维护说明',
          onChange: (e: React.ChangeEvent<HTMLInputElement>) => { formValues.reason = e.target.value; },
        })
      ),
      React.createElement(
        Form.Item,
        { label: '预计恢复时间（可留空）' },
        React.createElement(AntInput, {
          defaultValue: formValues.eta,
          placeholder: '例如：2026-03-20 18:00',
          onChange: (e: React.ChangeEvent<HTMLInputElement>) => { formValues.eta = e.target.value; },
        })
      )
    );

    Modal.confirm({
      title: '维护模式设置',
      width: 480,
      content,
      okText: '确认',
      cancelText: '取消',
      onOk: () => {
        return realtimeControlApi
          .setMaintenanceMode({
            enabled: formValues.enabled,
            message: formValues.reason,
            eta: formValues.eta || undefined,
          })
          .then((response) => {
            notification.success({
              key: 'maintenance-mode-success',
              message: 'Maintenance Mode Updated',
              description: response.message,
              duration: 4,
            });
          })
          .catch((error: any) => {
            notification.error({
              key: 'maintenance-mode-failed',
              message: 'Maintenance Mode Update Failed',
              description: error?.message || 'Failed to update maintenance mode',
              duration: 5,
            });
          });
      },
    });

  }

  /**
   * Format uptime for display
   */
  public formatUptime(seconds: number): string {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  }

  /**
   * Format response time for display
   */
  public formatResponseTime(ms: number): string {
    if (ms < 1000) {
      return `${ms.toFixed(0)}ms`;
    } else {
      return `${(ms / 1000).toFixed(1)}s`;
    }
  }

  /**
   * Get status color for UI display
   */
  public getStatusColor(status: ServiceStatus): string {
    switch (status) {
      case ServiceStatus.HEALTHY:
        return '#52c41a';
      case ServiceStatus.WARNING:
        return '#faad14';
      case ServiceStatus.ERROR:
        return '#ff4d4f';
      case ServiceStatus.MAINTENANCE:
        return '#1890ff';
      case ServiceStatus.STARTING:
      case ServiceStatus.STOPPING:
        return '#722ed1';
      default:
        return '#d9d9d9';
    }
  }

  /**
   * Get priority icon for UI display
   */
  public getPriorityIcon(priority: ServicePriority): string {
    switch (priority) {
      case ServicePriority.CRITICAL:
        return '🔴';
      case ServicePriority.HIGH:
        return '🟠';
      case ServicePriority.MEDIUM:
        return '🟡';
      case ServicePriority.LOW:
        return '🟢';
      default:
        return '⚪';
    }
  }
}

// Export singleton instance
export const realTimeStatusService = new RealTimeStatusService();
export default realTimeStatusService;
