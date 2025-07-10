import React, { useState } from 'react';
import { 
  Drawer, 
  Form, 
  Input, 
  Select, 
  DatePicker, 
  Button, 
  Space, 
  Switch,
  InputNumber,
  Row,
  Col,
  message 
} from 'antd';
import { FilterOutlined, ClearOutlined } from '@ant-design/icons';
import { TelegramGroup } from '../../types';
import { MessageFilter } from '../../types/chat';

const { RangePicker } = DatePicker;
const { Option } = Select;

interface MessageFilterDrawerProps {
  visible: boolean;
  onClose: () => void;
  selectedGroup: TelegramGroup | null;
  currentFilter: MessageFilter;
  onApplyFilter: (filter: MessageFilter) => void;
  isMobile?: boolean;
}

const MessageFilterDrawer: React.FC<MessageFilterDrawerProps> = ({
  visible,
  onClose,
  selectedGroup,
  currentFilter,
  onApplyFilter,
  isMobile = false
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  // 应用筛选
  const handleApplyFilter = async (values: any) => {
    setLoading(true);
    try {
      const filter: MessageFilter = {};
      
      // 搜索关键词
      if (values.search) {
        filter.search = values.search.trim();
      }
      
      // 发送者过滤
      if (values.sender_username) {
        filter.sender_username = values.sender_username.trim();
      }
      
      // 媒体类型
      if (values.media_type) {
        filter.media_type = values.media_type;
      }
      
      // 是否包含媒体
      if (values.has_media !== undefined) {
        filter.has_media = values.has_media;
      }
      
      // 是否为转发消息
      if (values.is_forwarded !== undefined) {
        filter.is_forwarded = values.is_forwarded;
      }
      
      // 时间范围
      if (values.date_range && values.date_range.length === 2) {
        filter.date_range = [
          values.date_range[0].toISOString(),
          values.date_range[1].toISOString()
        ];
      }
      
      onApplyFilter(filter);
      message.success('筛选条件已应用');
      onClose();
    } catch (error) {
      message.error('应用筛选失败');
    } finally {
      setLoading(false);
    }
  };

  // 清除筛选
  const handleClearFilter = () => {
    form.resetFields();
    onApplyFilter({});
    message.success('筛选条件已清除');
    onClose();
  };

  // 初始化表单值
  React.useEffect(() => {
    if (visible) {
      const initialValues: any = {};
      
      if (currentFilter.search) {
        initialValues.search = currentFilter.search;
      }
      
      if (currentFilter.sender_username) {
        initialValues.sender_username = currentFilter.sender_username;
      }
      
      if (currentFilter.media_type) {
        initialValues.media_type = currentFilter.media_type;
      }
      
      if (currentFilter.has_media !== undefined) {
        initialValues.has_media = currentFilter.has_media;
      }
      
      if (currentFilter.is_forwarded !== undefined) {
        initialValues.is_forwarded = currentFilter.is_forwarded;
      }
      
      if (currentFilter.date_range && currentFilter.date_range.length === 2) {
        initialValues.date_range = [
          new Date(currentFilter.date_range[0]),
          new Date(currentFilter.date_range[1])
        ];
      }
      
      form.setFieldsValue(initialValues);
    }
  }, [visible, currentFilter, form]);

  return (
    <Drawer
      title={
        <Space>
          <FilterOutlined />
          消息筛选
        </Space>
      }
      placement="right"
      onClose={onClose}
      open={visible}
      width={isMobile ? '100%' : 400}
      footer={
        <div style={{ textAlign: 'right' }}>
          <Space>
            <Button 
              icon={<ClearOutlined />}
              onClick={handleClearFilter}
            >
              清除
            </Button>
            <Button 
              type="primary" 
              onClick={() => form.submit()}
              loading={loading}
              icon={<FilterOutlined />}
            >
              应用筛选
            </Button>
          </Space>
        </div>
      }
    >
      {!selectedGroup ? (
        <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
          请先选择一个群组
        </div>
      ) : (
        <Form
          form={form}
          layout="vertical"
          onFinish={handleApplyFilter}
        >
          <Form.Item
            name="search"
            label="搜索内容"
            tooltip="在消息文本中搜索关键词"
          >
            <Input 
              placeholder="输入搜索关键词..." 
              allowClear
            />
          </Form.Item>

          <Form.Item
            name="sender_username"
            label="发送者"
            tooltip="按发送者用户名筛选"
          >
            <Input 
              placeholder="输入发送者用户名..." 
              allowClear
              addonBefore="@"
            />
          </Form.Item>

          <Form.Item
            name="media_type"
            label="媒体类型"
            tooltip="按媒体类型筛选消息"
          >
            <Select 
              placeholder="选择媒体类型" 
              allowClear
            >
              <Option value="photo">图片</Option>
              <Option value="video">视频</Option>
              <Option value="document">文档</Option>
              <Option value="audio">音频</Option>
              <Option value="voice">语音</Option>
              <Option value="sticker">贴纸</Option>
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="has_media"
                label="包含媒体"
                tooltip="筛选是否包含媒体文件的消息"
              >
                <Select placeholder="选择" allowClear>
                  <Option value={true}>包含媒体</Option>
                  <Option value={false}>仅文本</Option>
                </Select>
              </Form.Item>
            </Col>
            
            <Col span={12}>
              <Form.Item
                name="is_forwarded"
                label="转发消息"
                tooltip="筛选转发或原创消息"
              >
                <Select placeholder="选择" allowClear>
                  <Option value={true}>转发消息</Option>
                  <Option value={false}>原创消息</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="date_range"
            label="时间范围"
            tooltip="按时间范围筛选消息"
          >
            <RangePicker 
              showTime 
              style={{ width: '100%' }}
              placeholder={['开始时间', '结束时间']}
            />
          </Form.Item>

          <div style={{ 
            background: '#f5f5f5', 
            padding: 12, 
            borderRadius: 6,
            marginTop: 16 
          }}>
            <div style={{ marginBottom: 8, fontWeight: 'bold', color: '#666' }}>
              当前群组: {selectedGroup.title}
            </div>
            <div style={{ fontSize: 12, color: '#999' }}>
              成员数: {selectedGroup.member_count?.toLocaleString() || 0}
            </div>
            <div style={{ fontSize: 12, color: '#999' }}>
              状态: {selectedGroup.is_active ? '活跃' : '暂停'}
            </div>
          </div>
        </Form>
      )}
    </Drawer>
  );
};

export default MessageFilterDrawer;