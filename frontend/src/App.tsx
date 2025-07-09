import React, { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Layout } from 'antd';
import MainLayout from './components/Layout/MainLayout';
import Dashboard from './pages/Dashboard';
import Groups from './pages/Groups';
import Rules from './pages/Rules';
import Downloads from './pages/Downloads';
import Logs from './pages/Logs';
import Settings from './pages/Settings';
import { webSocketService } from './services/websocket';
import { useGlobalStore } from './store';

const { Content } = Layout;

const App: React.FC = () => {
  const { setError } = useGlobalStore();

  useEffect(() => {
    // 初始化WebSocket连接
    try {
      webSocketService.connect();
    } catch (error) {
      setError('WebSocket连接失败');
      console.error('WebSocket连接失败:', error);
    }

    // 清理函数
    return () => {
      webSocketService.disconnect();
    };
  }, [setError]);

  return (
    <div className="app-container">
      <MainLayout>
        <Content>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/groups" element={<Groups />} />
            <Route path="/rules" element={<Rules />} />
            <Route path="/downloads" element={<Downloads />} />
            <Route path="/logs" element={<Logs />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Content>
      </MainLayout>
    </div>
  );
};

export default App;