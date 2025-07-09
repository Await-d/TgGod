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
import { webSocketService } from './services/websocket';
import { useGlobalStore, useAuthStore } from './store';

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
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={
          <ProtectedRoute>
            <MainLayout>
              <Content>
                <Routes>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/groups" element={<Groups />} />
                  <Route path="/messages" element={<Messages />} />
                  <Route path="/rules" element={<Rules />} />
                  <Route path="/downloads" element={<Downloads />} />
                  <Route path="/logs" element={<Logs />} />
                  <Route path="/settings" element={<Settings />} />
                </Routes>
              </Content>
            </MainLayout>
          </ProtectedRoute>
        } />
      </Routes>
    </div>
  );
};

export default App;