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
import SystemStatus from './pages/SystemStatus';
import LoginPage from './pages/Login';
import ChatInterface from './pages/ChatInterface';
import TaskManagement from './pages/TaskManagement';
import DownloadHistory from './pages/DownloadHistory';
import { RealTimeStatusMonitor } from './components/StatusMonitor';
import { useAuthStore, useUserSettingsStore } from './store';
import ThemeProvider from './components/UserSettings/ThemeProvider';
import { RealTimeStatusProvider } from './providers/RealTimeStatusProvider';
import './styles/themes.css';

const { Content } = Layout;

const App: React.FC = () => {
  // 获取用户设置以应用布局密度
  const { settings } = useUserSettingsStore();

  // 应用布局密度设置
  useEffect(() => {
    document.documentElement.setAttribute('data-density', settings.displayDensity);
  }, [settings.displayDensity]);
  const { initializeAuth } = useAuthStore();

  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  return (
    <ThemeProvider>
      <RealTimeStatusProvider>
        <div className="app-container">
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
                  <SystemStatus />
                </Content>
              </MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/realtime-status" element={
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
      </RealTimeStatusProvider>
    </ThemeProvider>
  );
};

export default App;
