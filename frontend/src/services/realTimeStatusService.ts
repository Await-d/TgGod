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

import { webSocketService } from './websocket';
import { notification, Modal } from 'antd';

// Status enums matching backend
export enum ServiceStatus {
  HEALTHY = 'healthy',
  WARNING = 'warning',
  ERROR = 'error',
  MAINTENANCE = 'maintenance',
  STARTING = 'starting',
  STOPPING = 'stopping',
  UNKNOWN = 'unknown'
}

export enum ServicePriority {
  CRITICAL = 'critical',
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low'
}

// Interface definitions
export interface ServiceInfo {
  name: string;
  status: ServiceStatus;
  priority: ServicePriority;
  health_score: number;
  last_check: string;
  uptime: number;
  response_time: number;
  error_count: number;
  recovery_attempts: number;
  message: string;
  metrics: Record<string, any>;
  recovery_suggestion?: string;
  maintenance_window?: {
    start: string;
    end: string;
    message: string;
  };
}

export interface SystemMetrics {
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  network_io: Record<string, number>;
  active_connections: number;
  total_tasks: number;
  failed_tasks: number;
  uptime: number;
  load_average: number[];
}

export interface ErrorReport {
  error_id: string;
  timestamp: string;
  service: string;
  error_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  message: string;
  details: Record<string, any>;
  suggested_actions: string[];
  auto_recovery_possible: boolean;
  impact_assessment: string;
  resolution_eta?: string;
}

export interface ProductionStatusData {
  type: 'production_status';
  timestamp: string;
  maintenance_mode: boolean;
  services: Record<string, ServiceInfo>;
  system_metrics?: SystemMetrics;
  error_summary: {
    total_errors: number;
    critical_errors: number;
    recent_errors: number;
  };
  maintenance?: {
    message: string;
    eta?: string;
  };
}

export interface ServiceHealthSummary {
  overall_health: 'healthy' | 'warning' | 'critical';
  total_services: number;
  healthy_services: number;
  error_services: number;
  critical_errors: number;
  average_health_score: number;
  maintenance_mode: boolean;
}

// Event listener types
export type StatusUpdateCallback = (data: ProductionStatusData) => void;
export type ErrorReportCallback = (error: ErrorReport) => void;
export type SystemEventCallback = (event: any) => void;

class RealTimeStatusService {
  private statusUpdateCallbacks: StatusUpdateCallback[] = [];
  private errorReportCallbacks: ErrorReportCallback[] = [];
  private systemEventCallbacks: SystemEventCallback[] = [];
  private currentStatus: ProductionStatusData | null = null;
  private connected = false;
  private autoRetryEnabled = true;

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
      notification.success({
        message: 'Real-time Connection Established',
        description: 'Status monitoring is now active',
      });
    } else {
      notification.warning({
        message: 'Real-time Connection Lost',
        description: 'Attempting to reconnect...',
        duration: 0, // Persistent until reconnected
        key: 'connection-lost',
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
      this.showCriticalServiceAlert(criticalServices);
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

    Modal.error({
      title: 'Critical System Services Offline',
      content: `Affected Services: ${serviceNames}\n\nSystem functionality may be severely impacted. Please check the service status page for details and recovery options.`,
      okText: 'View Service Status',
      onOk: () => {
        // Navigate to service status page
        window.location.hash = '#/services';
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
      message: 'System Maintenance Active',
      description,
      duration: 0, // Persistent during maintenance
      key: 'maintenance-mode',
    });
  }

  /**
   * Check for system resource warnings
   */
  private checkResourceWarnings(metrics: SystemMetrics): void {
    // CPU warning
    if (metrics.cpu_percent > 80) {
      notification.warning({
        message: 'High CPU Usage',
        description: `CPU usage is at ${metrics.cpu_percent.toFixed(1)}%`,
      });
    }

    // Memory warning
    if (metrics.memory_percent > 85) {
      notification.warning({
        message: 'High Memory Usage',
        description: `Memory usage is at ${metrics.memory_percent.toFixed(1)}%`,
      });
    }

    // Disk space warning
    if (metrics.disk_percent > 90) {
      notification.error({
        message: 'Critical Disk Space',
        description: `Disk usage is at ${metrics.disk_percent.toFixed(1)}%`,
      });
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
          message: 'Production Monitoring Active',
          description: 'Real-time system monitoring has been initialized',
        });
        break;

      case 'monitoring_stopped':
        notification.warning({
          message: 'Production Monitoring Stopped',
          description: 'Real-time system monitoring has been disabled',
        });
        break;

      case 'maintenance_mode_changed':
        if (data.data.enabled) {
          this.showMaintenanceNotification(data.data);
        } else {
          notification.destroy('maintenance-mode');
          notification.success({
            message: 'Maintenance Complete',
            description: 'System maintenance has been completed',
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
        message: 'Recovery Initiated',
        description: `Attempting to recover ${serviceName}...`,
      });

      // TODO: Implement actual API call to backend recovery endpoint
      // await apiService.recoverService(serviceName);

    } catch (error) {
      notification.error({
        message: 'Recovery Failed',
        description: `Failed to initiate recovery for ${serviceName}`,
      });
    }
  }

  /**
   * Show system maintenance dialog
   */
  public showMaintenanceDialog(): void {
    // TODO: Implement maintenance mode toggle functionality
    Modal.info({
      title: 'System Maintenance',
      content: 'Maintenance mode controls will be available in the admin panel.',
      okText: 'OK',
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