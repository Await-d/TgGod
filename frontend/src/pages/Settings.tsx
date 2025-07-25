import React from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Space,
  message,
  Typography,
  Alert,
  Divider,
  Row,
  Col,
  Spin,
  Badge,
  Tabs
} from 'antd';
import {
  SettingOutlined,
  SaveOutlined,
  ReloadOutlined,
  ClearOutlined,
  WifiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  UserOutlined
} from '@ant-design/icons';
import UserSettingsForm from '../components/UserSettings/UserSettingsForm';
import { apiService } from '../services/api';
import { useGlobalStore } from '../store';
import TelegramAuth from '../components/TelegramAuth';
import { useIsMobile } from '../hooks/useMobileGestures';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface ConfigItem {
  value: string;
  description: string;
  is_encrypted: boolean;
}

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

interface TelegramTestConnectionResponse {
  stats: {
    total_groups: number;
    groups_preview: Array<{
      name: string;
      id: number;
    }>;
  };
  user_info: {
    id: number;
    first_name: string;
    last_name?: string;
    username?: string;
  };
  connection_status?: string;
}

const Settings: React.FC = () => {
  const isMobile = useIsMobile();
  const [form] = Form.useForm();
  const { connectionStatus } = useGlobalStore();
  const [loading, setLoading] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [testingConnection, setTestingConnection] = React.useState(false);
  const [configs, setConfigs] = React.useState<Record<string, ConfigItem>>({});
  const [telegramStatus, setTelegramStatus] = React.useState<TelegramStatus | null>(null);
  const [activeTab, setActiveTab] = React.useState('system');

  const loadConfigs = React.useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiService.get('/config/configs');
      if (response.success && response.data) {
        setConfigs(response.data as Record<string, ConfigItem> || {});

        // 设置表单初始值
        const formValues: Record<string, string> = {};
        Object.entries(response.data).forEach(([key, config]) => {
          formValues[key] = config.value;
        });
        form.setFieldsValue(formValues);
      }
    } catch (error) {
      message.error('加载配置失败');
      console.error('Load configs error:', error);
    } finally {
      setLoading(false);
    }
  }, [form]);

  const checkTelegramStatus = React.useCallback(async () => {
    try {
      console.log('Settings页面 - 检查Telegram认证状态...');
      const response = await apiService.get('/telegram/auth/status');
      console.log('Settings页面 - Telegram API响应:', response);
      
      if (response.success && response.data) {
        console.log('Settings页面 - Telegram状态数据:', response.data);
        // 确保响应数据是预期的格式
        const statusData = response.data as TelegramStatus;
        
        // 即使后端返回数据，也确保数据结构符合预期
        if (typeof statusData.is_authorized === 'boolean') {
          setTelegramStatus(statusData);
          
          // 如果认证成功但没有用户信息，尝试添加默认用户信息避免UI错误
          if (statusData.is_authorized && !statusData.user_info) {
            console.warn('后端返回认证成功但无用户信息');
          }
        } else {
          console.warn('Telegram状态数据格式不正确:', statusData);
          // 构造一个安全的默认状态
          setTelegramStatus({
            is_authorized: false,
            message: '返回的认证数据格式不正确'
          });
        }
      } else {
        console.warn('Telegram状态API返回失败响应', response);
        // 使用更友好的错误消息
        const errorMessage = response.message || '获取Telegram认证状态失败';
        message.warning(`Telegram认证状态检查: ${errorMessage}`);
        setTelegramStatus({
          is_authorized: false,
          message: errorMessage
        } as TelegramStatus);
      }
    } catch (error: any) {
      console.error('检查Telegram状态时出错:', error);
      const errorMessage = error.message || '无法检查Telegram认证状态';
      message.error(`Telegram认证状态错误: ${errorMessage}`);
      setTelegramStatus({
        is_authorized: false,
        message: errorMessage
      });
    }
  }, []);

  React.useEffect(() => {
    loadConfigs();
    checkTelegramStatus();
  }, [loadConfigs, checkTelegramStatus]);

  const handleSave = async () => {
    try {
      setSaving(true);
      const values = await form.validateFields();

      const response = await apiService.post('/config/configs', {
        configs: values
      });

      if (response.success) {
        message.success(response.message || '保存成功');
        await loadConfigs(); // 重新加载配置
        // 如果修改了Telegram配置，重新检查状态
        if (values.telegram_api_id || values.telegram_api_hash) {
          setTimeout(() => {
            checkTelegramStatus();
          }, 1000);
        }
      } else {
        message.error(response.message || '保存失败');
      }
    } catch (error) {
      message.error('保存配置失败');
      console.error('Save configs error:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    try {
      setTestingConnection(true);

      // 先保存当前配置
      const values = await form.validateFields(['telegram_api_id', 'telegram_api_hash']);

      const saveResponse = await apiService.post('/config/configs', {
        configs: values
      });

      if (!saveResponse.success) {
        message.error('保存配置失败');
        return;
      }

      // 测试连接
      const response = await apiService.post('/telegram/test-connection');

      if (response.success && response.data) {
        const data = response.data as TelegramTestConnectionResponse;
        message.success(`连接测试成功！找到 ${data.stats.total_groups} 个群组`);
        setTelegramStatus({
          is_authorized: true,
          user_info: data.user_info,
          message: '连接成功'
        });

        // 显示群组预览
        if (data.stats.groups_preview && data.stats.groups_preview.length > 0) {
          const groupNames = data.stats.groups_preview.map(g => g.name).join(', ');
          message.info(`群组预览: ${groupNames}`, 5);
        }
      } else {
        const connectionStatus = (response.data as Partial<TelegramTestConnectionResponse>)?.connection_status;
        if (connectionStatus === 'unauthorized') {
          message.warning('API配置正确，但需要完成Telegram认证');
          setTelegramStatus({
            is_authorized: false,
            message: '未授权'
          });
        } else {
          message.error(response.message || '连接测试失败');
          setTelegramStatus({
            is_authorized: false,
            message: response.message || '连接失败'
          });
        }
      }

    } catch (error) {
      message.error('连接测试失败');
      console.error('Test connection error:', error);
      setTelegramStatus({
        is_authorized: false,
        message: '连接测试失败'
      });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleReset = () => {
    form.resetFields();
    loadConfigs();
  };

  const handleClearCache = async () => {
    try {
      const response = await apiService.post('/config/configs/clear-cache');
      if (response.success) {
        message.success('清除缓存成功');
      }
    } catch (error) {
      message.error('清除缓存失败');
    }
  };

  const handleInitDefaults = async () => {
    try {
      const response = await apiService.post('/config/configs/init');
      if (response.success) {
        message.success('初始化配置成功');
        await loadConfigs();
      }
    } catch (error) {
      message.error('初始化配置失败');
    }
  };

  const handleTelegramAuthSuccess = (userInfo: any) => {
    setTelegramStatus({
      is_authorized: true,
      user_info: userInfo,
      message: '认证成功'
    });
    message.success('Telegram认证成功');
    // 刷新连接状态
    checkTelegramStatus();
  };

  const handleTelegramAuthError = (error: string) => {
    message.error(`Telegram认证失败: ${error}`);
  };

  const renderTelegramStatus = () => {
    if (!telegramStatus) {
      return <Badge status="processing" text="检查中..." />;
    }

    if (telegramStatus.is_authorized) {
      return (
        <Space>
          <Badge status="success" text="已认证" />
          {telegramStatus.user_info && (
            <Text type="secondary">
              ({telegramStatus.user_info.first_name} {telegramStatus.user_info.username ? `@${telegramStatus.user_info.username}` : ''})
            </Text>
          )}
        </Space>
      );
    } else {
      return <Badge status="error" text="未认证" />;
    }
  };

  const renderConfigSection = (title: string, configKeys: string[]) => (
    <Card
      title={title}
      size={isMobile ? "small" : "default"}
      style={{ marginBottom: 16 }}
      extra={title === 'Telegram 配置' && (
        <Space direction={isMobile ? "vertical" : "horizontal"} size="small">
          {renderTelegramStatus()}
          <Button
            size="small"
            icon={testingConnection ? <LoadingOutlined /> : <WifiOutlined />}
            onClick={handleTestConnection}
            loading={testingConnection}
            disabled={saving}
          >
            {isMobile ? '测试' : '测试连接'}
          </Button>
        </Space>
      )}
    >
      <Row gutter={isMobile ? [8, 8] : 16}>
        {configKeys.map(key => {
          const config = configs[key];
          if (!config) return null;

          return (
            <Col span={24} key={key} style={{ marginBottom: isMobile ? 12 : 16 }}>
              <Form.Item
                label={key}
                name={key}
                help={config.description}
                rules={[
                  {
                    required: ['telegram_api_id', 'telegram_api_hash', 'secret_key'].includes(key),
                    message: '此字段为必填项'
                  }
                ]}
              >
                {config.is_encrypted ? (
                  <Input.Password
                    placeholder={config.value === '***' ? '不修改请留空' : '请输入'}
                    autoComplete="new-password"
                    size={isMobile ? "large" : "middle"}
                  />
                ) : key === 'allowed_origins' ? (
                  <TextArea
                    rows={isMobile ? 2 : 3}
                    placeholder='JSON数组格式，例如：["http://localhost:3000"]'
                    size={isMobile ? "large" : "middle"}
                  />
                ) : (
                  <Input 
                    placeholder="请输入" 
                    size={isMobile ? "large" : "middle"}
                  />
                )}
              </Form.Item>
            </Col>
          );
        })}
      </Row>
    </Card>
  );

  const systemConfigTab = (
    <Spin spinning={loading}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSave}
      >
        {renderConfigSection('Telegram 配置', ['telegram_api_id', 'telegram_api_hash'])}
        {renderConfigSection('安全配置', ['secret_key'])}
        {renderConfigSection('数据库配置', ['database_url'])}
        {renderConfigSection('日志配置', ['log_level', 'log_file'])}
        {renderConfigSection('文件存储', ['media_root'])}
        {renderConfigSection('跨域配置', ['allowed_origins'])}

        <Divider />

        <Row justify={isMobile ? "center" : "space-between"} gutter={[16, 16]}>
          <Col xs={24} sm={12}>
            <Space direction={isMobile ? "vertical" : "horizontal"} style={{ width: '100%', justifyContent: 'center' }}>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                loading={saving}
                onClick={handleSave}
                size={isMobile ? "large" : "middle"}
                block={isMobile}
              >
                保存配置
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleReset}
                disabled={saving}
                size={isMobile ? "large" : "middle"}
                block={isMobile}
              >
                重置
              </Button>
            </Space>
          </Col>
          {!isMobile && (
            <Col sm={12}>
              <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                <Button
                  type="dashed"
                  icon={<ClearOutlined />}
                  onClick={handleClearCache}
                  disabled={saving}
                >
                  清除缓存
                </Button>
                <Button
                  type="dashed"
                  onClick={handleInitDefaults}
                  disabled={saving}
                >
                  初始化默认配置
                </Button>
              </Space>
            </Col>
          )}
          {isMobile && (
            <Col xs={24}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Button
                  type="dashed"
                  icon={<ClearOutlined />}
                  onClick={handleClearCache}
                  disabled={saving}
                  size="large"
                  block
                >
                  清除缓存
                </Button>
                <Button
                  type="dashed"
                  onClick={handleInitDefaults}
                  disabled={saving}
                  size="large"
                  block
                >
                  初始化默认配置
                </Button>
              </Space>
            </Col>
          )}
        </Row>
      </Form>
    </Spin>
  );

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
        style={{ marginBottom: 24 }}
      />

      <TelegramAuth
        onAuthSuccess={handleTelegramAuthSuccess}
        onAuthError={handleTelegramAuthError}
      />
    </div>
  );

  return (
    <div style={{ padding: isMobile ? '16px' : '24px' }}>
      <div style={{ marginBottom: isMobile ? 16 : 24 }}>
        <Title level={isMobile ? 3 : 2}>
          <SettingOutlined style={{ marginRight: 8 }} />
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
          style={{ marginBottom: 24 }}
        />
      )}

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        tabPosition={isMobile ? "top" : "top"}
        size={isMobile ? "small" : "middle"}
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
                  <CheckCircleOutlined style={{ color: '#52c41a', marginLeft: 4 }} />
                ) : (
                  <CloseCircleOutlined style={{ color: '#ff4d4f', marginLeft: 4 }} />
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
                {isMobile ? '用户' : '用户设置'}
              </span>
            ),
            children: <UserSettingsForm />,
          },
        ]}
      />
    </div>
  );
};

export default Settings;