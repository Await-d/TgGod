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
import apiService from '../services/apiService';
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

  const extractApiPayload = React.useCallback(<T extends { success: boolean }>(response: any): T | null => {
    if (response && typeof response === 'object') {
      if ('success' in response) {
        return response as T;
      }

      if ('data' in response && typeof response.data === 'object' && 'success' in response.data) {
        return response.data as T;
      }
    }

    return null;
  }, []);
  const updateTelegramStatus = React.useCallback((status: TelegramStatus | null) => {
    setTelegramStatus(prev => {
      if (prev === null && status === null) {
        return prev;
      }

      if (status === null || prev === null) {
        return status;
      }

      const sameUser =
        (!!prev.user_info === !!status.user_info) &&
        (!prev.user_info || (
          prev.user_info.id === status.user_info?.id &&
          prev.user_info.username === status.user_info?.username &&
          prev.user_info.first_name === status.user_info?.first_name &&
          prev.user_info.last_name === status.user_info?.last_name
        ));

      if (
        prev.is_authorized === status.is_authorized &&
        prev.message === status.message &&
        sameUser
      ) {
        return prev;
      }

      return status;
    });
  }, [setTelegramStatus]);
  const [activeTab, setActiveTab] = React.useState('system');

  const loadConfigs = React.useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiService.get('/config/configs');
      const payload = extractApiPayload<{ success: boolean; data?: Record<string, ConfigItem> }>(response);
      if (payload?.success && payload.data) {
        setConfigs(payload.data || {});

        // 设置表单初始值
        const formValues: Record<string, string> = {};
        Object.entries(payload.data as Record<string, ConfigItem>).forEach(([key, config]) => {
          formValues[key] = (config as ConfigItem).value;
        });
        form.setFieldsValue(formValues);
      }
    } catch (error) {
      message.error('加载配置失败');
      console.error('Load configs error:', error);
    } finally {
      setLoading(false);
    }
  }, [form, extractApiPayload]);

  const checkTelegramStatus = React.useCallback(async () => {
    try {
      console.log('Settings页面 - 检查Telegram认证状态...');
      const response = await apiService.get('/telegram/auth/status');
      console.log('Settings页面 - Telegram API响应:', response);

      const normalizeStatus = (payload: any): TelegramStatus | null => {
        if (!payload || typeof payload !== 'object') {
          return null;
        }

        if ('is_authorized' in payload) {
          return payload as TelegramStatus;
        }

        if ('data' in payload) {
          return normalizeStatus((payload as any).data);
        }

        if ('success' in payload && (payload as any).success && 'data' in payload) {
          return normalizeStatus((payload as any).data);
        }

        return null;
      };

      const parsedStatus = normalizeStatus(response);

      if (!parsedStatus) {
        console.warn('Telegram状态API返回格式不符合预期:', response);
        updateTelegramStatus({
          is_authorized: false,
          message: '获取认证状态失败',
        });
        return;
      }

      const newStatus: TelegramStatus = {
        is_authorized: parsedStatus.is_authorized,
        user_info: parsedStatus.user_info,
        message: parsedStatus.message || (parsedStatus.is_authorized ? '已授权' : '未授权'),
      };

      console.log('Settings页面 - 即将设置新状态:', newStatus);
      updateTelegramStatus(newStatus);
    } catch (error: any) {
      console.error('检查Telegram状态时出错:', error);
      const errorMessage = error.message || '无法检查Telegram认证状态';
      updateTelegramStatus({
        is_authorized: false,
        message: errorMessage,
      });
    }
  }, [updateTelegramStatus]);

  React.useEffect(() => {
    loadConfigs();
    checkTelegramStatus();
  }, [loadConfigs, checkTelegramStatus]);

  const handleSave = React.useCallback(async () => {
    try {
      setSaving(true);
      const values = await form.validateFields();

      const response = await apiService.post('/config/configs', {
        configs: values
      });

      const payload = extractApiPayload<{ success: boolean; message?: string }>(response);

      if (payload?.success) {
        message.success(payload.message || '保存成功');
        await loadConfigs(); // 重新加载配置
        // 如果修改了Telegram配置，重新检查状态
        if (values.telegram_api_id || values.telegram_api_hash) {
          setTimeout(() => {
            checkTelegramStatus();
          }, 1000);
        }
      } else {
        message.error(payload?.message || '保存失败');
      }
    } catch (error) {
      message.error('保存配置失败');
      console.error('Save configs error:', error);
    } finally {
      setSaving(false);
    }
  }, [form, extractApiPayload, loadConfigs, checkTelegramStatus]);

  const handleTestConnection = React.useCallback(async () => {
    try {
      setTestingConnection(true);

      // 先保存当前配置
      const values = await form.validateFields(['telegram_api_id', 'telegram_api_hash']);

      const saveResponse = await apiService.post('/config/configs', {
        configs: values
      });

      const savePayload = extractApiPayload<{ success: boolean; message?: string }>(saveResponse);
      if (!savePayload?.success) {
        message.error('保存配置失败');
        return;
      }

      // 测试连接
      const response = await apiService.post('/telegram/test-connection');

      const payload = extractApiPayload<{ success: boolean; data?: TelegramTestConnectionResponse; message?: string }>(response);

      if (payload?.success && payload.data) {
        const data = payload.data;
        message.success(`连接测试成功！找到 ${data.stats.total_groups} 个群组`);
        updateTelegramStatus({
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
        const connectionStatus = payload?.data ? (payload.data as Partial<TelegramTestConnectionResponse>).connection_status : undefined;
        if (connectionStatus === 'unauthorized') {
          message.warning('API配置正确，但需要完成Telegram认证');
          updateTelegramStatus({
            is_authorized: false,
            message: '未授权'
          });
        } else {
          message.error(payload?.message || '连接测试失败');
          updateTelegramStatus({
            is_authorized: false,
            message: payload?.message || '连接失败'
          });
        }
      }

    } catch (error) {
      message.error('连接测试失败');
      console.error('Test connection error:', error);
      updateTelegramStatus({
        is_authorized: false,
        message: '连接测试失败'
      });
    } finally {
      setTestingConnection(false);
    }
  }, [form, extractApiPayload, updateTelegramStatus]);

  const handleReset = () => {
    form.resetFields();
    loadConfigs();
  };

  const handleClearCache = React.useCallback(async () => {
    try {
      const response = await apiService.post('/config/configs/clear-cache');
      const payload = extractApiPayload<{ success: boolean; message?: string }>(response);
      if (payload?.success) {
        message.success(payload.message || '清除缓存成功');
      }
    } catch (error) {
      message.error('清除缓存失败');
    }
  }, [extractApiPayload]);

  const handleInitDefaults = React.useCallback(async () => {
    try {
      const response = await apiService.post('/config/configs/init');
      const payload = extractApiPayload<{ success: boolean; message?: string }>(response);
      if (payload?.success) {
        message.success(payload.message || '初始化配置成功');
        await loadConfigs();
      }
    } catch (error) {
      message.error('初始化配置失败');
    }
  }, [extractApiPayload, loadConfigs]);

  const handleTelegramAuthSuccess = React.useCallback((userInfo: any) => {
    updateTelegramStatus({
      is_authorized: true,
      user_info: userInfo,
      message: '认证成功'
    });
    message.success('Telegram认证成功');
    // 刷新连接状态
    checkTelegramStatus();
  }, [updateTelegramStatus, checkTelegramStatus]);

  const handleTelegramAuthError = React.useCallback((error: string) => {
    message.error(`Telegram认证失败: ${error}`);
  }, []);

  const renderTelegramStatus = () => {
    console.log('renderTelegramStatus - 当前状态:', telegramStatus);
    
    if (!telegramStatus) {
      return <Badge status="processing" text="检查中..." />;
    }

    if (telegramStatus.is_authorized) {
      console.log('renderTelegramStatus - 显示已认证状态');
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
      console.log('renderTelegramStatus - 显示未认证状态');
      return <Badge status="error" text={`未认证${telegramStatus.message ? ` (${telegramStatus.message})` : ''}`} />;
    }
  };

  const telegramConfigWarning = React.useMemo(() => {
    if (!telegramStatus || telegramStatus.is_authorized) {
      return null;
    }

    const warningKeywords = ['API 配置缺失', 'API配置不完整'];
    const hasConfigIssue = warningKeywords.some(keyword => telegramStatus.message?.includes(keyword));

    if (!hasConfigIssue) {
      return null;
    }

    return (
      <Alert
        type="warning"
        showIcon
        message="Telegram 配置缺失"
        description="请填写有效的 Telegram API ID 与 API Hash，保存后再进行认证或连接测试。"
        style={{ marginBottom: 16 }}
      />
    );
  }, [telegramStatus]);

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
      {title === 'Telegram 配置' && telegramConfigWarning}
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
