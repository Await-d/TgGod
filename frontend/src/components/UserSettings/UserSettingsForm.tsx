import React, { useEffect } from 'react';
import {
  Form,
  Select,
  Switch,
  InputNumber,
  Card,
  Space,
  Button,
  Tooltip,
  Radio,
  Divider,
  message,
  Input
} from 'antd';
import {
  SaveOutlined,
  ReloadOutlined,
  SettingOutlined,
  BulbOutlined,
  GlobalOutlined,
  BellOutlined,
  DownloadOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  CodeOutlined
} from '@ant-design/icons';
import { useUserSettingsStore } from '../../store/userSettingsStore';
import { userSettingsService, UserSettings } from '../../services/userSettingsService';

const { Option } = Select;

const UserSettingsForm: React.FC = () => {
  const [form] = Form.useForm();
  const { settings, setSettings, isLoading, setIsLoading, resetSettings } = useUserSettingsStore();
  const [messageApi, contextHolder] = message.useMessage();

  // 初始化表单值
  useEffect(() => {
    form.setFieldsValue(settings);
  }, [form, settings]);

  // 加载用户设置
  useEffect(() => {
    const loadSettings = async () => {
      setIsLoading(true);
      try {
        const loadedSettings = await userSettingsService.getUserSettings();
        setSettings(loadedSettings);
      } catch (error) {
        console.error('加载用户设置失败:', error);
        messageApi.error('加载用户设置失败');
      } finally {
        setIsLoading(false);
      }
    };

    loadSettings();
  }, [setSettings, setIsLoading, messageApi]);

  // 保存设置
  const handleSave = async (values: UserSettings) => {
    setIsLoading(true);
    try {
      await userSettingsService.saveUserSettings(values);
      setSettings(values);
      messageApi.success('设置已保存');
    } catch (error) {
      console.error('保存设置失败:', error);
      messageApi.error('保存设置失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 重置设置
  const handleReset = async () => {
    setIsLoading(true);
    try {
      await userSettingsService.resetUserSettings();
      resetSettings();
      form.setFieldsValue(await userSettingsService.getUserSettings());
      messageApi.success('设置已重置为默认值');
    } catch (error) {
      console.error('重置设置失败:', error);
      messageApi.error('重置设置失败');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {contextHolder}
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSave}
        initialValues={settings}
        disabled={isLoading}
      >
        <Card
          title={<><SettingOutlined /> 基本设置</>}
          style={{ marginBottom: 16 }}
          size="small"
        >
          <Form.Item
            label="界面主题"
            name="theme"
            tooltip="选择界面显示的主题模式"
          >
            <Radio.Group>
              <Radio.Button value="light"><BulbOutlined /> 浅色</Radio.Button>
              <Radio.Button value="dark"><BulbOutlined /> 深色</Radio.Button>
              <Radio.Button value="system"><BulbOutlined /> 跟随系统</Radio.Button>
            </Radio.Group>
          </Form.Item>

          <Form.Item
            label="界面语言"
            name="language"
            tooltip="选择界面显示的语言"
          >
            <Select>
              <Option value="zh_CN"><GlobalOutlined /> 简体中文</Option>
              <Option value="en_US"><GlobalOutlined /> English</Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="显示密度"
            name="displayDensity"
            tooltip="调整界面元素的显示密度"
          >
            <Radio.Group>
              <Radio.Button value="comfortable">宽松</Radio.Button>
              <Radio.Button value="default">默认</Radio.Button>
              <Radio.Button value="compact">紧凑</Radio.Button>
            </Radio.Group>
          </Form.Item>

          <Form.Item
            label="时区设置"
            name="timezone"
            tooltip="设置您的时区，用于显示正确的时间"
          >
            <Select>
              <Option value="Asia/Shanghai"><ClockCircleOutlined /> 中国标准时间 (UTC+8)</Option>
              <Option value="UTC"><ClockCircleOutlined /> 世界协调时间 (UTC)</Option>
              <Option value="America/New_York"><ClockCircleOutlined /> 美国东部时间</Option>
              <Option value="Europe/London"><ClockCircleOutlined /> 英国时间</Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="日期格式"
            name="dateFormat"
            tooltip="设置日期和时间的显示格式"
          >
            <Radio.Group>
              <Radio.Button value="YYYY-MM-DD HH:mm">2023-01-01 13:30</Radio.Button>
              <Radio.Button value="MM/DD/YYYY hh:mm A">01/01/2023 01:30 PM</Radio.Button>
              <Radio.Button value="DD/MM/YYYY HH:mm">01/01/2023 13:30</Radio.Button>
            </Radio.Group>
          </Form.Item>
        </Card>

        <Card
          title={<><BellOutlined /> 通知设置</>}
          style={{ marginBottom: 16 }}
          size="small"
        >
          <Form.Item
            label="启用通知"
            name="notificationEnabled"
            valuePropName="checked"
            tooltip="开启后，将收到媒体下载完成等重要事件的通知"
          >
            <Switch />
          </Form.Item>
        </Card>

        <Card
          title={<><DownloadOutlined /> 下载设置</>}
          style={{ marginBottom: 16 }}
          size="small"
        >
          <Form.Item
            label="自动下载"
            name="autoDownload"
            valuePropName="checked"
            tooltip="开启后，会自动下载符合条件的媒体文件"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            label="自动下载大小限制 (MB)"
            name="autoDownloadMaxSize"
            tooltip="超过此大小的文件将不会自动下载"
            dependencies={['autoDownload']}
          >
            <InputNumber
              min={1}
              max={1000}
              disabled={!form.getFieldValue('autoDownload')}
            />
          </Form.Item>

          <Form.Item
            label="默认下载路径"
            name="defaultDownloadPath"
            tooltip="设置媒体文件的默认下载位置（相对路径）"
          >
            <Input placeholder="下载文件的默认保存位置" />
          </Form.Item>

          <Form.Item
            label="启用缩略图"
            name="thumbnailsEnabled"
            valuePropName="checked"
            tooltip="开启后，将显示媒体文件的缩略图预览"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            label="默认分页大小"
            name="defaultPageSize"
            tooltip="设置列表页面每页显示的项目数量"
          >
            <Select>
              <Option value={10}>10 条/页</Option>
              <Option value={20}>20 条/页</Option>
              <Option value={50}>50 条/页</Option>
              <Option value={100}>100 条/页</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            label="内联预览文件"
            name="previewFilesInline"
            valuePropName="checked"
            tooltip="开启后，将在消息列表中直接预览媒体文件"
          >
            <Switch />
          </Form.Item>
        </Card>

        <Card
          title={<><CodeOutlined /> 高级设置</>}
          size="small"
        >
          <Form.Item
            label="开发者模式"
            name="developerMode"
            valuePropName="checked"
            tooltip="开启后，将显示更多调试信息和高级功能"
          >
            <Switch />
          </Form.Item>
        </Card>

        <Divider />

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={isLoading}
            >
              保存设置
            </Button>
            <Tooltip title="重置为默认设置">
              <Button
                danger
                icon={<ReloadOutlined />}
                onClick={handleReset}
                disabled={isLoading}
              >
                重置
              </Button>
            </Tooltip>
          </Space>
        </div>
      </Form>
    </>
  );
};

export default UserSettingsForm;