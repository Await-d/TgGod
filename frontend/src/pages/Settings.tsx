import React from 'react';
import {
  message,
  Typography,
  Alert,
  Tabs
} from 'antd';
import {
  SettingOutlined,
  WifiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  UserOutlined,
  IdcardOutlined
} from '@ant-design/icons';
import UserSettingsForm from '../components/UserSettings/UserSettingsForm';
import UserProfileForm from '../components/UserSettings/UserProfileForm';
import SystemConfigTab from '../components/Settings/SystemConfigTab';
import apiService from '../services/apiService';
import { useGlobalStore } from '../store';
import TelegramAuth from '../components/TelegramAuth';
import { useIsMobile } from '../hooks/useMobileGestures';
import './Settings.css';

const { Title, Text } = Typography;

interface TelegramStatus {
  is_authorized: boolean;
  user_info?: {
    id: number;
    first_name: string;
    last_name?: string;
    username?: string;
    phone?: string;
  };
  message: string;
}

const Settings: React.FC = () => {
  const isMobile = useIsMobile();
  const { connectionStatus } = useGlobalStore();

  const [activeTab, setActiveTab] = React.useState('system');
  const [telegramStatus, setTelegramStatus] = React.useState<TelegramStatus | null>(null);

  // 检查 Telegram 状态
  const checkTelegramStatus = React.useCallback(async () => {
    try {
      const response = await apiService.get('/telegram/auth/status');
      const data = response.data || response;
      setTelegramStatus(data);
    } catch (error) {
      console.error('检查Telegram状态失败:', error);
      setTelegramStatus({
        is_authorized: false,
        message: '检查状态失败'
      });
    }
  }, []);

  React.useEffect(() => {
    checkTelegramStatus();
  }, [checkTelegramStatus]);

  // Telegram 认证成功回调
  const handleTelegramAuthSuccess = React.useCallback((userInfo: any) => {
    setTelegramStatus({
      is_authorized: true,
      user_info: userInfo,
      message: '认证成功'
    });
    message.success('Telegram认证成功');
    checkTelegramStatus();
  }, [checkTelegramStatus]);

  // Telegram 认证失败回调
  const handleTelegramAuthError = React.useCallback((error: string) => {
    message.error(`Telegram认证失败: ${error}`);
  }, []);

  const systemConfigTab = <SystemConfigTab />;

  const telegramAuthTab = (
    <div>
      <Alert
        message="Telegram 认证说明"
        description={
          <div>
            <p>• 完成认证后才能使用群组消息管理功能</p>
            <p>• 认证信息仅存储在本地，安全可靠</p>
            <p>• 支持两步验证，保护账户安全</p>
            <p>• 配置Telegram API后请先测试连接状态</p>
          </div>
        }
        type="info"
        showIcon
        className="settings-alert"
      />

      <TelegramAuth
        onAuthSuccess={handleTelegramAuthSuccess}
        onAuthError={handleTelegramAuthError}
      />
    </div>
  );

  return (
    <div className="settings-page">
      <div className="settings-header">
        <Title level={isMobile ? 3 : 2} className="settings-title">
          <SettingOutlined className="settings-title-icon" />
          系统设置
        </Title>
        <Text type="secondary">
          配置系统运行所需的参数和Telegram认证。
        </Text>
      </div>

      {connectionStatus === 'disconnected' && (
        <Alert
          message="连接状态"
          description="后端服务连接断开，请检查服务状态"
          type="warning"
          showIcon
          className="settings-alert"
        />
      )}

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        tabPosition={isMobile ? "top" : "top"}
        size={isMobile ? "small" : "middle"}
        destroyOnHidden={false}
        items={[
          {
            key: 'system',
            label: (
              <span>
                <SettingOutlined />
                {isMobile ? '系统' : '系统配置'}
              </span>
            ),
            children: systemConfigTab,
          },
          {
            key: 'telegram',
            label: (
              <span>
                <WifiOutlined />
                {isMobile ? 'TG' : 'Telegram认证'}
                {telegramStatus?.is_authorized ? (
                  <CheckCircleOutlined className="settings-tab-status settings-tab-status-success" />
                ) : (
                  <CloseCircleOutlined className="settings-tab-status settings-tab-status-warning" />
                )}
              </span>
            ),
            children: telegramAuthTab,
          },
          {
            key: 'user',
            label: (
              <span>
                <UserOutlined />
                {isMobile ? '偏好' : '偏好设置'}
              </span>
            ),
            children: <UserSettingsForm />,
          },
          {
            key: 'profile',
            label: (
              <span>
                <IdcardOutlined />
                {isMobile ? '资料' : '个人资料'}
              </span>
            ),
            children: <UserProfileForm />,
          },
        ]}
      />
    </div>
  );
};

export default Settings;
