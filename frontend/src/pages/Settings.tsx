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
  Spin
} from 'antd';
import { 
  SettingOutlined, 
  SaveOutlined,
  ReloadOutlined,
  ClearOutlined
} from '@ant-design/icons';
import { apiService } from '../services/api';
import { useGlobalStore } from '../store';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface ConfigItem {
  value: string;
  description: string;
  is_encrypted: boolean;
}

const Settings: React.FC = () => {
  const [form] = Form.useForm();
  const { connectionStatus } = useGlobalStore();
  const [loading, setLoading] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [configs, setConfigs] = React.useState<Record<string, ConfigItem>>({});

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

  React.useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

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

  const renderConfigSection = (title: string, configKeys: string[]) => (
    <Card 
      title={title} 
      size="small" 
      style={{ marginBottom: 16 }}
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

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <SettingOutlined style={{ marginRight: 8 }} />
          系统配置
        </Title>
        <Text type="secondary">
          配置系统运行所需的参数。修改配置后需要重启服务才能生效。
        </Text>
      </div>

      <Alert
        message="配置说明"
        description={
          <div>
            <p>• Telegram API ID 和 API Hash 需要从 https://my.telegram.org 获取</p>
            <p>• 敏感配置项（如密钥）会加密存储，显示为 *** 时表示已设置</p>
            <p>• 修改配置后建议重启服务以确保配置生效</p>
          </div>
        }
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      {connectionStatus === 'disconnected' && (
        <Alert
          message="连接状态"
          description="后端服务连接断开，请检查服务状态"
          type="warning"
          showIcon
          style={{ marginBottom: 24 }}
        />
      )}

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
    </div>
  );
};

export default Settings;