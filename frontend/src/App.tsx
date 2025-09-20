import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from 'antd';
import MainLayout from './components/Layout/MainLayout';
import ProtectedRoute from './components/ProtectedRoute';
import Dashboard from './pages/Dashboard';
import Groups from './pages/Groups';
import Messages from './pages/Messages';
import Rules from './pages/Rules';
import Logs from './pages/Logs';
import Settings from './pages/Settings';
import DatabaseStatus from './pages/DatabaseStatus';
import LoginPage from './pages/Login';
import ChatInterface from './pages/ChatInterface';
import TaskManagement from './pages/TaskManagement';
import DownloadHistory from './pages/DownloadHistory';
import { RealTimeStatusMonitor } from './components/StatusMonitor';
import { webSocketService } from './services/websocket';
import { realTimeStatusService } from './services/realTimeStatusService';
import { useGlobalStore, useAuthStore, useUserSettingsStore, useRealTimeStatusStore } from './store';
import ThemeProvider from './components/UserSettings/ThemeProvider';
import './styles/themes.css';
// 导入StagewiseToolbar和ReactPlugin
import { StagewiseToolbar } from '@stagewise/toolbar-react';
import reactPlugin from '@stagewise-plugins/react';

const { Content } = Layout;

const App: React.FC = () => {
  // 获取用户设置以应用布局密度
  const { settings } = useUserSettingsStore();

  // 应用布局密度设置
  useEffect(() => {
    document.documentElement.setAttribute('data-density', settings.displayDensity);
  }, [settings.displayDensity]);
  const { setError } = useGlobalStore();
  const { isAuthenticated, initializeAuth } = useAuthStore();
  const { setConnectionStatus } = useRealTimeStatusStore();

  useEffect(() => {
    // 初始化认证状态
    initializeAuth();

    // 初始化WebSocket连接和实时状态服务
    if (isAuthenticated) {
      try {
        webSocketService.connect();

        // 初始化实时状态服务连接状态监控
        const checkConnectionStatus = () => {
          setConnectionStatus(realTimeStatusService.isConnected());
        };

        // 立即检查一次连接状态
        checkConnectionStatus();

        // 定期检查连接状态
        const connectionInterval = setInterval(checkConnectionStatus, 1000);

        // 清理函数会在组件卸载或依赖变化时执行
        return () => {
          clearInterval(connectionInterval);
        };

      } catch (error) {
        setError('WebSocket连接失败');
        console.error('WebSocket连接失败:', error);
      }
    }

    // 清理函数
    return () => {
      webSocketService.disconnect();
    };
  }, [setError, isAuthenticated, initializeAuth]);

  return (
    <ThemeProvider>
      <div className="app-container">
        {/* 集成StagewiseToolbar组件 - 只在开发环境下显示 */}
        <StagewiseToolbar config={{ plugins: [reactPlugin] }} />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={
            <ProtectedRoute>
              <MainLayout>
                <Content>
                  <Navigate to="/dashboard" replace />
                </Content>
              </MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <MainLayout>
                <Content>
                  <Dashboard />
                </Content>
              </MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/groups" element={
            <ProtectedRoute>
              <MainLayout>
                <Content>
                  <Groups />
                </Content>
              </MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/messages" element={
            <ProtectedRoute>
              <MainLayout>
                <Content>
                  <Messages />
                </Content>
              </MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/rules" element={
            <ProtectedRoute>
              <MainLayout>
                <Content>
                  <Rules />
                </Content>
              </MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/tasks" element={
            <ProtectedRoute>
              <MainLayout>
                <Content>
                  <TaskManagement />
                </Content>
              </MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/download-history" element={
            <ProtectedRoute>
              <MainLayout>
                <Content>
                  <DownloadHistory />
                </Content>
              </MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/logs" element={
            <ProtectedRoute>
              <MainLayout>
                <Content>
                  <Logs />
                </Content>
              </MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/chat" element={
            <ProtectedRoute>
              <MainLayout>
                <Content className="chat-interface-content">
                  <ChatInterface />
                </Content>
              </MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/database" element={
            <ProtectedRoute>
              <MainLayout>
                <Content>
                  <DatabaseStatus />
                </Content>
              </MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/settings" element={
            <ProtectedRoute>
              <MainLayout>
                <Content>
                  <Settings />
                </Content>
              </MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/status" element={
            <ProtectedRoute>
              <MainLayout>
                <Content>
                  <RealTimeStatusMonitor />
                </Content>
              </MainLayout>
            </ProtectedRoute>
          } />
        </Routes>
      </div>
    </ThemeProvider>
  );
};

export default App;