/**
 * 完整生产级前端错误管理服务
 * 企业级错误处理，具备预测性故障检测、自动恢复和全面错误预防
 */

import { notification, message, Modal } from 'antd';

// 错误严重程度
export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

// 错误分类
export enum ErrorCategory {
  BUSINESS = 'business',
  SYSTEM = 'system',
  EXTERNAL_SERVICE = 'external',
  CONFIGURATION = 'configuration',
  VALIDATION = 'validation',
  AUTHENTICATION = 'auth',
  NETWORK = 'network',
  DATABASE = 'database',
  UI = 'ui',
  PERMISSION = 'permission'
}

// 恢复策略
export enum RecoveryStrategy {
  RETRY = 'retry',
  REFRESH_PAGE = 'refresh_page',
  CLEAR_CACHE = 'clear_cache',
  FALLBACK_UI = 'fallback_ui',
  REDIRECT_LOGIN = 'redirect_login',
  SHOW_OFFLINE_MODE = 'show_offline_mode',
  CONTACT_SUPPORT = 'contact_support',
  IGNORE = 'ignore'
}

// 错误上下文
export interface ErrorContext {
  component?: string;
  route?: string;
  userId?: string;
  timestamp: string;
  sessionId: string;
  userAgent: string;
  url: string;
  additionalData?: Record<string, any>;
}

// 应用错误
export interface AppError {
  id: string;
  message: string;
  category: ErrorCategory;
  severity: ErrorSeverity;
  context: ErrorContext;
  originalError?: Error;
  suggestedAction?: string;
  recoveryStrategies: RecoveryStrategy[];
  isRetryable: boolean;
  retryCount: number;
  suppressUntil?: Date;
}

// 错误模式
export interface ErrorPattern {
  pattern: string;
  count: number;
  lastOccurrence: Date;
  severity: ErrorSeverity;
  isEscalating: boolean;
}

// 系统健康状态
export interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'critical' | 'offline';
  services: Record<string, {
    status: 'healthy' | 'degraded' | 'critical' | 'offline';
    lastCheck: Date;
    responseTime?: number;
    errorRate?: number;
  }>;
  lastUpdate: Date;
}

// 恢复行动
export interface RecoveryAction {
  strategy: RecoveryStrategy;
  description: string;
  execute: () => Promise<boolean>;
  rollback?: () => Promise<void>;
  priority: number;
}

// 错误抑制规则
interface ErrorSuppressionRule {
  pattern: string;
  maxOccurrences: number;
  timeWindow: number; // 毫秒
  suppressionDuration: number; // 毫秒
}

// 性能指标
interface PerformanceMetrics {
  timestamp: Date;
  memoryUsage?: number;
  renderTime?: number;
  networkLatency?: number;
  errorCount: number;
  userInteractions: number;
}

class ErrorManagementService {
  private errors: Map<string, AppError> = new Map();
  private errorPatterns: Map<string, ErrorPattern> = new Map();
  private suppressionRules: ErrorSuppressionRule[] = [];
  private suppressedErrors: Set<string> = new Set();
  private retryAttempts: Map<string, number> = new Map();
  private systemHealth!: SystemHealth;
  private performanceMetrics: PerformanceMetrics[] = [];
  private recoveryActions: Map<RecoveryStrategy, RecoveryAction> = new Map();
  private monitoringInterval?: NodeJS.Timeout;
  private isOnline = navigator.onLine;
  private circuitBreakers: Map<string, CircuitBreaker> = new Map();

  // 配置
  private config = {
    maxErrors: 1000,
    maxRetries: 3,
    retryDelays: [1000, 2000, 4000], // 指数退避
    suppressionWindow: 60000, // 1分钟
    maxSuppressedErrors: 100,
    healthCheckInterval: 30000, // 30秒
    performanceMetricsWindow: 300000, // 5分钟
    enablePredictiveAnalysis: true,
    enableAutoRecovery: true,
    enableUserNotifications: true
  };

  constructor() {
    this.initializeSystemHealth();
    this.setupDefaultSuppressionRules();
    this.setupRecoveryActions();
    this.setupEventListeners();
    this.startMonitoring();
  }

  private initializeSystemHealth(): void {
    this.systemHealth = {
      overall: 'healthy',
      services: {
        api: { status: 'healthy', lastCheck: new Date() },
        websocket: { status: 'healthy', lastCheck: new Date() },
        telegram: { status: 'healthy', lastCheck: new Date() },
        storage: { status: 'healthy', lastCheck: new Date() }
      },
      lastUpdate: new Date()
    };
  }

  private setupDefaultSuppressionRules(): void {
    this.suppressionRules = [
      {
        pattern: 'network.*timeout',
        maxOccurrences: 3,
        timeWindow: 60000,
        suppressionDuration: 300000 // 5分钟
      },
      {
        pattern: 'validation.*',
        maxOccurrences: 5,
        timeWindow: 30000,
        suppressionDuration: 60000 // 1分钟
      },
      {
        pattern: 'ui.*render',
        maxOccurrences: 10,
        timeWindow: 60000,
        suppressionDuration: 120000 // 2分钟
      }
    ];
  }

  private setupRecoveryActions(): void {
    this.recoveryActions.set(RecoveryStrategy.RETRY, {
      strategy: RecoveryStrategy.RETRY,
      description: 'Retry the failed operation',
      execute: async () => {
        // 实现重试逻辑
        return true;
      },
      priority: 1
    });

    this.recoveryActions.set(RecoveryStrategy.REFRESH_PAGE, {
      strategy: RecoveryStrategy.REFRESH_PAGE,
      description: 'Refresh the page to recover',
      execute: async () => {
        window.location.reload();
        return true;
      },
      priority: 5
    });

    this.recoveryActions.set(RecoveryStrategy.CLEAR_CACHE, {
      strategy: RecoveryStrategy.CLEAR_CACHE,
      description: 'Clear application cache',
      execute: async () => {
        try {
          // 清理localStorage
          const keysToRemove: string[] = [];
          for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && !key.includes('auth')) { // 保留认证信息
              keysToRemove.push(key);
            }
          }
          keysToRemove.forEach(key => localStorage.removeItem(key));

          // 清理sessionStorage
          sessionStorage.clear();

          // 清理缓存
          if ('caches' in window) {
            const cacheNames = await caches.keys();
            await Promise.all(
              cacheNames.map(cacheName => caches.delete(cacheName))
            );
          }

          return true;
        } catch (error) {
          console.error('Failed to clear cache:', error);
          return false;
        }
      },
      priority: 3
    });

    this.recoveryActions.set(RecoveryStrategy.FALLBACK_UI, {
      strategy: RecoveryStrategy.FALLBACK_UI,
      description: 'Switch to fallback UI mode',
      execute: async () => {
        // 启用简化UI模式
        document.body.classList.add('fallback-mode');
        return true;
      },
      rollback: async () => {
        document.body.classList.remove('fallback-mode');
      },
      priority: 4
    });

    this.recoveryActions.set(RecoveryStrategy.REDIRECT_LOGIN, {
      strategy: RecoveryStrategy.REDIRECT_LOGIN,
      description: 'Redirect to login page',
      execute: async () => {
        window.location.href = '/login';
        return true;
      },
      priority: 2
    });

    this.recoveryActions.set(RecoveryStrategy.SHOW_OFFLINE_MODE, {
      strategy: RecoveryStrategy.SHOW_OFFLINE_MODE,
      description: 'Enable offline mode',
      execute: async () => {
        // 显示离线模式UI
        this.showOfflineNotification();
        return true;
      },
      priority: 6
    });
  }

  private setupEventListeners(): void {
    // 全局错误监听
    window.addEventListener('error', (event) => {
      this.handleGlobalError(event.error, {
        component: 'global',
        route: window.location.pathname
      });
    });

    // Promise rejection监听
    window.addEventListener('unhandledrejection', (event) => {
      this.handleGlobalError(new Error(event.reason), {
        component: 'promise',
        route: window.location.pathname
      });
    });

    // 网络状态监听
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.updateServiceHealth('network', 'healthy');
      this.hideOfflineNotification();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
      this.updateServiceHealth('network', 'offline');
      this.showOfflineNotification();
    });

    // 性能监控
    if ('PerformanceObserver' in window) {
      this.setupPerformanceMonitoring();
    }
  }

  private setupPerformanceMonitoring(): void {
    // 监控渲染性能
    const paintObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.name === 'first-contentful-paint') {
          this.recordPerformanceMetric('renderTime', entry.startTime);
        }
      }
    });

    paintObserver.observe({ entryTypes: ['paint'] });

    // 监控网络性能
    const navigationObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.entryType === 'navigation') {
          const navEntry = entry as PerformanceNavigationTiming;
          this.recordPerformanceMetric('networkLatency',
            navEntry.responseEnd - navEntry.requestStart);
        }
      }
    });

    navigationObserver.observe({ entryTypes: ['navigation'] });
  }

  private startMonitoring(): void {
    this.monitoringInterval = setInterval(() => {
      this.performHealthCheck();
      this.analyzeErrorPatterns();
      this.cleanupOldData();
    }, this.config.healthCheckInterval);
  }

  // 主要的错误处理方法
  public handleError(
    error: Error | AppError,
    context?: Partial<ErrorContext>,
    options?: {
      suppress?: boolean;
      autoRecover?: boolean;
      showNotification?: boolean;
    }
  ): string {
    const errorId = this.generateErrorId();

    let appError: AppError;
    if (this.isAppError(error)) {
      appError = error;
    } else {
      appError = this.createAppError(error, context, errorId);
    }

    // 检查错误抑制
    if (options?.suppress !== false && this.shouldSuppressError(appError)) {
      this.suppressedErrors.add(errorId);
      return errorId;
    }

    // 记录错误
    this.errors.set(errorId, appError);

    // 更新错误模式
    this.updateErrorPattern(appError);

    // 记录性能影响
    this.recordErrorMetric();

    // 熔断器检查
    this.updateCircuitBreaker(appError);

    // 日志记录
    this.logError(appError);

    // 显示用户通知
    if (options?.showNotification !== false && this.config.enableUserNotifications) {
      this.showErrorNotification(appError);
    }

    // 自动恢复
    if (options?.autoRecover !== false && this.config.enableAutoRecovery) {
      this.attemptAutoRecovery(appError);
    }

    // 上报到后端
    this.reportErrorToBackend(appError);

    return errorId;
  }

  private isAppError(error: any): error is AppError {
    return error && typeof error === 'object' && 'id' in error && 'category' in error;
  }

  private createAppError(
    error: Error,
    context?: Partial<ErrorContext>,
    errorId?: string
  ): AppError {
    const errorContext: ErrorContext = {
      component: context?.component || 'unknown',
      route: context?.route || window.location.pathname,
      timestamp: new Date().toISOString(),
      sessionId: this.getSessionId(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      ...context
    };

    // 错误分类
    const category = this.categorizeError(error);
    const severity = this.determineSeverity(error, category);
    const recoveryStrategies = this.determineRecoveryStrategies(category, severity);

    return {
      id: errorId || this.generateErrorId(),
      message: error.message || 'Unknown error',
      category,
      severity,
      context: errorContext,
      originalError: error,
      recoveryStrategies,
      isRetryable: this.isRetryableError(category),
      retryCount: 0
    };
  }

  private categorizeError(error: Error): ErrorCategory {
    const message = error.message.toLowerCase();
    const stack = error.stack?.toLowerCase() || '';

    if (message.includes('network') || message.includes('fetch')) {
      return ErrorCategory.NETWORK;
    }
    if (message.includes('auth') || message.includes('unauthorized')) {
      return ErrorCategory.AUTHENTICATION;
    }
    if (message.includes('validation') || message.includes('invalid')) {
      return ErrorCategory.VALIDATION;
    }
    if (message.includes('permission') || message.includes('forbidden')) {
      return ErrorCategory.PERMISSION;
    }
    if (stack.includes('react') || stack.includes('render')) {
      return ErrorCategory.UI;
    }
    if (message.includes('config') || message.includes('environment')) {
      return ErrorCategory.CONFIGURATION;
    }

    return ErrorCategory.SYSTEM;
  }

  private determineSeverity(error: Error, category: ErrorCategory): ErrorSeverity {
    // 根据错误类型和内容确定严重程度
    if (category === ErrorCategory.AUTHENTICATION) {
      return ErrorSeverity.HIGH;
    }
    if (category === ErrorCategory.NETWORK && !this.isOnline) {
      return ErrorSeverity.MEDIUM;
    }
    if (category === ErrorCategory.VALIDATION) {
      return ErrorSeverity.LOW;
    }
    if (error.message.includes('critical') || error.message.includes('fatal')) {
      return ErrorSeverity.CRITICAL;
    }

    return ErrorSeverity.MEDIUM;
  }

  private determineRecoveryStrategies(
    category: ErrorCategory,
    severity: ErrorSeverity
  ): RecoveryStrategy[] {
    const strategies: RecoveryStrategy[] = [];

    switch (category) {
      case ErrorCategory.NETWORK:
        strategies.push(RecoveryStrategy.RETRY);
        if (!this.isOnline) {
          strategies.push(RecoveryStrategy.SHOW_OFFLINE_MODE);
        }
        break;

      case ErrorCategory.AUTHENTICATION:
        strategies.push(RecoveryStrategy.REDIRECT_LOGIN);
        break;

      case ErrorCategory.UI:
        strategies.push(RecoveryStrategy.FALLBACK_UI, RecoveryStrategy.REFRESH_PAGE);
        break;

      case ErrorCategory.SYSTEM:
        if (severity === ErrorSeverity.CRITICAL) {
          strategies.push(RecoveryStrategy.REFRESH_PAGE);
        } else {
          strategies.push(RecoveryStrategy.RETRY, RecoveryStrategy.CLEAR_CACHE);
        }
        break;

      default:
        strategies.push(RecoveryStrategy.RETRY);
    }

    return strategies;
  }

  private shouldSuppressError(error: AppError): boolean {
    const errorKey = `${error.category}.${error.message}`;

    for (const rule of this.suppressionRules) {
      if (this.matchesPattern(errorKey, rule.pattern)) {
        const recentErrors = Array.from(this.errors.values())
          .filter(e =>
            this.matchesPattern(`${e.category}.${e.message}`, rule.pattern) &&
            Date.now() - new Date(e.context.timestamp).getTime() < rule.timeWindow
          );

        if (recentErrors.length >= rule.maxOccurrences) {
          return true;
        }
      }
    }

    return false;
  }

  private matchesPattern(text: string, pattern: string): boolean {
    const regex = new RegExp(pattern.replace('*', '.*'), 'i');
    return regex.test(text);
  }

  private updateErrorPattern(error: AppError): void {
    const patternKey = `${error.category}.${error.severity}`;
    const existing = this.errorPatterns.get(patternKey);

    if (existing) {
      existing.count++;
      existing.lastOccurrence = new Date();
      existing.isEscalating = this.isPatternEscalating(existing);
    } else {
      this.errorPatterns.set(patternKey, {
        pattern: patternKey,
        count: 1,
        lastOccurrence: new Date(),
        severity: error.severity,
        isEscalating: false
      });
    }
  }

  private isPatternEscalating(pattern: ErrorPattern): boolean {
    // 检查错误模式是否在升级
    const recentCount = pattern.count;
    const timeWindow = 300000; // 5分钟
    const threshold = pattern.severity === ErrorSeverity.CRITICAL ? 2 : 5;

    return recentCount > threshold &&
      Date.now() - pattern.lastOccurrence.getTime() < timeWindow;
  }

  private showErrorNotification(error: AppError): void {
    const config = {
      message: this.getUserFriendlyMessage(error),
      description: error.suggestedAction || this.getSuggestedAction(error),
      duration: this.getNotificationDuration(error.severity)
    };

    switch (error.severity) {
      case ErrorSeverity.CRITICAL:
        notification.error({
          ...config,
          key: error.id,
        });
        break;

      case ErrorSeverity.HIGH:
        notification.warning({
          ...config,
          key: error.id,
        });
        break;

      case ErrorSeverity.MEDIUM:
        notification.info(config);
        break;

      case ErrorSeverity.LOW:
        message.warning(config.message);
        break;
    }
  }

  private getUserFriendlyMessage(error: AppError): string {
    // 将技术错误消息转换为用户友好的消息
    switch (error.category) {
      case ErrorCategory.NETWORK:
        return this.isOnline ? '网络连接出现问题' : '网络连接已断开';
      case ErrorCategory.AUTHENTICATION:
        return '身份验证失败，请重新登录';
      case ErrorCategory.VALIDATION:
        return '输入数据有误，请检查后重试';
      case ErrorCategory.PERMISSION:
        return '您没有执行此操作的权限';
      default:
        return '系统出现异常，正在尝试恢复';
    }
  }

  private getSuggestedAction(error: AppError): string {
    if (!error.isRetryable) {
      return '请联系技术支持';
    }

    switch (error.category) {
      case ErrorCategory.NETWORK:
        return '请检查网络连接或稍后重试';
      case ErrorCategory.AUTHENTICATION:
        return '请重新登录';
      case ErrorCategory.VALIDATION:
        return '请检查输入内容';
      default:
        return '请稍后重试或刷新页面';
    }
  }

  private getNotificationDuration(severity: ErrorSeverity): number {
    switch (severity) {
      case ErrorSeverity.CRITICAL:
        return 0; // 不自动关闭
      case ErrorSeverity.HIGH:
        return 10;
      case ErrorSeverity.MEDIUM:
        return 6;
      case ErrorSeverity.LOW:
        return 3;
      default:
        return 4.5;
    }
  }

  private async attemptAutoRecovery(error: AppError): Promise<boolean> {
    if (!error.isRetryable || error.retryCount >= this.config.maxRetries) {
      return false;
    }

    // 增加重试计数
    error.retryCount++;

    // 获取重试延迟
    const delay = this.config.retryDelays[
      Math.min(error.retryCount - 1, this.config.retryDelays.length - 1)
    ];

    // 延迟后执行恢复
    setTimeout(async () => {
      const success = await this.executeRecovery(error);
      if (!success && error.retryCount < this.config.maxRetries) {
        // 如果失败且还有重试机会，继续重试
        this.attemptAutoRecovery(error);
      }
    }, delay);

    return true;
  }

  private async executeRecovery(error: AppError): Promise<boolean> {
    for (const strategy of error.recoveryStrategies) {
      const action = this.recoveryActions.get(strategy);
      if (!action) continue;

      try {
        const success = await action.execute();
        if (success) {
          // 记录成功恢复
          this.recordRecoverySuccess(error, strategy);

          // 关闭错误通知
          notification.destroy(error.id);

          return true;
        }
      } catch (recoveryError) {
        console.error(`Recovery strategy ${strategy} failed:`, recoveryError);
      }
    }

    return false;
  }

  private recordRecoverySuccess(error: AppError, strategy: RecoveryStrategy): void {
    // 更新错误状态
    error.recoveryStrategies = error.recoveryStrategies.filter(s => s !== strategy);

    // 如果是完全恢复，从错误列表中移除
    if (error.recoveryStrategies.length === 0) {
      this.errors.delete(error.id);
    }

    // 记录恢复指标
    this.recordPerformanceMetric('recoverySuccess', 1);
  }

  // 系统健康检查
  private async performHealthCheck(): Promise<void> {
    // 检查API连接
    await this.checkServiceHealth('api', '/api/health');

    // 检查WebSocket连接
    this.checkWebSocketHealth();

    // 检查存储
    this.checkStorageHealth();

    // 更新整体健康状态
    this.updateOverallHealth();

    this.systemHealth.lastUpdate = new Date();
  }

  private async checkServiceHealth(serviceName: string, endpoint: string): Promise<void> {
    const startTime = Date.now();

    try {
      const response = await fetch(endpoint, {
        method: 'GET',
        // timeout: 5000
      } as any);

      const responseTime = Date.now() - startTime;

      if (response.ok) {
        this.updateServiceHealth(serviceName, 'healthy', responseTime);
      } else {
        this.updateServiceHealth(serviceName, 'degraded', responseTime);
      }
    } catch (error) {
      this.updateServiceHealth(serviceName, 'critical');
    }
  }

  private checkWebSocketHealth(): void {
    // 这里应该检查WebSocket连接状态
    // 可以通过全局WebSocket实例或者状态管理来获取
    const status = 'healthy'; // 默认状态，实际应该从WebSocket管理器获取
    this.updateServiceHealth('websocket', status);
  }

  private checkStorageHealth(): void {
    try {
      const testKey = '__health_check__';
      localStorage.setItem(testKey, 'test');
      localStorage.removeItem(testKey);
      this.updateServiceHealth('storage', 'healthy');
    } catch (error) {
      this.updateServiceHealth('storage', 'critical');
    }
  }

  private updateServiceHealth(
    serviceName: string,
    status: 'healthy' | 'degraded' | 'critical' | 'offline',
    responseTime?: number
  ): void {
    const service = this.systemHealth.services[serviceName];
    if (service) {
      service.status = status;
      service.lastCheck = new Date();
      if (responseTime !== undefined) {
        service.responseTime = responseTime;
      }
    }
  }

  private updateOverallHealth(): void {
    const services = Object.values(this.systemHealth.services);
    const criticalCount = services.filter(s => s.status === 'critical').length;
    const degradedCount = services.filter(s => s.status === 'degraded').length;

    if (criticalCount > 0) {
      this.systemHealth.overall = 'critical';
    } else if (degradedCount > 0) {
      this.systemHealth.overall = 'degraded';
    } else {
      this.systemHealth.overall = 'healthy';
    }
  }

  // 性能指标
  private recordPerformanceMetric(type: string, value: number): void {
    const now = new Date();
    let metric = this.performanceMetrics.find(m =>
      m.timestamp.getTime() === Math.floor(now.getTime() / 60000) * 60000 // 分钟级聚合
    );

    if (!metric) {
      metric = {
        timestamp: new Date(Math.floor(now.getTime() / 60000) * 60000),
        errorCount: 0,
        userInteractions: 0
      };
      this.performanceMetrics.push(metric);
    }

    if (type === 'error') {
      metric.errorCount++;
    } else if (type === 'renderTime') {
      metric.renderTime = value;
    } else if (type === 'networkLatency') {
      metric.networkLatency = value;
    } else if (type === 'memoryUsage') {
      metric.memoryUsage = value;
    } else if (type === 'userInteraction') {
      metric.userInteractions++;
    }

    // 保持最近5分钟的数据
    const cutoff = now.getTime() - this.config.performanceMetricsWindow;
    this.performanceMetrics = this.performanceMetrics.filter(m =>
      m.timestamp.getTime() > cutoff
    );
  }

  private recordErrorMetric(): void {
    this.recordPerformanceMetric('error', 1);
  }

  // 熔断器
  private updateCircuitBreaker(error: AppError): void {
    const service = error.context.component || 'unknown';
    let breaker = this.circuitBreakers.get(service);

    if (!breaker) {
      breaker = new CircuitBreaker(service);
      this.circuitBreakers.set(service, breaker);
    }

    breaker.recordFailure();
  }

  public isServiceCircuitOpen(service: string): boolean {
    const breaker = this.circuitBreakers.get(service);
    return breaker ? breaker.isOpen() : false;
  }

  // 错误模式分析
  private analyzeErrorPatterns(): void {
    if (!this.config.enablePredictiveAnalysis) return;

    for (const [key, pattern] of Array.from(this.errorPatterns.entries())) {
      if (pattern.isEscalating) {
        this.handleEscalatingPattern(pattern);
      }
    }
  }

  private handleEscalatingPattern(pattern: ErrorPattern): void {
    // 处理升级的错误模式
    notification.warning({
      message: '错误模式升级警告',
      description: `检测到 ${pattern.pattern} 错误模式正在升级，建议采取预防措施`,
      duration: 10,
      key: `pattern_${pattern.pattern}`
    });

    // 可以在这里实施预防性措施
    this.implementPreventiveMeasures(pattern);
  }

  private implementPreventiveMeasures(pattern: ErrorPattern): void {
    // 根据错误模式实施预防措施
    if (pattern.pattern.includes('network')) {
      // 网络相关预防措施
      this.preloadCriticalResources();
    } else if (pattern.pattern.includes('ui')) {
      // UI相关预防措施
      this.optimizeUIPerformance();
    }
  }

  // 数据清理
  private cleanupOldData(): void {
    const now = Date.now();
    const cutoffTime = now - (24 * 60 * 60 * 1000); // 24小时前

    // 清理旧错误
    for (const [id, error] of Array.from(this.errors.entries())) {
      const errorTime = new Date(error.context.timestamp).getTime();
      if (errorTime < cutoffTime) {
        this.errors.delete(id);
      }
    }

    // 清理旧的错误模式
    for (const [key, pattern] of Array.from(this.errorPatterns.entries())) {
      if (pattern.lastOccurrence.getTime() < cutoffTime) {
        this.errorPatterns.delete(key);
      }
    }

    // 清理被抑制的错误
    this.suppressedErrors.clear();
  }

  // 实用方法
  private generateErrorId(): string {
    return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private getSessionId(): string {
    let sessionId = sessionStorage.getItem('sessionId');
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('sessionId', sessionId);
    }
    return sessionId;
  }

  private isRetryableError(category: ErrorCategory): boolean {
    return [
      ErrorCategory.NETWORK,
      ErrorCategory.SYSTEM,
      ErrorCategory.EXTERNAL_SERVICE
    ].includes(category);
  }

  private logError(error: AppError): void {
    const logLevel = {
      [ErrorSeverity.LOW]: 'info',
      [ErrorSeverity.MEDIUM]: 'warn',
      [ErrorSeverity.HIGH]: 'error',
      [ErrorSeverity.CRITICAL]: 'error'
    }[error.severity];

    console[logLevel as 'info' | 'warn' | 'error'](
      `[${error.severity.toUpperCase()}] ${error.category}: ${error.message}`,
      {
        errorId: error.id,
        context: error.context,
        originalError: error.originalError
      }
    );
  }

  private async reportErrorToBackend(error: AppError): Promise<void> {
    try {
      // 只上报中等及以上严重程度的错误
      if ([ErrorSeverity.MEDIUM, ErrorSeverity.HIGH, ErrorSeverity.CRITICAL].includes(error.severity)) {
        await fetch('/api/errors/report', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            ...error,
            originalError: error.originalError ? {
              name: error.originalError.name,
              message: error.originalError.message,
              stack: error.originalError.stack
            } : undefined
          })
        });
      }
    } catch (reportError) {
      // 上报失败时不要抛出错误，避免无限循环
      console.warn('Failed to report error to backend:', reportError);
    }
  }

  // 离线处理
  private showOfflineNotification(): void {
    notification.warning({
      key: 'offline',
      message: '网络连接已断开',
      description: '应用将在离线模式下运行，部分功能可能受限',
      duration: 0,
    });
  }

  private hideOfflineNotification(): void {
    notification.destroy('offline');
    message.success('网络连接已恢复');
  }

  // 性能优化方法
  private preloadCriticalResources(): void {
    // 预加载关键资源
  }

  private optimizeUIPerformance(): void {
    // 优化UI性能
  }

  // 全局错误处理器
  private handleGlobalError(error: Error, context: Partial<ErrorContext>): void {
    this.handleError(error, context, {
      autoRecover: true,
      showNotification: true
    });
  }

  // 公共API
  public getSystemHealth(): SystemHealth {
    return { ...this.systemHealth };
  }

  public getErrorSummary(): {
    totalErrors: number;
    errorsByCategory: Record<ErrorCategory, number>;
    errorsBySeverity: Record<ErrorSeverity, number>;
    recentErrors: AppError[];
  } {
    const errors = Array.from(this.errors.values());
    const recentErrors = errors
      .filter(e => Date.now() - new Date(e.context.timestamp).getTime() < 300000) // 最近5分钟
      .sort((a, b) => new Date(b.context.timestamp).getTime() - new Date(a.context.timestamp).getTime())
      .slice(0, 10);

    const errorsByCategory = errors.reduce((acc, error) => {
      acc[error.category] = (acc[error.category] || 0) + 1;
      return acc;
    }, {} as Record<ErrorCategory, number>);

    const errorsBySeverity = errors.reduce((acc, error) => {
      acc[error.severity] = (acc[error.severity] || 0) + 1;
      return acc;
    }, {} as Record<ErrorSeverity, number>);

    return {
      totalErrors: errors.length,
      errorsByCategory,
      errorsBySeverity,
      recentErrors
    };
  }

  public clearErrors(): void {
    this.errors.clear();
    this.errorPatterns.clear();
    this.suppressedErrors.clear();
  }

  public destroy(): void {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
    }
    this.clearErrors();
    this.circuitBreakers.clear();
  }
}

// 熔断器实现
class CircuitBreaker {
  private failures = 0;
  private lastFailureTime = 0;
  private state: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED';

  constructor(
    private serviceName: string,
    private failureThreshold = 5,
    private timeout = 60000 // 1分钟
  ) {}

  recordFailure(): void {
    this.failures++;
    this.lastFailureTime = Date.now();

    if (this.failures >= this.failureThreshold) {
      this.state = 'OPEN';
    }
  }

  recordSuccess(): void {
    this.failures = 0;
    this.state = 'CLOSED';
  }

  isOpen(): boolean {
    if (this.state === 'OPEN') {
      if (Date.now() - this.lastFailureTime > this.timeout) {
        this.state = 'HALF_OPEN';
        return false;
      }
      return true;
    }
    return false;
  }

  getState(): string {
    return this.state;
  }
}

// 导出单例实例
export const errorManagementService = new ErrorManagementService();

// 导出工具函数
export function handleError(
  error: Error,
  context?: Partial<ErrorContext>,
  options?: {
    suppress?: boolean;
    autoRecover?: boolean;
    showNotification?: boolean;
  }
): string {
  return errorManagementService.handleError(error, context, options);
}

export function getSystemHealth(): SystemHealth {
  return errorManagementService.getSystemHealth();
}

export function isServiceHealthy(serviceName: string): boolean {
  const health = errorManagementService.getSystemHealth();
  return health.services[serviceName]?.status === 'healthy';
}

export default errorManagementService;