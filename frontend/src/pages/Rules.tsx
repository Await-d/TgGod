import React from 'react';
import { 
  Table, 
  Button, 
  Space, 
  Modal, 
  Form, 
  Input, 
  Select, 
  DatePicker, 
  InputNumber,
  Switch,
  Tag,
  message,
  Popconfirm,
  Typography,
  Card,
  Row,
  Col,
  Statistic
} from 'antd';
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined, 
  PlayCircleOutlined,
  PauseCircleOutlined,
  ExperimentOutlined,
  FilterOutlined
} from '@ant-design/icons';
import { FilterRule, TelegramGroup } from '../types';
import { useRuleStore, useTelegramStore, useGlobalStore } from '../store';
import { apiService } from '../services/api';

const { Title } = Typography;
const { RangePicker } = DatePicker;
const { TextArea } = Input;

const Rules: React.FC = () => {
  const { rules, setRules, addRule, updateRule, removeRule } = useRuleStore();
  const { groups, setGroups } = useTelegramStore();
  const { setLoading, setError } = useGlobalStore();
  const [isModalVisible, setIsModalVisible] = React.useState(false);
  const [editingRule, setEditingRule] = React.useState<FilterRule | null>(null);
  const [form] = Form.useForm();

  const loadData = React.useCallback(async () => {
    setLoading(true);
    try {
      // 加载群组数据
      const groupsResponse = await apiService.get<TelegramGroup[]>('/telegram/groups');
      if (groupsResponse.success && groupsResponse.data) {
        setGroups(groupsResponse.data);
      }

      // 加载规则数据
      const rulesResponse = await apiService.get<FilterRule[]>('/rule/rules');
      if (rulesResponse.success && rulesResponse.data) {
        setRules(rulesResponse.data);
      }
    } catch (error) {
      setError('加载数据失败');
      console.error('加载数据失败:', error);
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, setGroups, setRules]);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSubmit = async (values: any) => {
    try {
      // 处理关键词数据
      const processedValues = {
        ...values,
        keywords: values.keywords ? values.keywords.split('\n').filter((k: string) => k.trim()) : [],
        exclude_keywords: values.exclude_keywords ? values.exclude_keywords.split('\n').filter((k: string) => k.trim()) : [],
        sender_filter: values.sender_filter ? values.sender_filter.split('\n').filter((s: string) => s.trim()) : [],
        date_from: values.date_range?.[0]?.toISOString() || null,
        date_to: values.date_range?.[1]?.toISOString() || null,
      };

      delete processedValues.date_range;

      let response;
      if (editingRule) {
        response = await apiService.put<FilterRule>(`/rule/rules/${editingRule.id}`, processedValues);
        if (response.success && response.data) {
          updateRule(editingRule.id, response.data);
          message.success('规则更新成功');
        }
      } else {
        response = await apiService.post<FilterRule>('/rule/rules', processedValues);
        if (response.success && response.data) {
          addRule(response.data);
          message.success('规则创建成功');
        }
      }

      setIsModalVisible(false);
      form.resetFields();
      setEditingRule(null);
    } catch (error) {
      message.error(editingRule ? '更新规则失败' : '创建规则失败');
      console.error('提交规则失败:', error);
    }
  };

  const handleEdit = (rule: FilterRule) => {
    setEditingRule(rule);
    form.setFieldsValue({
      name: rule.name,
      group_id: rule.group_id,
      keywords: rule.keywords?.join('\n') || '',
      exclude_keywords: rule.exclude_keywords?.join('\n') || '',
      sender_filter: rule.sender_filter?.join('\n') || '',
      media_types: rule.media_types || [],
      date_range: rule.date_from && rule.date_to ? [
        new Date(rule.date_from),
        new Date(rule.date_to)
      ] : null,
      min_views: rule.min_views,
      max_views: rule.max_views,
      include_forwarded: rule.include_forwarded,
    });
    setIsModalVisible(true);
  };

  const handleDelete = async (ruleId: number) => {
    try {
      const response = await apiService.delete(`/rule/rules/${ruleId}`);
      if (response.success) {
        removeRule(ruleId);
        message.success('规则删除成功');
      }
    } catch (error) {
      message.error('删除规则失败');
      console.error('删除规则失败:', error);
    }
  };

  const handleToggleStatus = async (ruleId: number, currentStatus: boolean) => {
    try {
      const response = await apiService.put<FilterRule>(`/rule/rules/${ruleId}`, {
        is_active: !currentStatus
      });
      if (response.success && response.data) {
        updateRule(ruleId, { is_active: !currentStatus });
        message.success('状态更新成功');
      }
    } catch (error) {
      message.error('状态更新失败');
      console.error('状态更新失败:', error);
    }
  };

  const handleTestRule = async (ruleId: number) => {
    try {
      const response = await apiService.post(`/rule/rules/${ruleId}/test`);
      if (response.success) {
        message.success('规则测试完成');
      }
    } catch (error) {
      message.error('规则测试失败');
      console.error('规则测试失败:', error);
    }
  };

  const columns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: FilterRule) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {groups.find(g => g.id === record.group_id)?.title || '未知群组'}
          </div>
        </div>
      ),
    },
    {
      title: '关键词',
      dataIndex: 'keywords',
      key: 'keywords',
      render: (keywords: string[]) => (
        <div>
          {keywords?.slice(0, 3).map((keyword, index) => (
            <Tag key={index} color="blue" style={{ marginBottom: 2 }}>
              {keyword}
            </Tag>
          ))}
          {keywords && keywords.length > 3 && (
            <Tag color="default">+{keywords.length - 3}</Tag>
          )}
        </div>
      ),
    },
    {
      title: '媒体类型',
      dataIndex: 'media_types',
      key: 'media_types',
      render: (types: string[]) => (
        <div>
          {types?.map((type, index) => (
            <Tag key={index} color="green" style={{ marginBottom: 2 }}>
              {type}
            </Tag>
          ))}
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'red'}>
          {isActive ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: FilterRule) => (
        <Space size="middle">
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="text"
            size="small"
            icon={<ExperimentOutlined />}
            onClick={() => handleTestRule(record.id)}
          >
            测试
          </Button>
          <Button
            type="text"
            size="small"
            icon={record.is_active ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={() => handleToggleStatus(record.id, record.is_active)}
          >
            {record.is_active ? '禁用' : '启用'}
          </Button>
          <Popconfirm
            title="确定要删除这个规则吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={2}>规则配置</Title>
        <Button 
          type="primary" 
          icon={<PlusOutlined />} 
          onClick={() => setIsModalVisible(true)}
        >
          创建规则
        </Button>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="总规则数"
              value={rules.length}
              prefix={<FilterOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="启用规则"
              value={rules.filter(r => r.is_active).length}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="禁用规则"
              value={rules.filter(r => !r.is_active).length}
              prefix={<PauseCircleOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 规则表格 */}
      <Table
        columns={columns}
        dataSource={rules}
        rowKey="id"
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
        }}
      />

      {/* 创建/编辑规则模态框 */}
      <Modal
        title={editingRule ? '编辑规则' : '创建规则'}
        open={isModalVisible}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
          setEditingRule(null);
        }}
        footer={null}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="规则名称"
                name="name"
                rules={[{ required: true, message: '请输入规则名称' }]}
              >
                <Input placeholder="请输入规则名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="目标群组"
                name="group_id"
                rules={[{ required: true, message: '请选择目标群组' }]}
              >
                <Select placeholder="请选择群组">
                  {groups.map(group => (
                    <Select.Option key={group.id} value={group.id}>
                      {group.title}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="包含关键词"
                name="keywords"
                tooltip="每行一个关键词，支持正则表达式"
              >
                <TextArea 
                  rows={4} 
                  placeholder="请输入关键词，每行一个"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="排除关键词"
                name="exclude_keywords"
                tooltip="每行一个关键词，包含这些关键词的消息将被排除"
              >
                <TextArea 
                  rows={4} 
                  placeholder="请输入排除关键词，每行一个"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="发送者过滤"
                name="sender_filter"
                tooltip="每行一个用户名，只获取指定用户的消息"
              >
                <TextArea 
                  rows={3} 
                  placeholder="请输入用户名，每行一个"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="媒体类型"
                name="media_types"
              >
                <Select
                  mode="multiple"
                  placeholder="请选择媒体类型"
                  options={[
                    { label: '图片', value: 'photo' },
                    { label: '视频', value: 'video' },
                    { label: '文档', value: 'document' },
                    { label: '音频', value: 'audio' },
                    { label: '语音', value: 'voice' },
                    { label: '贴纸', value: 'sticker' },
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="时间范围"
                name="date_range"
              >
                <RangePicker 
                  showTime 
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="包含转发消息"
                name="include_forwarded"
                valuePropName="checked"
                initialValue={true}
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="最小浏览量"
                name="min_views"
              >
                <InputNumber 
                  style={{ width: '100%' }}
                  min={0}
                  placeholder="请输入最小浏览量"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="最大浏览量"
                name="max_views"
              >
                <InputNumber 
                  style={{ width: '100%' }}
                  min={0}
                  placeholder="请输入最大浏览量"
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setIsModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                {editingRule ? '更新' : '创建'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Rules;