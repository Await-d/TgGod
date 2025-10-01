/**
 * Status Monitor Components Export
 *
 * Centralized export for all status monitoring related components
 * providing easy imports throughout the application.
 *
 * @author TgGod Team
 * @version 1.0.0
 */

export { default as RealTimeStatusMonitor } from './RealTimeStatusMonitor';
export type {
  ServiceInfo,
  SystemMetrics,
  ServiceHealthSummary,
  ProductionStatusData,
  ServiceStatus,
  ServicePriority
} from '../../types/realtime';
export {
  useRealTimeStatus,
  useServiceStatus,
  useSystemHealth
} from '../../hooks/useRealTimeStatus';
