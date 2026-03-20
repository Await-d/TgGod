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
  Statistic,
  Dropdown
} from 'antd';
import { useIsMobile } from '../hooks/useMobileGestures';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ExperimentOutlined,
  FilterOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { FilterRule } from '../types';
import { useRuleStore, useGlobalStore } from '../store';
import { ruleApi } from '../services/apiService';
import PageContainer from '../components/Layout/PageContainer';
import './Rules.css';

const { Text } = Typography;
const { RangePicker } = DatePicker;
const { TextArea } = Input;

const Rules: React.FC = () => {
  const isMobile = useIsMobile();
  const { rules, setRules, addRule, updateRule, removeRule } = useRuleStore();
  // 移除群组状态 - 规则不再直接关联群组
  const { setLoading, setError } = useGlobalStore();
  const [isModalVisible, setIsModalVisible] = React.useState(false);
  const [editingRule, setEditingRule] = React.useState<FilterRule | null>(null);
  const [form] = Form.useForm();

  const loadData = React.useCallback(async () => {
    setLoading(true);
    try {
      // 只加载规则数据 - 不再需要群组数据
      const rulesData = await ruleApi.getRules();
      setRules(rulesData);
    } catch (error) {
      setError('加载数据失败');
      console.error('加载数据失败:', error);
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, setRules]);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSubmit = async (values: Record<string, any>) => {
    try {
      // 处理关键词和文件大小数据
      const {
        date_range,
        min_file_size_mb,
        max_file_size_mb,
        ...otherValues
      } = values;

      const processedValues = {
        ...otherValues,
        keywords: values.keywords ? values.keywords.split('\n').filter((k: string) => k.trim()) : [],
        exclude_keywords: values.exclude_keywords ? values.exclude_keywords.split('\n').filter((k: string) => k.trim()) : [],
        sender_filter: values.sender_filter ? values.sender_filter.split('\n').filter((s: string) => s.trim()) : [],
        date_from: date_range?.[0]?.toISOString() || undefined,
        date_to: date_range?.[1]?.toISOString() || undefined,
        // 将MB转换为字节
        min_file_size: min_file_size_mb ? Math.round(min_file_size_mb * 1024 * 1024) : undefined,
        max_file_size: max_file_size_mb ? Math.round(max_file_size_mb * 1024 * 1024) : undefined,
      };

      if (editingRule) {
        const updatedRule = await ruleApi.updateRule(editingRule.id, processedValues);
        updateRule(editingRule.id, updatedRule);
        message.success('规则更新成功');
      } else {
        const newRule = await ruleApi.createRule(processedValues);
        addRule(newRule);
        message.success('规则创建成功');
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
      // 移除 group_id
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
      min_file_size_mb: rule.min_file_size ? (rule.min_file_size / 1024 / 1024) : undefined,
      max_file_size_mb: rule.max_file_size ? (rule.max_file_size / 1024 / 1024) : undefined,
      
      // 媒体时长
      min_duration: rule.min_duration,
      max_duration: rule.max_duration,
      
      // 视频尺寸
      min_width: rule.min_width,
      max_width: rule.max_width,
      min_height: rule.min_height,
      max_height: rule.max_height,
      
      // 文本长度
      min_text_length: rule.min_text_length,
      max_text_length: rule.max_text_length,
      
      // 高级选项
      has_urls: rule.has_urls,
      has_mentions: rule.has_mentions,
      has_hashtags: rule.has_hashtags,
      is_reply: rule.is_reply,
      is_edited: rule.is_edited,
      is_pinned: rule.is_pinned,
      
      // 时间过滤
      message_age_days: rule.message_age_days,
      exclude_weekends: rule.exclude_weekends,
      time_range_start: rule.time_range_start,
      time_range_end: rule.time_range_end,
      
      include_forwarded: rule.include_forwarded,
    });
    setIsModalVisible(true);
  };

  const handleDelete = async (ruleId: number) => {
    try {
      await ruleApi.deleteRule(ruleId);
      removeRule(ruleId);
      message.success('规则删除成功');
    } catch (error) {
      message.error('删除规则失败');
      console.error('删除规则失败:', error);
    }
  };

  const handleToggleStatus = async (ruleId: number, currentStatus: boolean) => {
    try {
      await ruleApi.updateRule(ruleId, {
        is_active: !currentStatus
      });
      updateRule(ruleId, { is_active: !currentStatus });
      message.success('状态更新成功');
    } catch (error) {
      message.error('状态更新失败');
      console.error('状态更新失败:', error);
    }
  };

  const handleTestRule = async (ruleId: number) => {
    try {
      const testResult = await ruleApi.testRule(ruleId);
      message.success(`规则测试完成，匹配消息数：${testResult.matched_messages}`);
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
            通用规则 - 由任务指定群组
          </div>
          {isMobile && (
            <div style={{ marginTop: 8 }}>
              <Tag color={record.is_active ? 'green' : 'red'}>
                {record.is_active ? '启用' : '禁用'}
              </Tag>
              <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>
                {new Date(record.created_at).toLocaleDateString()}
              </Text>
            </div>
          )}
        </div>
      ),
    },
    {
      title: isMobile ? '关键词/媒体类型' : '关键词',
      dataIndex: 'keywords',
      key: 'keywords',
      render: (keywords: string[], record: FilterRule) => (
        <div>
          <div style={{ marginBottom: isMobile ? 8 : 4 }}>
            {keywords?.slice(0, isMobile ? 2 : 3).map((keyword, index) => (
              <Tag key={index} color="blue" style={{ marginBottom: 2, fontSize: isMobile ? 11 : 12 }}>
                {keyword}
              </Tag>
            ))}
            {keywords && keywords.length > (isMobile ? 2 : 3) && (
              <Tag color="default" style={{ fontSize: isMobile ? 11 : 12 }}>
                +{keywords.length - (isMobile ? 2 : 3)}
              </Tag>
            )}
          </div>
          {isMobile && record.media_types && (
            <div>
              {record.media_types.slice(0, 2).map((type, index) => (
                <Tag key={index} color="green" style={{ marginBottom: 2, fontSize: 11 }}>
                  {type}
                </Tag>
              ))}
              {record.media_types.length > 2 && (
                <Tag color="default" style={{ fontSize: 11 }}>
                  +{record.media_types.length - 2}
                </Tag>
              )}
            </div>
          )}
        </div>
      ),
    },
    ...(!isMobile ? [{
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
    }] : []),
    ...(!isMobile ? [{
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'red'}>
          {isActive ? '启用' : '禁用'}
        </Tag>
      ),
    }] : []),
    ...(!isMobile ? [{
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
    }] : []),
    {
      title: '操作',
      key: 'actions',
      width: isMobile ? 80 : undefined,
      render: (_: unknown, record: FilterRule) => (
        <Space size="small">
          {isMobile ? (
            <Dropdown
              menu={{
                items: [
                  {
                    key: 'edit',
                    icon: <EditOutlined />,
                    label: '编辑',
                    onClick: () => handleEdit(record)
                  },
                  {
                    key: 'test',
                    icon: <ExperimentOutlined />,
                    label: '测试',
                    onClick: () => handleTestRule(record.id)
                  },
                  {
                    key: 'toggle',
                    icon: record.is_active ? <PauseCircleOutlined /> : <PlayCircleOutlined />,
                    label: record.is_active ? '禁用' : '启用',
                    onClick: () => handleToggleStatus(record.id, record.is_active)
                  },
                  {
                    key: 'delete',
                    icon: <DeleteOutlined />,
                    label: '删除',
                    danger: true,
                    onClick: () => {
                      Modal.confirm({
                        title: '确定要删除这个规则吗？',
                        content: '删除后无法恢复',
                        okText: '确定',
                        cancelText: '取消',
                        onOk: () => handleDelete(record.id),
                      });
                    }
                  }
                ]
              }}
              trigger={['click']}
            >
              <Button size="small" type="text">
                ···
              </Button>
            </Dropdown>
          ) : (
            <>
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
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer
      title="规则管理"
      description="配置下载过滤规则"
      breadcrumb={[{ title: '规则管理' }]}
      extra={
        <Space className="gap-sm">
          <Button
            icon={<ReloadOutlined />}
            onClick={loadData}
            title="刷新规则列表"
          >
            {!isMobile && '刷新'}
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setIsModalVisible(true)}
          >
            {isMobile ? '创建' : '创建规则'}
          </Button>
        </Space>
      }
    >
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} className="grid-responsive mb-lg">
        <Col xs={24} sm={8}>
          <Card className="stat-card stat-card--primary">
            <Statistic
              title="总规则数"
              value={rules.length}
              prefix={<FilterOutlined className="stat-card-icon" />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card className="stat-card stat-card--success">
            <Statistic
              title="启用规则"
              value={rules.filter(r => r.is_active).length}
              prefix={<PlayCircleOutlined className="stat-card-icon" />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card className="stat-card stat-card--error">
            <Statistic
              title="禁用规则"
              value={rules.filter(r => !r.is_active).length}
              prefix={<PauseCircleOutlined className="stat-card-icon" />}
            />
          </Card>
        </Col>
      </Row>

      {/* 规则表格 */}
      <div className="tg-table-container table-responsive">
        <Table
          columns={columns}
          dataSource={rules}
          rowKey="id"
          scroll={isMobile ? { x: 600 } : undefined}
          pagination={{
            pageSize: isMobile ? 5 : 10,
            showSizeChanger: !isMobile,
            showQuickJumper: !isMobile,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
            size: isMobile ? 'small' : 'default',
          }}
        />

      </div>

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
        width={isMobile ? '95%' : 800}
        className={isMobile ? 'modal-fullscreen-mobile' : 'modal-responsive'}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          className="tg-form form-responsive"
        >
          <Row gutter={16}>
            <Col span={24} className="form-item-full">
              <Form.Item
                label="规则名称"
                name="name"
                rules={[{ required: true, message: '请输入规则名称' }]}
              >
                <Input placeholder="请输入规则名称" />
              </Form.Item>
            </Col>
          </Row>

          <div className="rules-info-box">
            <Text type="secondary">
              💡 提示：规则不再直接绑定群组。创建任务时可以选择规则和群组的组合。
            </Text>
          </div>

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
                  className="rules-field-full"
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
                  className="rules-field-full"
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
                  className="rules-field-full"
                  min={0}
                  placeholder="请输入最大浏览量"
                />
              </Form.Item>
            </Col>
          </Row>

          {/* 文件大小过滤 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="最小文件大小（MB）"
                name="min_file_size_mb"
                tooltip="过滤小于此大小的文件"
              >
                <InputNumber 
                  className="rules-field-full"
                  min={0}
                  step={0.1}
                  precision={1}
                  placeholder="请输入最小文件大小"
                  addonAfter="MB"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="最大文件大小（MB）"
                name="max_file_size_mb"
                tooltip="过滤大于此大小的文件"
              >
                <InputNumber 
                  className="rules-field-full"
                  min={0}
                  step={0.1}
                  precision={1}
                  placeholder="请输入最大文件大小"
                  addonAfter="MB"
                />
              </Form.Item>
            </Col>
          </Row>

          {/* 媒体时长过滤 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="最小时长（秒）"
                name="min_duration"
                tooltip="视频或音频的最小时长"
              >
                <InputNumber 
                  className="rules-field-full"
                  min={0}
                  placeholder="请输入最小时长"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="最大时长（秒）"
                name="max_duration"
                tooltip="视频或音频的最大时长"
              >
                <InputNumber 
                  className="rules-field-full"
                  min={0}
                  placeholder="请输入最大时长"
                />
              </Form.Item>
            </Col>
          </Row>

          {/* 视频尺寸过滤 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="最小宽度（像素）"
                name="min_width"
                tooltip="视频或图片的最小宽度"
              >
                <InputNumber 
                  className="rules-field-full"
                  min={0}
                  placeholder="请输入最小宽度"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="最大宽度（像素）"
                name="max_width"
                tooltip="视频或图片的最大宽度"
              >
                <InputNumber 
                  className="rules-field-full"
                  min={0}
                  placeholder="请输入最大宽度"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="最小高度（像素）"
                name="min_height"
                tooltip="视频或图片的最小高度"
              >
                <InputNumber 
                  className="rules-field-full"
                  min={0}
                  placeholder="请输入最小高度"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="最大高度（像素）"
                name="max_height"
                tooltip="视频或图片的最大高度"
              >
                <InputNumber 
                  className="rules-field-full"
                  min={0}
                  placeholder="请输入最大高度"
                />
              </Form.Item>
            </Col>
          </Row>

          {/* 文本长度过滤 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="最小文本长度"
                name="min_text_length"
                tooltip="消息文本的最小字符数"
              >
                <InputNumber 
                  className="rules-field-full"
                  min={0}
                  placeholder="请输入最小文本长度"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="最大文本长度"
                name="max_text_length"
                tooltip="消息文本的最大字符数"
              >
                <InputNumber 
                  className="rules-field-full"
                  min={0}
                  placeholder="请输入最大文本长度"
                />
              </Form.Item>
            </Col>
          </Row>

          {/* 高级过滤选项 */}
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="包含链接"
                name="has_urls"
                valuePropName="checked"
                tooltip="只筛选包含URL链接的消息"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="包含@提及"
                name="has_mentions"
                valuePropName="checked"
                tooltip="只筛选包含@用户提及的消息"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="包含#话题"
                name="has_hashtags"
                valuePropName="checked"
                tooltip="只筛选包含#话题标签的消息"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="回复消息"
                name="is_reply"
                valuePropName="checked"
                tooltip="只筛选回复其他消息的消息"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="编辑过的消息"
                name="is_edited"
                valuePropName="checked"
                tooltip="只筛选被编辑过的消息"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="置顶消息"
                name="is_pinned"
                valuePropName="checked"
                tooltip="只筛选置顶的消息"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          {/* 时间相关过滤 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="消息年龄（天数内）"
                name="message_age_days"
                tooltip="只筛选指定天数内的消息"
              >
                <InputNumber 
                  className="rules-field-full"
                  min={1}
                  placeholder="请输入天数"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="排除周末消息"
                name="exclude_weekends"
                valuePropName="checked"
                tooltip="排除周六日发送的消息"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="时间范围开始"
                name="time_range_start"
                tooltip="每日时间范围开始（24小时制，如：09:00）"
              >
                <Input 
                  placeholder="请输入开始时间（HH:MM）"
                  pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="时间范围结束"
                name="time_range_end"
                tooltip="每日时间范围结束（24小时制，如：18:00）"
              >
                <Input 
                  placeholder="请输入结束时间（HH:MM）"
                  pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item className="form-actions form-actions--right">
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
    </PageContainer>
  );
};

export default Rules;
