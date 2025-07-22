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
  LoadingOutlined
} from '@ant-design/icons';
import { apiService } from '../services/api';
import { useGlobalStore } from '../store';
import TelegramAuth from '../components/TelegramAuth';

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
      const response = await apiService.get('/telegram/auth/status');
      if (response.success && response.data) {
        setTelegramStatus(response.data as TelegramStatus);
      } else {
        setTelegramStatus({
          is_authorized: false,
          message: response.message || '获取Telegram状态失败'
        } as TelegramStatus);
      }
    } catch (error) {
      console.error('Check Telegram status error:', error);
      setTelegramStatus({
        is_authorized: false,
        message: '无法检查Telegram连接状态'
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
          <Badge status="success" text="已连接" />
          {telegramStatus.user_info && (
            <Text type="secondary">
              ({telegramStatus.user_info.first_name} @{telegramStatus.user_info.username})
            </Text>
          )}
        </Space>
      );
    } else {
      return <Badge status="error" text="未连接" />;
    }
  };

  const renderConfigSection = (title: string, configKeys: string[]) => (
    <Card
      title={title}
      size="small"
      style={{ marginBottom: 16 }}
      extra={title === 'Telegram 配置' && (
        <Space>
          {renderTelegramStatus()}
          <Button
            size="small"
            icon={testingConnection ? <LoadingOutlined /> : <WifiOutlined />}
            onClick={handleTestConnection}
            loading={testingConnection}
            disabled={saving}
          >
            测试连接
          </Button>
        </Space>
      )}
    >
      <Row gutter={16}>
        {configKeys.map(key => {
          const config = configs[key];
          if (!config) return null;

          return (
            <Col span={24} key={key} style={{ marginBottom: 16 }}>
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
                  />
                ) : key === 'allowed_origins' ? (
                  <TextArea
                    rows={3}
                    placeholder='JSON数组格式，例如：["http://localhost:3000"]'
                  />
                ) : (
                  <Input placeholder="请输入" />
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

        <Row justify="space-between">
          <Col>
            <Space>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                loading={saving}
                onClick={handleSave}
              >
                保存配置
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleReset}
                disabled={saving}
              >
                重置
              </Button>
            </Space>
          </Col>
          <Col>
            <Space>
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
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
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
        items={[
          {
            key: 'system',
            label: (
              <span>
                <SettingOutlined />
                系统配置
              </span>
            ),
            children: systemConfigTab,
          },
          {
            key: 'telegram',
            label: (
              <span>
                <WifiOutlined />
                Telegram认证
                {telegramStatus?.is_authorized ? (
                  <CheckCircleOutlined style={{ color: '#52c41a', marginLeft: 8 }} />
                ) : (
                  <CloseCircleOutlined style={{ color: '#ff4d4f', marginLeft: 8 }} />
                )}
              </span>
            ),
            children: telegramAuthTab,
          },
        ]}
      />
    </div>
  );
};

export default Settings;