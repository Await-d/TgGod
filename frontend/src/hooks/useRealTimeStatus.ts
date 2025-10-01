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
import { realTimeStatusService } from '../services/realTimeStatusService';
import {
  ServiceInfo,
  SystemMetrics,
  ServiceHealthSummary,
  ProductionStatusData,
} from '../types/realtime';
import { useRealTimeStatusStore } from '../store';
import { useRealTimeStatusContext } from '../providers/RealTimeStatusProvider';

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
    autoReconnect = true,
    onConnectionChange,
    onCriticalAlert
  } = options;

  const context = useRealTimeStatusContext();

  const {
    isConnected,
    currentStatus,
    healthSummary,
    systemMetrics,
    lastUpdateTime
  } = useRealTimeStatusStore((state) => ({
    isConnected: state.isConnected,
    currentStatus: state.currentStatus,
    healthSummary: state.healthSummary,
    systemMetrics: state.systemMetrics,
    lastUpdateTime: state.lastUpdateTime,
  }));

  const prevConnectionRef = useRef(isConnected);
  const criticalKeyRef = useRef<string | null>(null);

  useEffect(() => {
    context.setAutoRetry(autoReconnect);
  }, [autoReconnect, context]);

  useEffect(() => {
    if (!onConnectionChange) {
      prevConnectionRef.current = isConnected;
      return;
    }

    if (prevConnectionRef.current !== isConnected) {
      onConnectionChange(isConnected);
    }

    prevConnectionRef.current = isConnected;
  }, [isConnected, onConnectionChange]);

  useEffect(() => {
    if (!onCriticalAlert || !currentStatus) {
      criticalKeyRef.current = null;
      return;
    }

    const criticalServices = Object.values<ServiceInfo>(currentStatus.services).filter(
      (service) => service.priority === 'critical' && service.status === 'error'
    );

    if (criticalServices.length === 0) {
      criticalKeyRef.current = null;
      return;
    }

    const alertKey = criticalServices
      .map((service) => service.name)
      .sort()
      .join('|');

    if (criticalKeyRef.current !== alertKey) {
      onCriticalAlert(criticalServices);
      criticalKeyRef.current = alertKey;
    }
  }, [currentStatus, onCriticalAlert]);

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
    context.reconnect();
  }, [context]);

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

    return Object.values<ServiceInfo>(currentStatus.services).filter(
      (service) => service.status === status
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
    context.setAutoRetry(enabled);
  }, [context]);

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
