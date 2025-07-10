import React, { useState } from 'react';
import { 
  Modal, 
  Form, 
  Input, 
  Select, 
  Switch, 
  Button, 
  Space, 
  Card,
  Typography,
  Row,
  Col,
  message,
  Divider,
  InputNumber 
} from 'antd';
import { PlusOutlined, MessageOutlined } from '@ant-design/icons';
import { TelegramGroup, TelegramMessage, FilterRule } from '../../types';
import { ruleApi } from '../../services/apiService';

const { Option } = Select;
const { Text, Paragraph } = Typography;

interface QuickRuleModalProps {
  visible: boolean;
  onClose: () => void;
  selectedGroup: TelegramGroup | null;
  baseMessage?: TelegramMessage | null;
  onSuccess?: (rule: FilterRule) => void;
  isMobile?: boolean;
}

const QuickRuleModal: React.FC<QuickRuleModalProps> = ({
  visible,
  onClose,
  selectedGroup,
  baseMessage,
  onSuccess,
  isMobile = false
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  // 创建规则
  const handleCreateRule = async (values: any) => {
    if (!selectedGroup) return;
    
    setLoading(true);
    try {
      const ruleData = {
        name: values.name,
        group_id: selectedGroup.id,
        keywords: values.keywords || [],
        exclude_keywords: values.exclude_keywords || [],
        sender_filter: values.sender_filter || [],
        media_types: values.media_types || [],
        min_views: values.min_views || undefined,
        max_views: values.max_views || undefined,
        include_forwarded: values.include_forwarded || false,
        is_active: values.is_active !== false, // 默认为true
      };
      
      const createdRule = await ruleApi.createRule(ruleData);
      message.success('规则创建成功！');
      
      onSuccess?.(createdRule);
      onClose();
      form.resetFields();
    } catch (error: any) {
      message.error('创建规则失败: ' + error.message);
      console.error('创建规则失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 取消创建
  const handleCancel = () => {
    onClose();
    form.resetFields();
  };

  // 当模态框打开且有基础消息时，预填充表单
  React.useEffect(() => {
    if (visible && baseMessage) {
      const ruleName = `基于消息 #${baseMessage.message_id} 的规则`;
      const keywords = baseMessage.text ? [baseMessage.text.substring(0, 50)] : [];
      const senderFilter = baseMessage.sender_username ? [baseMessage.sender_username] : [];
      const mediaTypes = baseMessage.media_type ? [baseMessage.media_type] : [];
      
      form.setFieldsValue({
        name: ruleName,
        keywords: keywords,
        sender_filter: senderFilter,
        media_types: mediaTypes,
        include_forwarded: baseMessage.is_forwarded || false,
        is_active: true,
      });
    } else if (visible && !baseMessage) {
      // 如果没有基础消息，设置默认值
      form.setFieldsValue({
        name: `${selectedGroup?.title || '群组'}下载规则`,
        is_active: true,
      });
    }
  }, [visible, baseMessage, selectedGroup, form]);

  return (
    <Modal
      title={
        <Space>
          <PlusOutlined />
          快捷创建下载规则
          {baseMessage && (
            <Text type="secondary">
              (基于消息 #{baseMessage.message_id})
            </Text>
          )}
        </Space>
      }
      open={visible}
      onCancel={handleCancel}
      footer={null}
      width={isMobile ? '100%' : 800}
      style={isMobile ? { top: 20 } : {}}
      destroyOnClose
    >
      {/* 基础消息预览 */}
      {baseMessage && (
        <Card 
          size="small" 
          style={{ marginBottom: 16, backgroundColor: '#f5f5f5' }}
          title={
            <Space>
              <MessageOutlined />
              <Text strong>参考消息</Text>
            </Space>
          }
        >
          <div style={{ marginBottom: 8 }}>
            <Text strong>发送者:</Text> {baseMessage.sender_name || baseMessage.sender_username || '未知'} 
            {baseMessage.sender_username && baseMessage.sender_name && (
              <Text type="secondary">(@{baseMessage.sender_username})</Text>
            )}
          </div>
          
          {baseMessage.text && (
            <div style={{ marginBottom: 8 }}>
              <Text strong>内容:</Text> 
              <Paragraph 
                style={{ margin: '4px 0', background: 'white', padding: 8, borderRadius: 4 }}
                ellipsis={{ rows: 3, expandable: true }}
              >
                {baseMessage.text}
              </Paragraph>
            </div>
          )}
          
          {baseMessage.media_type && (
            <div style={{ marginBottom: 8 }}>
              <Text strong>媒体类型:</Text> 
              <Text code style={{ marginLeft: 8 }}>{baseMessage.media_type}</Text>
            </div>
          )}
          
          <div>
            <Text strong>时间:</Text> {new Date(baseMessage.date).toLocaleString()}
          </div>
        </Card>
      )}

      <Form
        form={form}
        layout="vertical"
        onFinish={handleCreateRule}
      >
        <Form.Item
          name="name"
          label="规则名称"
          rules={[{ required: true, message: '请输入规则名称' }]}
        >
          <Input placeholder="请输入规则名称" maxLength={100} />
        </Form.Item>

        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item
              name="keywords"
              label="包含关键词"
              tooltip="消息必须包含这些关键词中的任意一个"
            >
              <Select
                mode="tags"
                placeholder="输入关键词，按回车添加"
                style={{ width: '100%' }}
                maxTagCount={10}
              />
            </Form.Item>
          </Col>
          
          <Col xs={24} sm={12}>
            <Form.Item
              name="exclude_keywords"
              label="排除关键词"
              tooltip="包含这些关键词的消息将被排除"
            >
              <Select
                mode="tags"
                placeholder="输入排除关键词，按回车添加"
                style={{ width: '100%' }}
                maxTagCount={10}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item
              name="sender_filter"
              label="发送者过滤"
              tooltip="只下载这些发送者的消息"
            >
              <Select
                mode="tags"
                placeholder="输入用户名，按回车添加"
                style={{ width: '100%' }}
                maxTagCount={10}
              />
            </Form.Item>
          </Col>
          
          <Col xs={24} sm={12}>
            <Form.Item
              name="media_types"
              label="媒体类型"
              tooltip="只下载这些媒体类型的消息"
            >
              <Select
                mode="multiple"
                placeholder="选择媒体类型"
                style={{ width: '100%' }}
              >
                <Option value="photo">图片</Option>
                <Option value="video">视频</Option>
                <Option value="document">文档</Option>
                <Option value="audio">音频</Option>
                <Option value="voice">语音</Option>
                <Option value="sticker">贴纸</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col xs={24} sm={8}>
            <Form.Item
              name="min_views"
              label="最小查看数"
              tooltip="只下载查看数大于等于此值的消息"
            >
              <InputNumber 
                placeholder="最小查看数"
                min={0}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
          
          <Col xs={24} sm={8}>
            <Form.Item
              name="max_views"
              label="最大查看数"
              tooltip="只下载查看数小于等于此值的消息"
            >
              <InputNumber 
                placeholder="最大查看数"
                min={0}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
          
          <Col xs={24} sm={8}>
            <Form.Item
              name="include_forwarded"
              label="包含转发消息"
              valuePropName="checked"
              tooltip="是否包含转发的消息"
            >
              <Switch />
            </Form.Item>
          </Col>
        </Row>

        <Divider />

        <Row gutter={16} align="middle">
          <Col xs={24} sm={12}>
            <Form.Item
              name="is_active"
              label="启用规则"
              valuePropName="checked"
              tooltip="创建后是否立即启用此规则"
            >
              <Switch defaultChecked />
            </Form.Item>
          </Col>
          
          {selectedGroup && (
            <Col xs={24} sm={12}>
              <div style={{ 
                background: '#f0f2f5', 
                padding: 12, 
                borderRadius: 6,
                fontSize: 12 
              }}>
                <div><Text strong>目标群组:</Text> {selectedGroup.title}</div>
                <div><Text type="secondary">成员: {selectedGroup.member_count?.toLocaleString() || 0}</Text></div>
              </div>
            </Col>
          )}
        </Row>

        <Form.Item style={{ marginBottom: 0, textAlign: 'right', marginTop: 24 }}>
          <Space>
            <Button onClick={handleCancel}>
              取消
            </Button>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              icon={<PlusOutlined />}
            >
              创建规则
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default QuickRuleModal;