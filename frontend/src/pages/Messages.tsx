import React, { useState, useEffect } from 'react';
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
  Badge,
  Divider,
  Switch,
  Drawer,
} from 'antd';
import {
  SendOutlined,
  SearchOutlined,
  DeleteOutlined,
  ReloadOutlined,
  EyeOutlined,
  MessageOutlined,
  UserOutlined,
  FileImageOutlined,
  FileTextOutlined,
  VideoCameraOutlined,
  AudioOutlined,
  PushpinOutlined,
  HeartOutlined,
  ShareAltOutlined,
  FilterOutlined,
  DownloadOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTelegramStore, useAuthStore } from '../store';
import { messageApi, telegramApi } from '../services/apiService';
import { TelegramMessage, TelegramGroup, MessageSendRequest, MessageSearchRequest } from '../types';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { RangePicker } = DatePicker;

const MessagesPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<TelegramMessage[]>([]);
  const [groups, setGroups] = useState<TelegramGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<TelegramGroup | null>(null);
  const [selectedMessage, setSelectedMessage] = useState<TelegramMessage | null>(null);
  const [sendModalVisible, setSendModalVisible] = useState(false);
  const [messageDetailVisible, setMessageDetailVisible] = useState(false);
  const [filterDrawerVisible, setFilterDrawerVisible] = useState(false);
  const [form] = Form.useForm();
  const [searchForm] = Form.useForm();
  const [pagination, setPagination] = useState({ current: 1, pageSize: 50, total: 0 });
  const [filters, setFilters] = useState<any>({});
  const [stats, setStats] = useState<any>(null);
  const [replyTo, setReplyTo] = useState<TelegramMessage | null>(null);
  const [isMobile, setIsMobile] = useState(false);
  
  const { user } = useAuthStore();
  const navigate = useNavigate();

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
  const fetchGroups = async () => {
    try {
      const response = await telegramApi.getGroups();
      setGroups(response);
      if (response.length > 0 && !selectedGroup) {
        setSelectedGroup(response[0]);
      }
    } catch (error: any) {
      message.error('获取群组列表失败: ' + error.message);
    }
  };

  // 获取群组消息
  const fetchMessages = async (groupId: number, page: number = 1, searchParams: any = {}) => {
    if (!groupId) return;
    
    setLoading(true);
    try {
      const skip = (page - 1) * pagination.pageSize;
      const params = {
        skip,
        limit: pagination.pageSize,
        ...searchParams,
      };
      
      const response = await messageApi.getGroupMessages(groupId, params);
      setMessages(response);
      
      setPagination(prev => ({
        ...prev,
        current: page,
        total: response.length === pagination.pageSize ? prev.total + response.length : skip + response.length
      }));
    } catch (error: any) {
      message.error('获取消息失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // 获取群组统计
  const fetchGroupStats = async (groupId: number) => {
    try {
      const response = await telegramApi.getGroupStats(groupId);
      setStats(response);
    } catch (error: any) {
      console.error('获取群组统计失败:', error);
    }
  };

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
      
    } catch (error: any) {
      message.error('删除消息失败: ' + error.message);
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

  // 清除搜索
  const clearSearch = () => {
    setFilters({});
    searchForm.resetFields();
    if (selectedGroup) {
      fetchMessages(selectedGroup.id, 1);
    }
  };

  // 获取媒体类型图标
  const getMediaIcon = (mediaType: string) => {
    switch (mediaType) {
      case 'photo': return <FileImageOutlined style={{ color: '#52c41a' }} />;
      case 'video': return <VideoCameraOutlined style={{ color: '#1890ff' }} />;
      case 'document': return <FileTextOutlined style={{ color: '#faad14' }} />;
      case 'audio': return <AudioOutlined style={{ color: '#722ed1' }} />;
      default: return <FileTextOutlined />;
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
              <Paragraph 
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
              </Paragraph>
            )}
            
            {record.media_type && (
              <Space>
                {getMediaIcon(record.media_type)}
                {!isMobile && (
                  <Text type="secondary">{record.media_type}</Text>
                )}
                {record.media_filename && !isMobile && (
                  <Text code style={{ fontSize: 12 }}>
                    {record.media_filename}
                  </Text>
                )}
              </Space>
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
          <div>
            <EyeOutlined style={{ color: '#1890ff' }} />
            <Text style={{ marginLeft: 4 }}>{record.view_count || 0}</Text>
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
      width: isMobile ? 80 : 120,
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
  }, []);

  // 当选择群组时获取消息
  useEffect(() => {
    if (selectedGroup) {
      fetchMessages(selectedGroup.id, 1, filters);
      fetchGroupStats(selectedGroup.id);
    }
  }, [selectedGroup]);

  return (
    <div style={{ padding: isMobile ? 16 : 24 }}>
      <Row gutter={[16, 16]}>
        {/* 顶部统计卡片 */}
        {stats && (
          <Col span={24}>
            <Row gutter={16}>
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
                <Title level={isMobile ? 5 : 4} style={{ margin: 0 }}>
                  {isMobile ? '消息管理' : '群组消息管理'}
                </Title>
                {selectedGroup && (
                  <Tag color="blue">{selectedGroup.title}</Tag>
                )}
              </Space>
            }
            extra={
              <Space wrap size="small">
                <Select
                  placeholder="选择群组"
                  value={selectedGroup?.id}
                  style={{ width: isMobile ? 120 : 200 }}
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
                  icon={<ReloadOutlined />}
                  onClick={() => selectedGroup && fetchMessages(selectedGroup.id, 1, filters)}
                  loading={loading}
                  size={isMobile ? 'small' : 'middle'}
                >
                  刷新
                </Button>
              </Space>
            }
          >
            <Table
              columns={columns}
              dataSource={messages}
              rowKey="id"
              loading={loading}
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
          <Card size="small" style={{ marginBottom: 16, backgroundColor: '#f5f5f5' }}>
            <Text strong>回复消息:</Text>
            <Paragraph style={{ margin: '8px 0 0 0' }}>
              {replyTo.text || '(媒体消息)'}
            </Paragraph>
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
            <RangePicker showTime style={{ width: '100%' }} />
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
                <Paragraph>{selectedMessage.text}</Paragraph>
              )}
              
              {selectedMessage.media_type && (
                <Space>
                  {getMediaIcon(selectedMessage.media_type)}
                  <Text>媒体类型: {selectedMessage.media_type}</Text>
                  {selectedMessage.media_filename && (
                    <Text code>{selectedMessage.media_filename}</Text>
                  )}
                </Space>
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
    </div>
  );
};

export default MessagesPage;