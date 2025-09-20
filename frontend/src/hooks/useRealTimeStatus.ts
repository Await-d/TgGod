/**
 * React Hook for Real-Time Status Management
 *
 * Provides integration between the real-time status service and React components
 * with automatic subscription management and state synchronization.
 *
 * Features:
 * - Automatic WebSocket subscription lifecycle
 * - Store integration for global state management
 * - Service health monitoring
 * - Error handling and recovery
 * - Performance optimized with proper cleanup
 *
 * @author TgGod Team
 * @version 1.0.0
 */

import { useEffect, useCallback, useRef } from 'react';
import {
  realTimeStatusService,
  ServiceInfo,
  SystemMetrics,
  ServiceHealthSummary,
  ProductionStatusData
} from '../services/realTimeStatusService';
import { useRealTimeStatusStore } from '../store';
import { webSocketService } from '../services/websocket';

export interface UseRealTimeStatusOptions {
  /**
   * Whether to automatically connect to real-time status updates
   * @default true
   */
  autoConnect?: boolean;

  /**
   * Whether to enable automatic reconnection
   * @default true
   */
  autoReconnect?: boolean;

  /**
   * Custom error handler for status update errors
   */
  onError?: (error: Error) => void;

  /**
   * Custom handler for connection status changes
   */
  onConnectionChange?: (connected: boolean) => void;

  /**
   * Custom handler for critical service alerts
   */
  onCriticalAlert?: (services: ServiceInfo[]) => void;
}

export interface UseRealTimeStatusReturn {
  /**
   * Whether the real-time connection is active
   */
  isConnected: boolean;

  /**
   * Current system status data
   */
  currentStatus: ProductionStatusData | null;

  /**
   * Overall system health summary
   */
  healthSummary: ServiceHealthSummary | null;

  /**
   * Current system performance metrics
   */
  systemMetrics: SystemMetrics | null;

  /**
   * Last update timestamp
   */
  lastUpdate: string | null;

  /**
   * Get specific service status
   */
  getServiceStatus: (serviceName: string) => ServiceInfo | null;

  /**
   * Manually trigger reconnection
   */
  reconnect: () => void;

  /**
   * Check if a service is healthy
   */
  isServiceHealthy: (serviceName: string) => boolean;

  /**
   * Get services by status
   */
  getServicesByStatus: (status: string) => ServiceInfo[];

  /**
   * Format service uptime for display
   */
  formatUptime: (seconds: number) => string;

  /**
   * Format response time for display
   */
  formatResponseTime: (ms: number) => string;

  /**
   * Get status color for UI
   */
  getStatusColor: (status: string) => string;

  /**
   * Show service recovery dialog
   */
  showServiceRecovery: (serviceName: string) => void;

  /**
   * Enable/disable auto-retry
   */
  setAutoRetry: (enabled: boolean) => void;
}

/**
 * React Hook for Real-Time Status Management
 *
 * Provides comprehensive real-time status monitoring with automatic
 * subscription management and store integration.
 *
 * @param options Configuration options for the hook
 * @returns Real-time status management interface
 */
export function useRealTimeStatus(
  options: UseRealTimeStatusOptions = {}
): UseRealTimeStatusReturn {
  const {
    autoConnect = true,
    autoReconnect = true,
    onError,
    onConnectionChange,
    onCriticalAlert
  } = options;

  // Store state
  const {
    isConnected,
    currentStatus,
    healthSummary,
    systemMetrics,
    lastUpdateTime,
    setConnectionStatus,
    setCurrentStatus,
    setHealthSummary,
    setSystemMetrics
  } = useRealTimeStatusStore();

  // Refs for stable callbacks
  const onErrorRef = useRef(onError);
  const onConnectionChangeRef = useRef(onConnectionChange);
  const onCriticalAlertRef = useRef(onCriticalAlert);

  // Update refs when callbacks change
  useEffect(() => {
    onErrorRef.current = onError;
    onConnectionChangeRef.current = onConnectionChange;
    onCriticalAlertRef.current = onCriticalAlert;
  }, [onError, onConnectionChange, onCriticalAlert]);

  /**
   * Handle status updates from the service
   */
  const handleStatusUpdate = useCallback((data: ProductionStatusData) => {
    try {
      setCurrentStatus(data);

      // Update health summary
      const summary = realTimeStatusService.getHealthSummary();
      if (summary) {
        setHealthSummary(summary);
      }

      // Update system metrics
      if (data.system_metrics) {
        setSystemMetrics(data.system_metrics);
      }

      // Check for critical services
      const criticalServices = Object.values(data.services).filter(
        service => service.priority === 'critical' && service.status === 'error'
      );

      if (criticalServices.length > 0 && onCriticalAlertRef.current) {
        onCriticalAlertRef.current(criticalServices);
      }

    } catch (error) {
      console.error('Error handling status update:', error);
      if (onErrorRef.current) {
        onErrorRef.current(error as Error);
      }
    }
  }, [setCurrentStatus, setHealthSummary, setSystemMetrics]);

  /**
   * Handle connection status changes
   */
  const handleConnectionChange = useCallback((connected: boolean) => {
    setConnectionStatus(connected);

    if (onConnectionChangeRef.current) {
      onConnectionChangeRef.current(connected);
    }
  }, [setConnectionStatus]);

  /**
   * Initialize real-time status monitoring
   */
  useEffect(() => {
    if (!autoConnect) return;

    let statusUnsubscribe: (() => void) | undefined;
    let connectionCheckInterval: NodeJS.Timeout;

    const initializeMonitoring = async () => {
      try {
        // Set up status update subscription
        statusUnsubscribe = realTimeStatusService.onStatusUpdate(handleStatusUpdate);

        // Set up auto-retry
        realTimeStatusService.setAutoRetry(autoReconnect);

        // Monitor connection status
        connectionCheckInterval = setInterval(() => {
          const connected = realTimeStatusService.isConnected();
          if (connected !== isConnected) {
            handleConnectionChange(connected);
          }
        }, 1000);

        // Initialize WebSocket connection if not already connected
        if (!webSocketService.isConnected()) {
          webSocketService.connect();
        }

        console.log('Real-time status monitoring initialized');

      } catch (error) {
        console.error('Failed to initialize real-time status monitoring:', error);
        if (onErrorRef.current) {
          onErrorRef.current(error as Error);
        }
      }
    };

    initializeMonitoring();

    // Cleanup function
    return () => {
      if (statusUnsubscribe) {
        statusUnsubscribe();
      }
      if (connectionCheckInterval) {
        clearInterval(connectionCheckInterval);
      }
    };
  }, [autoConnect, autoReconnect, handleStatusUpdate, handleConnectionChange, isConnected]);

  /**
   * Get specific service status
   */
  const getServiceStatus = useCallback((serviceName: string): ServiceInfo | null => {
    return realTimeStatusService.getServiceStatus(serviceName);
  }, []);

  /**
   * Manually trigger reconnection
   */
  const reconnect = useCallback(() => {
    realTimeStatusService.reconnect();
  }, []);

  /**
   * Check if a service is healthy
   */
  const isServiceHealthy = useCallback((serviceName: string): boolean => {
    const service = getServiceStatus(serviceName);
    return service?.status === 'healthy';
  }, [getServiceStatus]);

  /**
   * Get services by status
   */
  const getServicesByStatus = useCallback((status: string): ServiceInfo[] => {
    if (!currentStatus) return [];

    return (Object.values(currentStatus.services) as ServiceInfo[]).filter(
      (service: ServiceInfo) => service.status === status
    );
  }, [currentStatus]);

  /**
   * Format service uptime for display
   */
  const formatUptime = useCallback((seconds: number): string => {
    return realTimeStatusService.formatUptime(seconds);
  }, []);

  /**
   * Format response time for display
   */
  const formatResponseTime = useCallback((ms: number): string => {
    return realTimeStatusService.formatResponseTime(ms);
  }, []);

  /**
   * Get status color for UI
   */
  const getStatusColor = useCallback((status: string): string => {
    return realTimeStatusService.getStatusColor(status as any);
  }, []);

  /**
   * Show service recovery dialog
   */
  const showServiceRecovery = useCallback((serviceName: string) => {
    realTimeStatusService.showServiceRecovery(serviceName);
  }, []);

  /**
   * Enable/disable auto-retry
   */
  const setAutoRetry = useCallback((enabled: boolean) => {
    realTimeStatusService.setAutoRetry(enabled);
  }, []);

  return {
    isConnected,
    currentStatus,
    healthSummary,
    systemMetrics,
    lastUpdate: lastUpdateTime,
    getServiceStatus,
    reconnect,
    isServiceHealthy,
    getServicesByStatus,
    formatUptime,
    formatResponseTime,
    getStatusColor,
    showServiceRecovery,
    setAutoRetry
  };
}

/**
 * Hook for monitoring specific service status
 *
 * Provides focused monitoring for a single service with optimized updates.
 *
 * @param serviceName Name of the service to monitor
 * @returns Service-specific status interface
 */
export function useServiceStatus(serviceName: string) {
  const { getServiceStatus, isServiceHealthy, getStatusColor, formatUptime, formatResponseTime } = useRealTimeStatus();

  const serviceStatus = getServiceStatus(serviceName);

  return {
    service: serviceStatus,
    isHealthy: isServiceHealthy(serviceName),
    statusColor: serviceStatus ? getStatusColor(serviceStatus.status) : '#d9d9d9',
    formattedUptime: serviceStatus ? formatUptime(serviceStatus.uptime) : '0m',
    formattedResponseTime: serviceStatus ? formatResponseTime(serviceStatus.response_time) : '0ms',
    exists: !!serviceStatus
  };
}

/**
 * Hook for system health overview
 *
 * Provides high-level system health information for dashboards.
 *
 * @returns System health overview interface
 */
export function useSystemHealth() {
  const { healthSummary, systemMetrics, getServicesByStatus } = useRealTimeStatus();

  const criticalServices = getServicesByStatus('error').filter(s => s.priority === 'critical');
  const warningServices = getServicesByStatus('warning');
  const healthyServices = getServicesByStatus('healthy');

  const overallHealthScore = healthSummary?.average_health_score || 0;
  const healthPercentage = Math.round(overallHealthScore * 100);

  return {
    healthSummary,
    systemMetrics,
    criticalServices,
    warningServices,
    healthyServices,
    overallHealthScore,
    healthPercentage,
    isSystemHealthy: criticalServices.length === 0 && warningServices.length === 0,
    hasCriticalIssues: criticalServices.length > 0,
    totalServices: healthSummary?.total_services || 0
  };
}

export default useRealTimeStatus;