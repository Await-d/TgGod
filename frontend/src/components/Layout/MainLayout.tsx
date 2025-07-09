import React from 'react';
import { Layout, Menu, Avatar, Dropdown, Badge, Button } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  DashboardOutlined,
  TeamOutlined,
  FilterOutlined,
  DownloadOutlined,
  FileTextOutlined,
  BellOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  WifiOutlined,
  DisconnectOutlined,
  MessageOutlined
} from '@ant-design/icons';
import { webSocketService } from '../../services/websocket';
import { useGlobalStore, useAuthStore } from '../../store';
import { authApi } from '../../services/apiService';

const { Header, Sider, Content } = Layout;

interface MainLayoutProps {
  children: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { error, clearError } = useGlobalStore();
  const { user, logout } = useAuthStore();
  
  const [collapsed, setCollapsed] = React.useState(false);
  const [wsConnected, setWsConnected] = React.useState(false);

  React.useEffect(() => {
    // 监听WebSocket连接状态
    const checkConnection = () => {
      setWsConnected(webSocketService.isConnected());
    };
    
    const interval = setInterval(checkConnection, 1000);
    checkConnection();
    
    return () => clearInterval(interval);
  }, []);

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '仪表板',
    },
    {
      key: '/groups',
      icon: <TeamOutlined />,
      label: '群组管理',
    },
    {
      key: '/messages',
      icon: <MessageOutlined />,
      label: '消息管理',
    },
    {
      key: '/rules',
      icon: <FilterOutlined />,
      label: '规则配置',
    },
    {
      key: '/downloads',
      icon: <DownloadOutlined />,
      label: '下载任务',
    },
    {
      key: '/logs',
      icon: <FileTextOutlined />,
      label: '日志查看',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
  ];

  const userMenuItems = [
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出',
    },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      handleLogout();
    } else if (key === 'settings') {
      navigate('/settings');
    }
  };

  const handleLogout = async () => {
    try {
      await authApi.logout();
      logout();
      navigate('/login');
    } catch (error) {
      console.error('退出登录失败:', error);
      // 即使API调用失败，也要清除本地状态
      logout();
      navigate('/login');
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider 
        collapsible 
        collapsed={collapsed} 
        onCollapse={setCollapsed}
        theme="dark"
      >
        <div style={{ 
          height: 64, 
          padding: '16px', 
          color: 'white', 
          fontSize: '18px',
          fontWeight: 'bold',
          textAlign: 'center'
        }}>
          {collapsed ? 'TG' : 'TgGod'}
        </div>
        
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      
      <Layout>
        <Header style={{ 
          padding: '0 24px', 
          background: '#fff',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          boxShadow: '0 1px 4px rgba(0,21,41,.08)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <h1 style={{ margin: 0, fontSize: '20px', color: '#1890ff' }}>
              Telegram群组下载系统
            </h1>
            
            {/* WebSocket连接状态 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {wsConnected ? (
                <WifiOutlined style={{ color: '#52c41a' }} />
              ) : (
                <DisconnectOutlined style={{ color: '#f5222d' }} />
              )}
              <span style={{ 
                fontSize: '12px', 
                color: wsConnected ? '#52c41a' : '#f5222d' 
              }}>
                {wsConnected ? '已连接' : '未连接'}
              </span>
            </div>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {/* 错误提示 */}
            {error && (
              <Button 
                type="text" 
                danger 
                size="small"
                onClick={clearError}
              >
                {error}
              </Button>
            )}
            
            {/* 通知 */}
            <Badge count={0} showZero={false}>
              <BellOutlined style={{ fontSize: '16px', color: '#666' }} />
            </Badge>
            
            {/* 用户信息 */}
            <span style={{ fontSize: '14px', color: '#666' }}>
              欢迎，{user?.username}
            </span>
            
            {/* 用户菜单 */}
            <Dropdown
              menu={{
                items: userMenuItems,
                onClick: handleUserMenuClick,
              }}
              placement="bottomRight"
            >
              <Avatar 
                size="small" 
                icon={<UserOutlined />} 
                style={{ cursor: 'pointer' }}
              />
            </Dropdown>
          </div>
        </Header>
        
        <Content style={{ 
          margin: '24px 16px',
          padding: 24,
          background: '#fff',
          borderRadius: '8px',
          minHeight: 280,
          overflow: 'auto'
        }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;