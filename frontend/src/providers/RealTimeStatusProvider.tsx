import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { notification } from 'antd';
import { useAuthStore, useRealTimeStatusStore } from '../store';
import { realTimeStatusService } from '../services/realTimeStatusService';
import { webSocketService } from '../services/websocket';
import { ProductionStatusData } from '../types/realtime';

interface RealTimeStatusContextValue {
  reconnect: () => void;
  setAutoRetry: (enabled: boolean) => void;
  isAutoRetryEnabled: boolean;
}

const RealTimeStatusContext = createContext<RealTimeStatusContextValue | undefined>(undefined);

interface ProviderProps {
  children: React.ReactNode;
}

export const RealTimeStatusProvider: React.FC<ProviderProps> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  const setConnectionStatus = useRealTimeStatusStore((state) => state.setConnectionStatus);
  const setCurrentStatus = useRealTimeStatusStore((state) => state.setCurrentStatus);
  const setHealthSummary = useRealTimeStatusStore((state) => state.setHealthSummary);
  const setSystemMetrics = useRealTimeStatusStore((state) => state.setSystemMetrics);
  const resetStore = useRealTimeStatusStore((state) => state.reset);

  const [autoRetryEnabled, updateAutoRetryEnabled] = useState(true);
  const autoRetryRef = useRef(autoRetryEnabled);

  useEffect(() => {
    autoRetryRef.current = autoRetryEnabled;
    realTimeStatusService.setAutoRetry(autoRetryEnabled);
  }, [autoRetryEnabled]);

  useEffect(() => {
    if (!isAuthenticated) {
      realTimeStatusService.setAutoRetry(false);
      setConnectionStatus(false);
      resetStore();
      webSocketService.disconnect();
      return;
    }

    let statusUnsubscribe: (() => void) | undefined;
    let connectionInterval: NodeJS.Timeout | undefined;

    const handleStatusUpdate = (data: ProductionStatusData) => {
      try {
        setCurrentStatus(data);

        const summary = realTimeStatusService.getHealthSummary();
        if (summary) {
          setHealthSummary(summary);
        }

        if (data.system_metrics) {
          setSystemMetrics(data.system_metrics);
        }
      } catch (error) {
        console.error('Error handling status update:', error);
        notification.error({
          message: '实时状态更新失败',
          description: (error as Error).message,
        });
      }
    };

    statusUnsubscribe = realTimeStatusService.onStatusUpdate(handleStatusUpdate);

    if (!webSocketService.isConnected()) {
      webSocketService.connect();
    }

    setConnectionStatus(realTimeStatusService.isConnected());

    connectionInterval = setInterval(() => {
      const connected = realTimeStatusService.isConnected();
      setConnectionStatus(connected);

      if (!connected && autoRetryRef.current) {
        realTimeStatusService.reconnect();
      }
    }, 1000);

    return () => {
      if (statusUnsubscribe) {
        statusUnsubscribe();
      }
      if (connectionInterval) {
        clearInterval(connectionInterval);
      }
    };
  }, [isAuthenticated, setConnectionStatus, setCurrentStatus, setHealthSummary, setSystemMetrics, resetStore]);

  const contextValue = useMemo<RealTimeStatusContextValue>(() => ({
    reconnect: () => realTimeStatusService.reconnect(),
    setAutoRetry: (enabled: boolean) => updateAutoRetryEnabled(enabled),
    isAutoRetryEnabled: autoRetryEnabled,
  }), [autoRetryEnabled]);

  return (
    <RealTimeStatusContext.Provider value={contextValue}>
      {children}
    </RealTimeStatusContext.Provider>
  );
};

export const useRealTimeStatusContext = (): RealTimeStatusContextValue => {
  const context = useContext<RealTimeStatusContextValue | undefined>(RealTimeStatusContext);
  if (!context) {
    throw new Error('useRealTimeStatusContext must be used within RealTimeStatusProvider');
  }
  return context;
};
