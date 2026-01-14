import React from 'react';
import {
  Form,
  Input,
  Button,
  Space,
  message,
  Divider,
  Row,
  Col,
  Spin,
  Card,
  Badge,
  Alert,
} from 'antd';
import {
  SaveOutlined,
  ReloadOutlined,
  ClearOutlined,
  WifiOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import apiService from '../../services/apiService';
import { useIsMobile } from '../../hooks/useMobileGestures';

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

const SystemConfigTab: React.FC = () => {
  const [form] = Form.useForm();
  const isMobile = useIsMobile();
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

  const loadConfigs = React.useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiService.get('/config/configs');
      const payload = extractApiPayload<{ success: boolean; data: Record<string, ConfigItem> }>(response);

      if (payload && payload.success) {
        setConfigs(payload.data || {});

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

  // 配置项中文标签映射
  const configLabels: Record<string, string> = {
    telegram_api_id: 'Telegram API ID',
    telegram_api_hash: 'Telegram API Hash',
    secret_key: 'JWT密钥',
    database_url: '数据库地址',
    log_level: '日志级别',
    log_file: '日志文件路径',
    media_root: '媒体文件存储路径',
    allowed_origins: '允许的跨域来源',
  };

  React.useEffect(() => {
    loadConfigs();
    checkTelegramStatus();
  }, [loadConfigs, checkTelegramStatus]);

  const handleSave = React.useCallback(async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      // 转换为后端期待的格式: {configs: {key: value, ...}}
      const configs: Record<string, string> = {};
      Object.keys(values).forEach(key => {
        configs[key] = values[key] || '';
      });

      await apiService.post('/config/configs', { configs });
      message.success('配置已保存');
      await loadConfigs();
      await checkTelegramStatus();
    } catch (error: any) {
      if (error.errorFields) {
        message.error('请检查表单填写');
        return;
      }
      message.error('保存配置失败');
      console.error('Save error:', error);
    } finally {
      setSaving(false);
    }
  }, [form, loadConfigs, checkTelegramStatus]);

  const handleReset = () => {
    form.resetFields();
    message.info('表单已重置');
  };

  const handleClearCache = async () => {
    try {
      await apiService.post('/system/clear-cache');
      message.success('缓存已清除');
    } catch (error) {
      console.error('清除缓存失败:', error);
      message.error('清除缓存失败');
    }
  };

  const handleInitDefaults = async () => {
    try {
      await apiService.post('/config/init-defaults');
      message.success('默认配置已初始化');
      await loadConfigs();
    } catch (error) {
      console.error('初始化默认配置失败:', error);
      message.error('初始化默认配置失败');
    }
  };

  const handleTestConnection = React.useCallback(async () => {
    try {
      const values = await form.validateFields(['telegram_api_id', 'telegram_api_hash']);
      
      if (!values.telegram_api_id || !values.telegram_api_hash) {
        message.warning('请先填写 Telegram API ID 和 API Hash');
        return;
      }

      setTestingConnection(true);

      const response = await apiService.post('/telegram/test-connection', {
        api_id: values.telegram_api_id,
        api_hash: values.telegram_api_hash
      });

      const testResult = extractApiPayload<TelegramTestConnectionResponse & { success: boolean }>(response);

      if (testResult && testResult.stats) {
        const totalGroups = testResult.stats.total_groups;
        const groupsPreview = testResult.stats.groups_preview || [];
        const previewText = groupsPreview.map((g: { name: string; id: number }) => `${g.name} (ID: ${g.id})`).join(', ');

        message.success(
          `连接成功！找到 ${totalGroups} 个群组${previewText ? `，预览：${previewText}` : ''}`,
          5
        );
        await checkTelegramStatus();
      } else {
        message.error('连接测试失败');
      }
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || '连接测试失败';
      message.error(errorMsg);
      console.error('Test connection error:', error);
    } finally {
      setTestingConnection(false);
    }
  }, [form, extractApiPayload, checkTelegramStatus]);

  const renderTelegramStatus = () => {
    if (!telegramStatus) {
      return <Badge status="processing" text="检查中..." />;
    }

    if (telegramStatus.is_authorized) {
      return (
        <Space>
          <Badge status="success" text="已认证" />
          {telegramStatus.user_info && (
            <span style={{ fontSize: '12px', color: '#8c8c8c' }}>
              ({telegramStatus.user_info.first_name} {telegramStatus.user_info.username ? `@${telegramStatus.user_info.username}` : ''})
            </span>
          )}
        </Space>
      );
    } else {
      return <Badge status="error" text={`未认证${telegramStatus.message ? ` (${telegramStatus.message})` : ''}`} />;
    }
  };

  const telegramConfigWarning = !telegramStatus?.is_authorized && (
    <Alert
      message="Telegram 未认证"
      description="请在 Telegram认证 标签页完成认证后再配置"
      type="warning"
      showIcon
      style={{ marginBottom: 16 }}
    />
  );

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
                label={configLabels[key] || key}
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

  return (
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
};

export default SystemConfigTab;