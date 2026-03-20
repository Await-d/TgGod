import React, { useState } from 'react';
import {
  message,
  Alert,
  Tabs,
  Radio,
  Switch,
  Space
} from 'antd';
import {
  SettingOutlined,
  WifiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  UserOutlined,
  IdcardOutlined,
  BulbOutlined
} from '@ant-design/icons';
import PageContainer from '../components/Layout/PageContainer';
import UserSettingsForm from '../components/UserSettings/UserSettingsForm';
import UserProfileForm from '../components/UserSettings/UserProfileForm';
import SystemConfigTab from '../components/Settings/SystemConfigTab';
import apiService from '../services/apiService';
import { useGlobalStore } from '../store';
import TelegramAuth from '../components/TelegramAuth';
import { useIsMobile } from '../hooks/useMobileGestures';
import { useTranslation } from '../i18n';
import { useUserSettingsStore } from '../store/userSettingsStore';
import './Settings.css';

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
  const { t, language } = useTranslation();
  const { settings, setLanguage, setTheme } = useUserSettingsStore();

  const [activeTab, setActiveTab] = React.useState('system');
  const [telegramStatus, setTelegramStatus] = React.useState<TelegramStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 检查 Telegram 状态
  const checkTelegramStatus = React.useCallback(async () => {
    try {
      setError(null);
      const response = await apiService.get('/telegram/auth/status');
      const data = response.data || response;
      setTelegramStatus(data);
    } catch (err) {
      console.error('检查Telegram状态失败:', err);
      setError('检查Telegram状态失败，请重试');
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
    <PageContainer
      title="系统设置"
      description="配置系统参数和 Telegram 认证"
      breadcrumb={[{ title: '系统设置' }]}
      error={error}
      onRetry={checkTelegramStatus}
    >
      {connectionStatus === 'disconnected' && (
        <Alert
          message="连接状态"
          description="后端服务连接断开，请检查服务状态"
          type="warning"
          showIcon
          className="settings-alert"
        />
      )}

      <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
        <Space>
          <span style={{ fontSize: 14 }}>{t('settings.languageLabel')}：</span>
          <Radio.Group
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            buttonStyle="solid"
            size="small"
          >
            <Radio.Button value="zh_CN">中文</Radio.Button>
            <Radio.Button value="en_US">English</Radio.Button>
          </Radio.Group>
        </Space>
        <Space>
          <BulbOutlined />
          <span style={{ fontSize: 14 }}>深色模式</span>
          <Switch
            checked={settings.theme === 'dark'}
            onChange={(checked) => setTheme(checked ? 'dark' : 'light')}
            size="small"
          />
        </Space>
      </div>

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
    </PageContainer>
  );
};

export default Settings;
