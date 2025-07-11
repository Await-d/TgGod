import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from 'antd';
import MainLayout from './components/Layout/MainLayout';
import ProtectedRoute from './components/ProtectedRoute';
import Dashboard from './pages/Dashboard';
import Groups from './pages/Groups';
import Messages from './pages/Messages';
import Rules from './pages/Rules';
import Downloads from './pages/Downloads';
import Logs from './pages/Logs';
import Settings from './pages/Settings';
import LoginPage from './pages/Login';
import ChatInterface from './pages/ChatInterface';
import MediaTestPage from './pages/MediaTestPage';
import { webSocketService } from './services/websocket';
import { useGlobalStore, useAuthStore } from './store';
// 导入StagewiseToolbar和ReactPlugin
import { StagewiseToolbar } from '@stagewise/toolbar-react';
import reactPlugin from '@stagewise-plugins/react';

const { Content } = Layout;

const App: React.FC = () => {
  const { setError } = useGlobalStore();
  const { isAuthenticated, initializeAuth } = useAuthStore();

  useEffect(() => {
    // 初始化认证状态
    initializeAuth();

    // 初始化WebSocket连接
    if (isAuthenticated) {
      try {
        webSocketService.connect();
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
        <Route path="/downloads" element={
          <ProtectedRoute>
            <MainLayout>
              <Content>
                <Downloads />
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
        <Route path="/media-test" element={
          <ProtectedRoute>
            <MainLayout>
              <Content>
                <MediaTestPage />
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
      </Routes>
    </div>
  );
};

export default App;