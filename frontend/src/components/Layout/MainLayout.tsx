import React from 'react';
import { Layout, Menu, Avatar, Dropdown, Badge, Button, Drawer } from 'antd';
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
  MessageOutlined,
  MenuOutlined,
  PlayCircleOutlined,
  DatabaseOutlined
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
  
  // 检查是否为聊天界面
  const isChatInterface = location.pathname === '/chat';
  
  const [collapsed, setCollapsed] = React.useState(false);
  const [wsConnected, setWsConnected] = React.useState(false);
  const [mobileMenuVisible, setMobileMenuVisible] = React.useState(false);
  const [isMobile, setIsMobile] = React.useState(false);

  React.useEffect(() => {
    // 检查是否为移动设备
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

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
      key: '/chat',
      icon: <MessageOutlined />,
      label: '聊天界面',
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
      key: '/tasks',
      icon: <PlayCircleOutlined />,
      label: '任务管理',
    },
    {
      key: '/logs',
      icon: <FileTextOutlined />,
      label: '日志查看',
    },
    {
      key: '/database',
      icon: <DatabaseOutlined />,
      label: '数据库状态',
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
    // 移动端点击菜单后关闭抽屉
    if (isMobile) {
      setMobileMenuVisible(false);
    }
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
    <Layout style={{ 
      minHeight: isChatInterface ? '100vh' : '100vh',
      height: isChatInterface ? '100vh' : 'auto',
      overflow: isChatInterface ? 'hidden' : 'auto'
    }}>
      {/* 桌面端侧边栏 */}
      {!isMobile && (
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
      )}
      
      {/* 移动端导航抽屉 */}
      <Drawer
        title="TgGod"
        placement="left"
        onClose={() => setMobileMenuVisible(false)}
        open={mobileMenuVisible}
        styles={{
          body: { padding: 0 },
          header: { 
            background: '#001529', 
            color: 'white',
            borderBottom: '1px solid #303030'
          }
        }}
        width={250}
      >
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ height: '100%', borderRight: 0 }}
        />
      </Drawer>
      
      <Layout>
        <Header style={{ 
          padding: isMobile ? '0 16px' : '0 24px', 
          background: '#fff',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          boxShadow: '0 1px 4px rgba(0,21,41,.08)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? '8px' : '16px' }}>
            {/* 移动端菜单按钮 */}
            {isMobile && (
              <Button 
                type="text" 
                icon={<MenuOutlined />}
                onClick={() => setMobileMenuVisible(true)}
                style={{ padding: '4px 8px' }}
              />
            )}
            
            <h1 style={{ 
              margin: 0, 
              fontSize: isMobile ? '16px' : '20px', 
              color: '#1890ff',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}>
              {isMobile ? 'TgGod' : 'Telegram群组下载系统'}
            </h1>
            
            {/* WebSocket连接状态 */}
            {!isMobile && (
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
            )}
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? '8px' : '16px' }}>
            {/* 错误提示 */}
            {error && (
              <Button 
                type="text" 
                danger 
                size="small"
                onClick={clearError}
                style={{ maxWidth: isMobile ? '120px' : 'none' }}
              >
                {isMobile ? '错误' : error}
              </Button>
            )}
            
            {/* 通知 */}
            <Badge count={0} showZero={false}>
              <BellOutlined style={{ fontSize: '16px', color: '#666' }} />
            </Badge>
            
            {/* 用户信息 */}
            {!isMobile && (
              <span style={{ fontSize: '14px', color: '#666' }}>
                欢迎，{user?.username}
              </span>
            )}
            
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
          margin: isChatInterface ? 0 : (isMobile ? '16px 8px' : '24px 16px'),
          padding: isChatInterface ? 0 : (isMobile ? 16 : 24),
          background: isChatInterface ? 'transparent' : '#fff',
          borderRadius: isChatInterface ? 0 : '8px',
          minHeight: isChatInterface ? 0 : 280,
          overflow: isChatInterface ? 'hidden' : 'auto',
          height: isChatInterface ? '100%' : 'auto'
        }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;