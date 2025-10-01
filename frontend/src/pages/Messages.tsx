import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Select,
  Input,
  DatePicker,
  message,
  Modal,
  Form,
  Tag,
  Typography,
  Tooltip,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Avatar,
  Divider,
  Switch,
  Drawer,
  Progress,
  Alert,
  Radio,
} from 'antd';
import {
  SendOutlined,
  DeleteOutlined,
  ReloadOutlined,
  EyeOutlined,
  MessageOutlined,
  UserOutlined,
  PushpinOutlined,
  ShareAltOutlined,
  FilterOutlined,
  SyncOutlined,
  PlusOutlined,
  ClearOutlined,
  ExclamationCircleOutlined,
  CloudSyncOutlined,
} from '@ant-design/icons';
import MediaPreview from '../components/Media/MediaPreview';
import InlineMediaPreview from '../components/Media/InlineMediaPreview';
import MediaButton from '../components/Media/MediaButton';
import { messageApi, telegramApi, ruleApi } from '../services/apiService';
import { TelegramMessage, TelegramGroup, MessageSendRequest } from '../types';
import { useNormalPageScrollControl } from '../hooks/usePageScrollControl';
import { webSocketService } from '../services/websocket';
import './Messages.css';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { RangePicker } = DatePicker;

const MessagesPage: React.FC = () => {
  // 恢复正常页面滚动
  useNormalPageScrollControl();

  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<TelegramMessage[]>([]);
  const [groups, setGroups] = useState<TelegramGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<TelegramGroup | null>(null);
  const [selectedMessage, setSelectedMessage] = useState<TelegramMessage | null>(null);
  const [sendModalVisible, setSendModalVisible] = useState(false);
  const [messageDetailVisible, setMessageDetailVisible] = useState(false);
  const [filterDrawerVisible, setFilterDrawerVisible] = useState(false);
  const [quickRuleModalVisible, setQuickRuleModalVisible] = useState(false);
  const [selectedMessageForRule, setSelectedMessageForRule] = useState<TelegramMessage | null>(null);
  const [form] = Form.useForm();
  const [searchForm] = Form.useForm();
  const [ruleForm] = Form.useForm();
  const [pagination, setPagination] = useState({ current: 1, pageSize: 50, total: 0 });
  const [filters, setFilters] = useState<any>({});
  const [stats, setStats] = useState<any>(null);
  const [replyTo, setReplyTo] = useState<TelegramMessage | null>(null);
  const [isMobile, setIsMobile] = useState(false);

  // 批量选择相关状态
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchDeleteLoading, setBatchDeleteLoading] = useState(false);

  // 清空群组消息相关状态
  const [clearGroupLoading, setClearGroupLoading] = useState(false);
  const [clearGroupProgress, setClearGroupProgress] = useState<{ current: number; total: number } | null>(null);

  // 批量同步相关状态
  const [batchSyncModalVisible, setBatchSyncModalVisible] = useState(false);
  const [syncMonths, setSyncMonths] = useState<{ year: number, month: number }[]>([]);
  const [syncMonthsLoading, setSyncMonthsLoading] = useState(false);
  const [syncAllGroupsLoading, setSyncAllGroupsLoading] = useState(false);
  const [syncForm] = Form.useForm();

  // 批量同步进度相关状态
  const [batchSyncProgress, setBatchSyncProgress] = useState<{
    synced_groups: number;
    total_groups: number;
    total_messages: number;
    failed_groups: any[];
    group_results: any[];
  } | null>(null);
  const [batchSyncStatus, setBatchSyncStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');


  // 检查是否为移动设备
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);

    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // 获取群组列表
  const fetchGroups = useCallback(async () => {
    try {
      // 使用getAllGroups获取所有群组，避免分页限制
      const response = await telegramApi.getAllGroups();
      setGroups(response);
      console.log(`成功获取 ${response.length} 个群组`);
      if (response.length > 0 && !selectedGroup) {
        setSelectedGroup(response[0]);
      }
    } catch (error: any) {
      message.error('获取群组列表失败: ' + error.message);
    }
  }, [selectedGroup]);

  // 获取群组消息
  const fetchMessages = useCallback(async (groupId: number, page: number = 1, searchParams: any = {}) => {
    if (!groupId) return;

    setLoading(true);
    try {
      const skip = (page - 1) * pagination.pageSize;
      const params = {
        skip,
        limit: pagination.pageSize,
        ...searchParams,
      };

      const response = await messageApi.getGroupMessagesPaginated(groupId, params);
      setMessages(response.data);

      setPagination(prev => ({
        ...prev,
        current: response.pagination.current,
        pageSize: response.pagination.pageSize,
        total: response.pagination.total
      }));
    } catch (error: any) {
      message.error('获取消息失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  }, [pagination.pageSize]);

  // 获取群组统计
  const fetchGroupStats = useCallback(async (groupId: number) => {
    try {
      const response = await telegramApi.getGroupStats(groupId);
      setStats(response);
    } catch (error: any) {
      console.error('获取群组统计失败:', error);
    }
  }, []);

  // 发送消息
  const handleSendMessage = async (values: { text: string }) => {
    if (!selectedGroup) return;

    try {
      const messageData: MessageSendRequest = {
        text: values.text,
        reply_to_message_id: replyTo?.message_id,
      };

      await messageApi.sendMessage(selectedGroup.id, messageData);
      message.success('消息发送成功！');

      // 刷新消息列表
      await fetchMessages(selectedGroup.id, 1, filters);

      // 重置表单和状态
      form.resetFields();
      setSendModalVisible(false);
      setReplyTo(null);

    } catch (error: any) {
      message.error('发送消息失败: ' + error.message);
    }
  };

  // 删除消息
  const handleDeleteMessage = async (messageId: number) => {
    if (!selectedGroup) return;

    try {
      await messageApi.deleteMessage(selectedGroup.id, messageId);
      message.success('消息删除成功！');

      // 刷新消息列表
      await fetchMessages(selectedGroup.id, pagination.current, filters);

      // 移除已删除的消息从选中列表
      setSelectedRowKeys(prevKeys => prevKeys.filter(key => key !== messageId));

    } catch (error: any) {
      message.error('删除消息失败: ' + error.message);
    }
  };

  // 批量删除消息
  const handleBatchDeleteMessages = async () => {
    if (!selectedGroup || selectedRowKeys.length === 0) return;

    setBatchDeleteLoading(true);

    try {
      let successCount = 0;
      let failCount = 0;

      // 批量删除：并发调用单个删除API
      const deletePromises = selectedRowKeys.map(async (messageId) => {
        try {
          await messageApi.deleteMessage(selectedGroup.id, Number(messageId));
          successCount++;
        } catch (error) {
          failCount++;
          console.error(`删除消息 ${messageId} 失败:`, error);
        }
      });

      await Promise.all(deletePromises);

      // 显示结果消息
      if (successCount > 0 && failCount === 0) {
        message.success(`成功删除 ${successCount} 条消息！`);
      } else if (successCount > 0 && failCount > 0) {
        message.warning(`成功删除 ${successCount} 条消息，${failCount} 条删除失败`);
      } else {
        message.error(`删除失败，${failCount} 条消息删除失败`);
      }

      // 清空选择
      setSelectedRowKeys([]);

      // 刷新消息列表
      await fetchMessages(selectedGroup.id, pagination.current, filters);

    } catch (error: any) {
      message.error('批量删除失败: ' + error.message);
    } finally {
      setBatchDeleteLoading(false);
    }
  };

  // 选择变化处理
  const handleRowSelectionChange = (
    selectedKeys: React.Key[]
  ) => {
    setSelectedRowKeys(selectedKeys);
  };

  // 全选/取消全选
  const handleSelectAll = () => {
    if (selectedRowKeys.length === messages.length) {
      // 当前全选状态，执行取消全选
      setSelectedRowKeys([]);
    } else {
      // 执行全选
      const allKeys = messages.map(msg => msg.message_id as React.Key);
      setSelectedRowKeys(allKeys);
    }
  };

  // 清空选择
  const handleClearSelection = () => {
    setSelectedRowKeys([]);
  };

  // 清空群组所有消息
  const handleClearGroupMessages = async () => {
    if (!selectedGroup) return;

    setClearGroupLoading(true);
    setClearGroupProgress(null);

    try {
      const result = await messageApi.clearGroupMessages(
        selectedGroup.id,
        (progress) => {
          setClearGroupProgress(progress);
        }
      );

      // 显示结果
      if (result.success && result.failedCount === 0) {
        message.success(result.message);
      } else if (result.success && result.failedCount > 0) {
        message.warning(result.message);
      } else {
        message.error(result.message);
      }

      // 清空选择状态
      setSelectedRowKeys([]);

      // 刷新消息列表
      await fetchMessages(selectedGroup.id, 1, filters);
      setPagination(prev => ({ ...prev, current: 1 }));

    } catch (error: any) {
      message.error('清空群组消息失败: ' + error.message);
    } finally {
      setClearGroupLoading(false);
      setClearGroupProgress(null);
    }
  };

  // 同步消息
  const handleSyncMessages = async () => {
    if (!selectedGroup) return;

    setLoading(true);
    try {
      await telegramApi.syncGroupMessages(selectedGroup.id, 100);
      message.success('消息同步成功！');

      // 刷新消息列表
      await fetchMessages(selectedGroup.id, 1, filters);
      await fetchGroupStats(selectedGroup.id);

    } catch (error: any) {
      message.error('同步消息失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // 搜索消息
  const handleSearch = async (values: any) => {
    const searchParams: any = {};

    if (values.search) searchParams.search = values.search;
    if (values.sender_username) searchParams.sender_username = values.sender_username;
    if (values.media_type) searchParams.media_type = values.media_type;
    if (values.has_media !== undefined) searchParams.has_media = values.has_media;
    if (values.is_forwarded !== undefined) searchParams.is_forwarded = values.is_forwarded;
    if (values.date_range) {
      searchParams.start_date = values.date_range[0].toISOString();
      searchParams.end_date = values.date_range[1].toISOString();
    }

    setFilters(searchParams);
    await fetchMessages(selectedGroup?.id || 0, 1, searchParams);
    setFilterDrawerVisible(false);
  };

  // 快捷创建规则
  const handleCreateQuickRule = (messageData: TelegramMessage) => {
    setSelectedMessageForRule(messageData);

    // 预填充表单数据
    const ruleName = `基于消息 #${messageData.message_id} 的规则`;
    const keywords = messageData.text ? [messageData.text.substring(0, 50)] : [];
    const senderFilter = messageData.sender_username ? [messageData.sender_username] : [];
    const mediaTypes = messageData.media_type ? [messageData.media_type] : [];

    ruleForm.setFieldsValue({
      name: ruleName,
      keywords: keywords,
      sender_filter: senderFilter,
      media_types: mediaTypes,
      include_forwarded: messageData.is_forwarded,
      is_active: true,
    });

    setQuickRuleModalVisible(true);
  };

  // 提交快捷规则
  const handleQuickRuleSubmit = async (values: any) => {
    if (!selectedGroup) return;

    try {
      const ruleData = {
        ...values,
        group_id: selectedGroup.id,
        keywords: values.keywords || [],
        exclude_keywords: values.exclude_keywords || [],
        sender_filter: values.sender_filter || [],
        media_types: values.media_types || [],
        // 文件大小转换为字节
        min_file_size: values.min_file_size ? Math.floor(values.min_file_size * 1024 * 1024) : undefined,
        max_file_size: values.max_file_size ? Math.floor(values.max_file_size * 1024 * 1024) : undefined,
      };

      await ruleApi.createRule(ruleData);
      message.success('规则创建成功！');

      // 重置表单和状态
      ruleForm.resetFields();
      setQuickRuleModalVisible(false);
      setSelectedMessageForRule(null);

    } catch (error: any) {
      message.error('创建规则失败: ' + error.message);
    }
  };

  // 清除搜索
  const clearSearch = () => {
    setFilters({});
    searchForm.resetFields();
    if (selectedGroup) {
      fetchMessages(selectedGroup.id, 1);
    }
  };


  // 表格列定义
  const columns = [
    {
      title: '消息ID',
      dataIndex: 'message_id',
      key: 'message_id',
      width: isMobile ? 80 : 100,
      render: (id: number) => <Text code>{id}</Text>,
    },
    {
      title: '发送者',
      key: 'sender',
      width: isMobile ? 120 : 150,
      render: (record: TelegramMessage) => (
        <Space>
          <Avatar size="small" icon={<UserOutlined />} />
          <div>
            <div style={{ fontSize: isMobile ? 12 : 14 }}>
              {record.sender_name || '未知'}
            </div>
            {record.sender_username && !isMobile && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                @{record.sender_username}
              </Text>
            )}
          </div>
        </Space>
      ),
    },
    {
      title: '消息内容',
      key: 'content',
      render: (record: TelegramMessage) => (
        <div style={{ maxWidth: isMobile ? 200 : 300 }}>
          <Space direction="vertical" size="small">
            {record.reply_to_message_id && (
              <Tag color="blue">
                回复 #{record.reply_to_message_id}
              </Tag>
            )}

            {record.text && (
              <Typography.Paragraph
                ellipsis={{
                  rows: isMobile ? 1 : 2,
                  expandable: !isMobile,
                  symbol: 'more'
                }}
                style={{
                  margin: 0,
                  fontSize: isMobile ? 12 : 14
                }}
              >
                {record.text}
              </Typography.Paragraph>
            )}

            {record.media_type && (
              <>
                {/* 直接在列表中显示媒体预览 */}
                {['photo', 'video'].includes(record.media_type) ? (
                  <InlineMediaPreview
                    message={record}
                    size={isMobile ? 'small' : 'default'}
                    lazyLoad={true}
                    onClick={() => {
                      setSelectedMessage(record);
                      setMessageDetailVisible(true);
                    }}
                  />
                ) : (
                  <MediaPreview
                    message={record}
                    size={isMobile ? 'small' : 'default'}
                    showPreview={true}
                    showDownload={true}
                  />
                )}
              </>
            )}

            {record.is_forwarded && (
              <Tag color="orange">
                <ShareAltOutlined /> {isMobile ? '转发' : '转发'}
              </Tag>
            )}

            {record.is_pinned && (
              <Tag color="red">
                <PushpinOutlined /> {isMobile ? '置顶' : '置顶'}
              </Tag>
            )}

            {record.reactions && Object.keys(record.reactions).length > 0 && !isMobile && (
              <Space size="small">
                {Object.entries(record.reactions).map(([emoji, count]) => (
                  <Tag key={emoji} color="pink">
                    {emoji} {count}
                  </Tag>
                ))}
              </Space>
            )}
          </Space>
        </div>
      ),
    },
    {
      title: '时间',
      dataIndex: 'date',
      key: 'date',
      width: isMobile ? 100 : 180,
      render: (date: string) => (
        <div>
          <div style={{ fontSize: isMobile ? 12 : 14 }}>
            {new Date(date).toLocaleDateString()}
          </div>
          {!isMobile && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {new Date(date).toLocaleTimeString()}
            </Text>
          )}
        </div>
      ),
    },
    ...(!isMobile ? [{
      title: '统计',
      key: 'stats',
      width: 120,
      render: (record: TelegramMessage) => (
        <Space direction="vertical" size="small">
          <div className="messages-view-meta">
            <EyeOutlined className="messages-stat-icon" />
            <Text className="messages-stat-value">{record.view_count || 0}</Text>
          </div>
          {record.mentions && record.mentions.length > 0 && (
            <Tag color="purple">
              @{record.mentions.length}
            </Tag>
          )}
          {record.hashtags && record.hashtags.length > 0 && (
            <Tag color="green">
              #{record.hashtags.length}
            </Tag>
          )}
        </Space>
      ),
    }] : []),
    {
      title: '操作',
      key: 'actions',
      width: isMobile ? 120 : 160,
      render: (record: TelegramMessage) => (
        <Space size="small" direction={isMobile ? 'vertical' : 'horizontal'}>
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              size={isMobile ? 'small' : 'middle'}
              onClick={() => {
                setSelectedMessage(record);
                setMessageDetailVisible(true);
              }}
            />
          </Tooltip>

          <Tooltip title="回复">
            <Button
              type="text"
              icon={<MessageOutlined />}
              size={isMobile ? 'small' : 'middle'}
              onClick={() => {
                setReplyTo(record);
                setSendModalVisible(true);
              }}
            />
          </Tooltip>

          <Tooltip title="创建规则">
            <Button
              type="text"
              icon={<PlusOutlined />}
              size={isMobile ? 'small' : 'middle'}
              onClick={() => handleCreateQuickRule(record)}
            />
          </Tooltip>

          {record.media_type && (
            <>
              <MediaButton
                message={record}
                action="preview"
                size={isMobile ? 'small' : 'middle'}
                onPreview={() => {
                  setSelectedMessage(record);
                  setMessageDetailVisible(true);
                }}
              />
              <MediaButton
                message={record}
                action="download"
                size={isMobile ? 'small' : 'middle'}
              />
            </>
          )}

          {!isMobile && (
            <Popconfirm
              title="确认删除这条消息吗？"
              onConfirm={() => handleDeleteMessage(record.message_id)}
            >
              <Tooltip title="删除">
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  size="small"
                />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  // 组件挂载时获取数据
  useEffect(() => {
    fetchGroups();
  }, [fetchGroups]);

  // 当选择群组时获取消息
  useEffect(() => {
    if (selectedGroup) {
      fetchMessages(selectedGroup.id, 1, filters);
      fetchGroupStats(selectedGroup.id);
    }
  }, [selectedGroup, filters, fetchMessages, fetchGroupStats]);

  // 获取默认同步月份
  const fetchDefaultSyncMonths = useCallback(async (count: number = 3) => {
    if (!selectedGroup) return;

    try {
      setSyncMonthsLoading(true);
      const response = await telegramApi.getDefaultSyncMonths(selectedGroup.id, count);
      setSyncMonths(response.months);

      // 设置表单默认值
      syncForm.setFieldsValue({
        months: response.months
      });
    } catch (error: any) {
      message.error(`获取默认同步月份失败: ${error.message}`);
    } finally {
      setSyncMonthsLoading(false);
    }
  }, [selectedGroup, syncForm]);

  // 批量同步所有群组
  const handleBatchSyncAllGroups = async (values: any) => {
    try {
      setSyncAllGroupsLoading(true);
      setBatchSyncStatus('running');
      setBatchSyncProgress(null);

      let monthsToSync: { year: number, month: number }[] = [];

      // 根据模式确定要同步的月份
      if (values.mode === 'recent') {
        // 获取最近N个月
        const count = values.recentMonths || 3;
        const currentDate = new Date();

        // 生成最近N个月的数据
        for (let i = 0; i < count; i++) {
          const targetDate = new Date(currentDate);
          targetDate.setMonth(currentDate.getMonth() - i);

          monthsToSync.push({
            year: targetDate.getFullYear(),
            month: targetDate.getMonth() + 1 // JavaScript月份从0开始
          });
        }
      } else {
        // 使用自定义选择的月份，需要解析JSON字符串
        monthsToSync = (values.months || []).map((monthStr: string) => JSON.parse(monthStr));
      }

      if (monthsToSync.length === 0) {
        message.error('请至少选择一个月份');
        setSyncAllGroupsLoading(false);
        setBatchSyncStatus('idle');
        return;
      }

      // 执行批量同步
      const response = await telegramApi.syncAllGroupsMonthly(monthsToSync);

      if (response.success) {
        message.success(`批量同步任务已启动，同步 ${response.total_groups} 个群组，${monthsToSync.length} 个月的数据`);
      } else {
        message.error('批量同步启动失败');
        setBatchSyncStatus('failed');
      }
    } catch (error: any) {
      message.error(`启动批量同步失败: ${error.message}`);
      setBatchSyncStatus('failed');
    } finally {
      setSyncAllGroupsLoading(false);
    }
  };

  // 当批量同步模态框打开时，获取默认月份
  useEffect(() => {
    if (batchSyncModalVisible) {
      fetchDefaultSyncMonths(3);
      setBatchSyncStatus('idle');
      setBatchSyncProgress(null);
    }
  }, [batchSyncModalVisible, fetchDefaultSyncMonths]);

  // WebSocket 消息处理
  useEffect(() => {
    // 批量同步完成的处理函数
    const handleBatchSyncComplete = (data: any) => {
      if (data) {
        // 更新同步进度和状态
        setBatchSyncProgress(data);
        setBatchSyncStatus(data.success ? 'completed' : 'failed');

        // 显示通知
        if (data.success) {
          message.success(`批量同步完成，成功同步 ${data.synced_groups}/${data.total_groups} 个群组，共 ${data.total_messages} 条消息`);
        } else {
          message.error(`批量同步失败: ${data.error || '未知错误'}`);
        }
      }
    };

    // 单群组同步完成的处理函数
    const handleMonthlySyncComplete = (data: any) => {
      if (data && selectedGroup && data.group_id === selectedGroup.id) {
        // 如果是当前选中的群组，刷新消息
        fetchMessages(selectedGroup.id, 1, filters);
        fetchGroupStats(selectedGroup.id);
        message.success(`群组 ${selectedGroup.title} 同步完成，共同步 ${data.total_messages} 条消息`);
      }
    };

    // 订阅WebSocket消息
    const batchSyncUnsubscribe = webSocketService.subscribe('batch_monthly_sync_complete', handleBatchSyncComplete);
    const monthlySyncUnsubscribe = webSocketService.subscribe('monthly_sync_complete', handleMonthlySyncComplete);

    // 清理函数
    return () => {
      batchSyncUnsubscribe();
      monthlySyncUnsubscribe();
    };
  }, [selectedGroup, filters, fetchMessages, fetchGroupStats]);

  return (
    <div className={isMobile ? 'messages-page mobile' : 'messages-page'}>
      <Row gutter={[16, 16]}>
        {/* 顶部统计卡片 */}
        {stats && (
          <Col span={24}>
            <Row gutter={16} className="messages-stat-grid">
              <Col xs={12} sm={6}>
                <Card>
                  <Statistic
                    title="总消息数"
                    value={stats.total_messages}
                    valueStyle={{ fontSize: isMobile ? 16 : 24 }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card>
                  <Statistic
                    title="媒体消息"
                    value={stats.media_messages}
                    valueStyle={{ fontSize: isMobile ? 16 : 24 }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card>
                  <Statistic
                    title="文字消息"
                    value={stats.text_messages}
                    valueStyle={{ fontSize: isMobile ? 16 : 24 }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card>
                  <Statistic
                    title="群组成员"
                    value={stats.member_count}
                    valueStyle={{ fontSize: isMobile ? 16 : 24 }}
                  />
                </Card>
              </Col>
            </Row>
          </Col>
        )}

        {/* 主要内容卡片 */}
        <Col span={24}>
          <Card
            title={
              <Space wrap>
                <Title level={isMobile ? 5 : 4} className="messages-card-title">
                  {isMobile ? '消息管理' : '群组消息管理'}
                </Title>
                {selectedGroup && (
                  <Tag color="blue">{selectedGroup.title}</Tag>
                )}
              </Space>
            }
            extra={
              <Space wrap size="small" className="messages-toolbar-actions">
                <Select
                  placeholder="选择群组"
                  value={selectedGroup?.id}
                  className={isMobile ? 'messages-group-select mobile' : 'messages-group-select'}
                  showSearch
                  optionFilterProp="children"
                  filterOption={(input, option) => 
                    (option?.children as unknown as string)?.toLowerCase().indexOf(input.toLowerCase()) >= 0
                  }
                  onChange={(value) => {
                    const group = groups.find(g => g.id === value);
                    setSelectedGroup(group || null);
                  }}
                >
                  {groups.map(group => (
                    <Option key={group.id} value={group.id}>
                      {group.title}
                    </Option>
                  ))}
                </Select>

                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={() => setSendModalVisible(true)}
                  disabled={!selectedGroup}
                  size={isMobile ? 'small' : 'middle'}
                >
                  {isMobile ? '发送' : '发送消息'}
                </Button>

                <Button
                  icon={<FilterOutlined />}
                  onClick={() => setFilterDrawerVisible(true)}
                  size={isMobile ? 'small' : 'middle'}
                >
                  筛选
                </Button>

                <Button
                  icon={<SyncOutlined />}
                  onClick={handleSyncMessages}
                  loading={loading}
                  disabled={!selectedGroup}
                  size={isMobile ? 'small' : 'middle'}
                >
                  {isMobile ? '同步' : '同步消息'}
                </Button>

                <Button
                  icon={<CloudSyncOutlined />}
                  onClick={() => setBatchSyncModalVisible(true)}
                  loading={syncAllGroupsLoading}
                  size={isMobile ? 'small' : 'middle'}
                >
                  {isMobile ? '批量同步' : '批量同步'}
                </Button>

                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => selectedGroup && fetchMessages(selectedGroup.id, 1, filters)}
                  loading={loading}
                  size={isMobile ? 'small' : 'middle'}
                >
                  刷新
                </Button>

                {/* 清空群组消息按钮 */}
                <Popconfirm
                  title="清空群组所有消息"
                  description={
                    <div>
                      <p>⚠️ 此操作将删除该群组的所有消息</p>
                      <p>• 包括文本、图片、视频等所有类型消息</p>
                      <p>• 此操作不可撤销，请谨慎操作</p>
                      {selectedGroup && (
                        <p><strong>群组：{selectedGroup.title}</strong></p>
                      )}
                    </div>
                  }
                  onConfirm={handleClearGroupMessages}
                  okText="确认清空"
                  cancelText="取消"
                  okButtonProps={{
                    danger: true,
                    loading: clearGroupLoading
                  }}
                  icon={<ExclamationCircleOutlined className="messages-clear-icon" />}
                >
                  <Button
                    danger
                    icon={<ClearOutlined />}
                    disabled={!selectedGroup || clearGroupLoading}
                    loading={clearGroupLoading}
                    size={isMobile ? 'small' : 'middle'}
                  >
                    {clearGroupLoading ? '清空中...' : (isMobile ? '清空' : '清空群组')}
                  </Button>
                </Popconfirm>
              </Space>
            }
          >
            {/* 批量操作工具栏 */}
            {selectedRowKeys.length > 0 && (
              <div className="messages-selection-bar">
                <Row align="middle" justify="space-between">
                  <Col>
                    <Space className="messages-selection-meta">
                      <span className="messages-selection-count">已选择 {selectedRowKeys.length} 条消息</span>
                      <Button
                        size="small"
                        type="link"
                        className="messages-selection-link"
                        onClick={handleSelectAll}
                      >
                        {selectedRowKeys.length === messages.length ? '取消全选' : '全选当前页'}
                      </Button>
                      <Button
                        size="small"
                        type="link"
                        className="messages-selection-link"
                        onClick={handleClearSelection}
                      >
                        清空选择
                      </Button>
                    </Space>
                  </Col>
                  <Col>
                    <Space>
                      <Popconfirm
                        title="确认删除所选消息吗？"
                        description={`将删除 ${selectedRowKeys.length} 条消息，此操作不可撤销`}
                        onConfirm={handleBatchDeleteMessages}
                        okText="确认删除"
                        cancelText="取消"
                        okButtonProps={{ danger: true }}
                      >
                        <Button
                          type="primary"
                          danger
                          icon={<DeleteOutlined />}
                          loading={batchDeleteLoading}
                          size={isMobile ? 'small' : 'middle'}
                        >
                          批量删除
                        </Button>
                      </Popconfirm>
                    </Space>
                  </Col>
                </Row>
              </div>
            )}

            <Table
              columns={columns}
              dataSource={messages}
              rowKey="message_id"
              loading={loading}
              rowSelection={{
                selectedRowKeys,
                onChange: handleRowSelectionChange,
                onSelectAll: (selected, selectedRows, changeRows) => {
                  if (selected) {
                    // 选中当前页所有行
                    const allKeys = messages.map(msg => msg.message_id as React.Key);
                    const newSelectedKeys = [...selectedRowKeys];
                    allKeys.forEach(key => {
                      if (!newSelectedKeys.includes(key)) {
                        newSelectedKeys.push(key);
                      }
                    });
                    setSelectedRowKeys(newSelectedKeys);
                  } else {
                    // 取消选中当前页所有行
                    const currentPageKeys = messages.map(msg => msg.message_id as React.Key);
                    setSelectedRowKeys(selectedRowKeys.filter(key => !currentPageKeys.includes(key)));
                  }
                },
                getCheckboxProps: (record: TelegramMessage) => ({
                  name: record.message_id.toString(),
                }),
              }}
              pagination={{
                current: pagination.current,
                pageSize: pagination.pageSize,
                total: pagination.total,
                showSizeChanger: !isMobile,
                showQuickJumper: !isMobile,
                showTotal: (total, range) =>
                  isMobile ?
                    `${range[0]}-${range[1]} / ${total}` :
                    `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
                onChange: (page, pageSize) => {
                  setPagination(prev => ({ ...prev, current: page, pageSize: pageSize || 50 }));
                  selectedGroup && fetchMessages(selectedGroup.id, page, filters);
                },
                size: isMobile ? 'small' : 'default',
              }}
              scroll={{ x: isMobile ? 600 : 1200 }}
              size={isMobile ? 'small' : undefined}
            />
          </Card>
        </Col>
      </Row>

      {/* 发送消息模态框 */}
      <Modal
        title={
          <Space>
            <SendOutlined />
            发送消息
            {replyTo && (
              <Tag color="blue">回复 #{replyTo.message_id}</Tag>
            )}
          </Space>
        }
        open={sendModalVisible}
        onCancel={() => {
          setSendModalVisible(false);
          setReplyTo(null);
          form.resetFields();
        }}
        footer={null}
        width={isMobile ? '100%' : 600}
        style={isMobile ? { top: 20 } : {}}
      >
        {replyTo && (
          <Card size="small" className="messages-reply-card">
            <Text strong>回复消息:</Text>
            <Typography.Paragraph className="messages-reply-text">
              {replyTo.text || '(媒体消息)'}
            </Typography.Paragraph>
          </Card>
        )}

        <Form
          form={form}
          onFinish={handleSendMessage}
          layout="vertical"
        >
          <Form.Item
            name="text"
            label="消息内容"
            rules={[{ required: true, message: '请输入消息内容' }]}
          >
            <TextArea
              rows={4}
              placeholder="请输入要发送的消息..."
              showCount
              maxLength={4000}
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                发送
              </Button>
              <Button onClick={() => {
                setSendModalVisible(false);
                setReplyTo(null);
                form.resetFields();
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 筛选抽屉 */}
      <Drawer
        title="消息筛选"
        placement="right"
        onClose={() => setFilterDrawerVisible(false)}
        open={filterDrawerVisible}
        width={isMobile ? '100%' : 400}
      >
        <Form
          form={searchForm}
          onFinish={handleSearch}
          layout="vertical"
        >
          <Form.Item name="search" label="搜索内容">
            <Input placeholder="搜索消息文本..." />
          </Form.Item>

          <Form.Item name="sender_username" label="发送者">
            <Input placeholder="输入发送者用户名..." />
          </Form.Item>

          <Form.Item name="media_type" label="媒体类型">
            <Select placeholder="选择媒体类型" allowClear>
              <Option value="photo">图片</Option>
              <Option value="video">视频</Option>
              <Option value="document">文档</Option>
              <Option value="audio">音频</Option>
            </Select>
          </Form.Item>

          <Form.Item name="has_media" label="包含媒体">
            <Select placeholder="选择是否包含媒体" allowClear>
              <Option value={true}>包含媒体</Option>
              <Option value={false}>不包含媒体</Option>
            </Select>
          </Form.Item>

          <Form.Item name="is_forwarded" label="转发消息">
            <Select placeholder="选择是否为转发消息" allowClear>
              <Option value={true}>转发消息</Option>
              <Option value={false}>原创消息</Option>
            </Select>
          </Form.Item>

          <Form.Item name="date_range" label="时间范围">
            <RangePicker showTime className="messages-field-full" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                搜索
              </Button>
              <Button onClick={clearSearch}>
                清除
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Drawer>

      {/* 消息详情模态框 */}
      <Modal
        title="消息详情"
        open={messageDetailVisible}
        onCancel={() => setMessageDetailVisible(false)}
        footer={null}
        width={isMobile ? '100%' : 800}
        style={isMobile ? { top: 20 } : {}}
      >
        {selectedMessage && (
          <div>
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Card size="small" title="基本信息">
                  <p><strong>消息ID:</strong> {selectedMessage.message_id}</p>
                  <p><strong>发送者:</strong> {selectedMessage.sender_name || '未知'}</p>
                  <p><strong>用户名:</strong> @{selectedMessage.sender_username || '无'}</p>
                  <p><strong>时间:</strong> {new Date(selectedMessage.date).toLocaleString()}</p>
                  <p><strong>查看次数:</strong> {selectedMessage.view_count || 0}</p>
                </Card>
              </Col>

              <Col xs={24} md={12}>
                <Card size="small" title="消息状态">
                  <Space direction="vertical">
                    <div>
                      <strong>转发:</strong>
                      <Tag color={selectedMessage.is_forwarded ? 'orange' : 'green'}>
                        {selectedMessage.is_forwarded ? '是' : '否'}
                      </Tag>
                    </div>
                    <div>
                      <strong>置顶:</strong>
                      <Tag color={selectedMessage.is_pinned ? 'red' : 'default'}>
                        {selectedMessage.is_pinned ? '是' : '否'}
                      </Tag>
                    </div>
                    {selectedMessage.edit_date && (
                      <div>
                        <strong>编辑时间:</strong> {new Date(selectedMessage.edit_date).toLocaleString()}
                      </div>
                    )}
                  </Space>
                </Card>
              </Col>
            </Row>

            <Divider />

            <Card size="small" title="消息内容">
              {selectedMessage.text && (
                <Typography.Paragraph>{selectedMessage.text}</Typography.Paragraph>
              )}

              {selectedMessage.media_type && (
                <>
                  {/* 详情弹窗中的媒体预览 */}
                  {['photo', 'video'].includes(selectedMessage.media_type) ? (
                    <InlineMediaPreview
                      message={selectedMessage}
                      size="large"
                      lazyLoad={false}
                    />
                  ) : (
                    <MediaPreview
                      message={selectedMessage}
                      size="large"
                      showPreview={true}
                      showDownload={true}
                    />
                  )}
                </>
              )}
            </Card>

            {selectedMessage.reactions && Object.keys(selectedMessage.reactions).length > 0 && (
              <Card size="small" title="消息反应" style={{ marginTop: 16 }}>
                <Space>
                  {Object.entries(selectedMessage.reactions).map(([emoji, count]) => (
                    <Tag key={emoji} color="pink">
                      {emoji} {count}
                    </Tag>
                  ))}
                </Space>
              </Card>
            )}

            {((selectedMessage.mentions && selectedMessage.mentions.length > 0) ||
              (selectedMessage.hashtags && selectedMessage.hashtags.length > 0) ||
              (selectedMessage.urls && selectedMessage.urls.length > 0)) && (
                <Card size="small" title="提及和标签" style={{ marginTop: 16 }}>
                  <Space direction="vertical">
                    {selectedMessage.mentions && selectedMessage.mentions.length > 0 && (
                      <div>
                        <strong>提及:</strong>
                        <Space>
                          {selectedMessage.mentions.map(mention => (
                            <Tag key={mention} color="purple">@{mention}</Tag>
                          ))}
                        </Space>
                      </div>
                    )}

                    {selectedMessage.hashtags && selectedMessage.hashtags.length > 0 && (
                      <div>
                        <strong>标签:</strong>
                        <Space>
                          {selectedMessage.hashtags.map(hashtag => (
                            <Tag key={hashtag} color="green">#{hashtag}</Tag>
                          ))}
                        </Space>
                      </div>
                    )}

                    {selectedMessage.urls && selectedMessage.urls.length > 0 && (
                      <div>
                        <strong>链接:</strong>
                        <Space direction="vertical">
                          {selectedMessage.urls.map(url => (
                            <a key={url} href={url} target="_blank" rel="noopener noreferrer">
                              {url}
                            </a>
                          ))}
                        </Space>
                      </div>
                    )}
                  </Space>
                </Card>
              )}
          </div>
        )}
      </Modal>

      {/* 快捷创建规则模态框 */}
      <Modal
        title={
          <Space>
            <PlusOutlined />
            快捷创建下载规则
            {selectedMessageForRule && (
              <Tag color="blue">基于消息 #{selectedMessageForRule.message_id}</Tag>
            )}
          </Space>
        }
        open={quickRuleModalVisible}
        onCancel={() => {
          setQuickRuleModalVisible(false);
          setSelectedMessageForRule(null);
          ruleForm.resetFields();
        }}
        footer={null}
        width={isMobile ? '100%' : 800}
        style={isMobile ? { top: 20 } : {}}
      >
        {selectedMessageForRule && (
          <>
            <Card size="small" className="messages-reference-card">
              <Text strong>参考消息:</Text>
              <div className="messages-reference-content">
                <Space direction="vertical" size="small">
                  <div>
                    <Text strong>发送者:</Text> {selectedMessageForRule.sender_name}
                    {selectedMessageForRule.sender_username && (
                      <Text type="secondary">(@{selectedMessageForRule.sender_username})</Text>
                    )}
                  </div>
                  {selectedMessageForRule.text && (
                    <div>
                      <Text strong>内容:</Text>
                      <Typography.Paragraph className="messages-reference-text">
                        {selectedMessageForRule.text}
                      </Typography.Paragraph>
                    </div>
                  )}
                  {selectedMessageForRule.media_type && (
                    <div>
                      <Text strong>媒体类型:</Text> {selectedMessageForRule.media_type}
                    </div>
                  )}
                  <div>
                    <Text strong>时间:</Text> {new Date(selectedMessageForRule.date).toLocaleString()}
                  </div>
                </Space>
              </div>
            </Card>

            <Form
              form={ruleForm}
              onFinish={handleQuickRuleSubmit}
              layout="vertical"
            >
              <Form.Item
                name="name"
                label="规则名称"
                rules={[{ required: true, message: '请输入规则名称' }]}
              >
                <Input placeholder="请输入规则名称" />
              </Form.Item>

              <Row gutter={16}>
                <Col xs={24} sm={12}>
                  <Form.Item
                    name="keywords"
                    label="关键词"
                    tooltip="包含这些关键词的消息将被匹配"
                  >
                    <Select
                      mode="tags"
                      placeholder="输入关键词，按回车添加"
                      className="messages-field-full"
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
                      className="messages-field-full"
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} sm={12}>
                  <Form.Item
                    name="sender_filter"
                    label="发送者过滤"
                    tooltip="只匹配这些发送者的消息"
                  >
                    <Select
                      mode="tags"
                      placeholder="输入用户名，按回车添加"
                      className="messages-field-full"
                    />
                  </Form.Item>
                </Col>

                <Col xs={24} sm={12}>
                  <Form.Item
                    name="media_types"
                    label="媒体类型"
                    tooltip="只匹配这些媒体类型的消息"
                  >
                    <Select
                      mode="multiple"
                      placeholder="选择媒体类型"
                      className="messages-field-full"
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
                  >
                    <Input
                      type="number"
                      placeholder="最小查看数"
                      min={0}
                    />
                  </Form.Item>
                </Col>

                <Col xs={24} sm={8}>
                  <Form.Item
                    name="max_views"
                    label="最大查看数"
                  >
                    <Input
                      type="number"
                      placeholder="最大查看数"
                      min={0}
                    />
                  </Form.Item>
                </Col>

                <Col xs={24} sm={8}>
                  <Form.Item
                    name="include_forwarded"
                    label="包含转发消息"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} sm={12}>
                  <Form.Item
                    name="min_file_size"
                    label="最小文件大小 (MB)"
                    tooltip="设置媒体文件的最小大小限制"
                  >
                    <Input
                      type="number"
                      placeholder="最小文件大小"
                      min={0}
                      step={0.1}
                      addonAfter="MB"
                    />
                  </Form.Item>
                </Col>

                <Col xs={24} sm={12}>
                  <Form.Item
                    name="max_file_size"
                    label="最大文件大小 (MB)"
                    tooltip="设置媒体文件的最大大小限制"
                  >
                    <Input
                      type="number"
                      placeholder="最大文件大小"
                      min={0}
                      step={0.1}
                      addonAfter="MB"
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name="is_active"
                label="启用规则"
                valuePropName="checked"
                initialValue={true}
              >
                <Switch />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit">
                    创建规则
                  </Button>
                  <Button onClick={() => {
                    setQuickRuleModalVisible(false);
                    setSelectedMessageForRule(null);
                    ruleForm.resetFields();
                  }}>
                    取消
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </>
        )}
      </Modal>

      {/* 清空群组消息进度模态框 */}
      <Modal
        title="清空群组消息"
        open={clearGroupLoading}
        closable={false}
        maskClosable={false}
        footer={null}
        centered
      >
        <div className="messages-progress-panel">
          <div>
            <ClearOutlined className="messages-progress-icon-large" />
            <p className="messages-progress-text">正在清空群组消息...</p>
            {selectedGroup && (
              <p className="messages-clear-caption">群组：{selectedGroup.title}</p>
            )}
          </div>

          {clearGroupProgress && (
            <div className="messages-progress-details">
              <Progress
                percent={Math.round((clearGroupProgress.current / clearGroupProgress.total) * 100)}
                status="active"
                className="messages-progress-bar"
              />
              <p className="messages-progress-info">
                已处理 {clearGroupProgress.current} / {clearGroupProgress.total} 条消息
              </p>
            </div>
          )}

          <div className="messages-progress-alert">
            <p>⚠️ 正在执行删除操作，请勿关闭页面</p>
          </div>
        </div>
      </Modal>

      {/* 批量同步模态框 */}
      <Modal
        title={
          <Space>
            <CloudSyncOutlined />
            批量同步消息
          </Space>
        }
        open={batchSyncModalVisible}
        onCancel={() => {
          if (!syncAllGroupsLoading) {
            setBatchSyncModalVisible(false);
          }
        }}
        footer={null}
        width={isMobile ? '100%' : 600}
        style={isMobile ? { top: 20 } : {}}
        maskClosable={!syncAllGroupsLoading}
      >
        <Form
          form={syncForm}
          onFinish={handleBatchSyncAllGroups}
          layout="vertical"
          initialValues={{
            mode: 'recent',
            recentMonths: 3
          }}
        >
          <Alert
            message="批量同步功能"
            description={
              <div>
                <p>此功能将按照选择的月份对所有活跃群组进行消息同步</p>
                <p>• 同步任务将在后台运行，不会阻塞界面</p>
                <p>• 同步进度和结果将通过WebSocket推送</p>
                <p>• 请注意：同步大量数据可能需要较长时间</p>
              </div>
            }
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Form.Item name="mode" label="选择模式">
            <Radio.Group>
              <Radio value="recent">最近几个月</Radio>
              <Radio value="custom">自定义月份</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) => prevValues.mode !== currentValues.mode}
          >
            {({ getFieldValue }) => {
              const mode = getFieldValue('mode');

              return mode === 'recent' ? (
                <Form.Item
                  name="recentMonths"
                  label="最近月份数量"
                  rules={[{ required: true, message: '请选择同步最近几个月' }]}
                >
                  <Select placeholder="选择同步最近几个月">
                    {[1, 2, 3, 6, 12].map(num => (
                      <Option key={num} value={num}>最近 {num} 个月</Option>
                    ))}
                  </Select>
                </Form.Item>
              ) : (
                <Form.Item
                  name="months"
                  label="选择要同步的月份"
                  rules={[{ required: true, message: '请选择至少一个月份' }]}
                >
                  <Select
                    mode="multiple"
                    placeholder="选择要同步的月份"
                    loading={syncMonthsLoading}
                    className="messages-field-full"
                  >
                    {syncMonths.map((month) => (
                      <Option
                        key={`${month.year}-${month.month}`}
                        value={JSON.stringify(month)}
                      >
                        {month.year}年{month.month}月
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              );
            }}
          </Form.Item>

          {/* 同步进度显示区域 */}
          {batchSyncStatus !== 'idle' && (
            <div className="messages-progress-section">
              <Divider orientation="left">同步进度</Divider>

              {batchSyncStatus === 'running' && !batchSyncProgress && (
                <div className="messages-progress-loading">
                  <div className="messages-progress-loading-box">
                    <SyncOutlined spin className="messages-progress-icon" />
                    <p>同步任务正在运行中，请稍候...</p>
                  </div>
                </div>
              )}

              {batchSyncProgress && (
                <div>
                  <Row gutter={[16, 16]}>
                    <Col span={24}>
                      <Progress
                        percent={Math.round((batchSyncProgress.synced_groups / Math.max(1, batchSyncProgress.total_groups)) * 100)}
                        status={batchSyncStatus === 'completed' ? 'success' : batchSyncStatus === 'failed' ? 'exception' : 'active'}
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic
                        title="已同步群组"
                        value={batchSyncProgress.synced_groups}
                        suffix={`/ ${batchSyncProgress.total_groups}`}
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic
                        title="已同步消息"
                        value={batchSyncProgress.total_messages}
                      />
                    </Col>
                  </Row>

                  {batchSyncProgress.failed_groups.length > 0 && (
                    <div style={{ marginTop: 16 }}>
                      <Alert
                        message={`${batchSyncProgress.failed_groups.length} 个群组同步失败`}
                        type="warning"
                        showIcon
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                loading={syncAllGroupsLoading}
                icon={<CloudSyncOutlined />}
                disabled={batchSyncStatus === 'running'}
              >
                开始批量同步
              </Button>
              <Button
                onClick={() => {
                  if (batchSyncStatus !== 'running') {
                    setBatchSyncModalVisible(false);
                  }
                }}
                disabled={batchSyncStatus === 'running'}
              >
                {batchSyncStatus === 'completed' || batchSyncStatus === 'failed' ? '关闭' : '取消'}
              </Button>
              <Form.Item
                noStyle
                shouldUpdate={(prevValues, currentValues) => prevValues.mode !== currentValues.mode}
              >
                {({ getFieldValue }) => {
                  const mode = getFieldValue('mode');

                  return mode === 'custom' ? (
                    <Button
                      onClick={() => fetchDefaultSyncMonths(6)}
                      loading={syncMonthsLoading}
                      disabled={batchSyncStatus === 'running'}
                    >
                      加载更多月份
                    </Button>
                  ) : null;
                }}
              </Form.Item>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default MessagesPage;
