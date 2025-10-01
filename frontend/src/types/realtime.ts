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

export type StatusUpdateCallback = (data: ProductionStatusData) => void;
export type ErrorReportCallback = (error: ErrorReport) => void;
export type SystemEventCallback = (event: any) => void;
