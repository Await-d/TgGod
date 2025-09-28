import React, { useState, useEffect } from 'react';
import { 
  Drawer, 
  Input, 
  Button, 
  Space, 
  List, 
  Card, 
  Typography, 
  Tag, 
  DatePicker, 
  Select, 
  Switch, 
  Form, 
  Divider,
  Empty,
  Spin,
  message
} from 'antd';
import {
  SearchOutlined,
  CloseOutlined,
  UserOutlined,
  FileImageOutlined,
  // MessageOutlined,
  // CalendarOutlined,
  FilterOutlined
} from '@ant-design/icons';
import { TelegramGroup, TelegramMessage, MessageSearchRequest } from '../../types';
import { messageApi } from '../../services/apiService';
import MessageHighlight from './MessageHighlight';

const { Text, Paragraph } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

interface MessageSearchDrawerProps {
  visible: boolean;
  onClose: () => void;
  selectedGroup: TelegramGroup | null;
  onMessageSelect?: (message: TelegramMessage) => void;
  isMobile?: boolean;
}

const MessageSearchDrawer: React.FC<MessageSearchDrawerProps> = ({
  visible,
  onClose,
  selectedGroup,
  onMessageSelect,
  isMobile = false
}) => {
  const [form] = Form.useForm();
  const [searchResults, setSearchResults] = useState<TelegramMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  // const [currentPage] = useState(1); // 暂时未使用分页功能
  const [total, setTotal] = useState(0);

  // 重置搜索结果
  const resetResults = () => {
    setSearchResults([]);
    setTotal(0);
  };

  // 执行搜索
  const handleSearch = async (values: any) => {
    if (!selectedGroup) return;

    setLoading(true);
    try {
      const searchParams: MessageSearchRequest = {
        query: values.query || searchQuery,
        sender_username: values.sender_username,
        media_type: values.media_type,
        has_media: values.has_media,
        is_forwarded: values.is_forwarded,
        start_date: values.date_range?.[0]?.format('YYYY-MM-DD'),
        end_date: values.date_range?.[1]?.format('YYYY-MM-DD'),
      };

      const response = await messageApi.searchMessages(selectedGroup.id, searchParams);
      setSearchResults(response.items || []);
      setTotal(response.total || 0);
      // 分页功能暂时不需要
    } catch (error: any) {
      message.error('搜索失败: ' + error.message);
      console.error('搜索失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 快速搜索
  const handleQuickSearch = () => {
    if (!searchQuery.trim()) return;
    
    form.setFieldsValue({ query: searchQuery });
    handleSearch({ query: searchQuery });
  };

  // 清空搜索
  const handleClearSearch = () => {
    form.resetFields();
    setSearchQuery('');
    resetResults();
  };

  // 选择消息
  const handleSelectMessage = (message: TelegramMessage) => {
    onMessageSelect?.(message);
    onClose();
  };

  // 格式化时间
  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // 获取媒体类型标签
  const getMediaTypeTag = (mediaType: string) => {
    const mediaTypes = {
      photo: { color: 'green', text: '图片' },
      video: { color: 'blue', text: '视频' },
      document: { color: 'orange', text: '文档' },
      audio: { color: 'purple', text: '音频' },
      voice: { color: 'pink', text: '语音' },
      sticker: { color: 'cyan', text: '贴纸' },
    };
    
    const config = mediaTypes[mediaType as keyof typeof mediaTypes];
    return config ? (
      <Tag color={config.color}>
        {config.text}
      </Tag>
    ) : null;
  };

  // 渲染搜索结果项
  const renderSearchResult = (item: TelegramMessage) => (
    <List.Item
      key={item.id}
      style={{ cursor: 'pointer' }}
      onClick={() => handleSelectMessage(item)}
    >
      <Card 
        size="small" 
        style={{ width: '100%' }}
        hoverable
        bodyStyle={{ padding: '12px 16px' }}
      >
        <div style={{ marginBottom: 8 }}>
          <Space>
            <UserOutlined style={{ color: '#1890ff' }} />
            <Text strong style={{ color: '#1890ff' }}>
              {item.sender_name || item.sender_username || '未知用户'}
            </Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {formatTime(item.date)}
            </Text>
            {item.media_type && getMediaTypeTag(item.media_type)}
            {item.is_forwarded && (
              <Tag color="orange">转发</Tag>
            )}
            {item.is_pinned && (
              <Tag color="red">置顶</Tag>
            )}
          </Space>
        </div>
        
        {item.text && (
          <Paragraph 
            style={{ margin: 0, fontSize: 14 }}
            ellipsis={{ rows: 2 }}
          >
            <MessageHighlight 
              text={item.text} 
              searchQuery={searchQuery}
            />
          </Paragraph>
        )}
        
        {item.media_type && !item.text && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <FileImageOutlined style={{ color: '#8c8c8c' }} />
            <Text type="secondary">
              {item.media_filename || `${item.media_type.toUpperCase()} 文件`}
            </Text>
          </div>
        )}
        
        {item.view_count !== undefined && (
          <div style={{ marginTop: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              查看次数: {item.view_count}
            </Text>
          </div>
        )}
      </Card>
    </List.Item>
  );

  // 当抽屉打开时重置状态
  useEffect(() => {
    if (visible) {
      resetResults();
      setShowAdvanced(false);
    }
  }, [visible]);

  return (
    <Drawer
      title={
        <Space>
          <SearchOutlined />
          搜索消息
          {selectedGroup && (
            <Text type="secondary">
              - {selectedGroup.title}
            </Text>
          )}
        </Space>
      }
      placement="right"
      onClose={onClose}
      open={visible}
      width={isMobile ? '100%' : 600}
      destroyOnClose
    >
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* 搜索输入区 */}
        <div style={{ marginBottom: 16 }}>
          <Input.Search
            placeholder="搜索消息内容..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onSearch={handleQuickSearch}
            enterButton={
              <Button 
                type="primary" 
                icon={<SearchOutlined />}
                loading={loading}
              >
                搜索
              </Button>
            }
            size="large"
          />
          
          <div style={{ marginTop: 12, textAlign: 'right' }}>
            <Space>
              <Button
                type="link"
                size="small"
                icon={<FilterOutlined />}
                onClick={() => setShowAdvanced(!showAdvanced)}
              >
                {showAdvanced ? '收起高级搜索' : '高级搜索'}
              </Button>
              
              <Button
                type="link"
                size="small"
                icon={<CloseOutlined />}
                onClick={handleClearSearch}
              >
                清空
              </Button>
            </Space>
          </div>
        </div>

        {/* 高级搜索选项 */}
        {showAdvanced && (
          <Card size="small" style={{ marginBottom: 16 }}>
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSearch}
              size="small"
            >
              <Form.Item name="sender_username" label="发送者">
                <Input placeholder="用户名或昵称" />
              </Form.Item>
              
              <Form.Item name="media_type" label="媒体类型">
                <Select placeholder="选择媒体类型" allowClear>
                  <Option value="photo">图片</Option>
                  <Option value="video">视频</Option>
                  <Option value="document">文档</Option>
                  <Option value="audio">音频</Option>
                  <Option value="voice">语音</Option>
                  <Option value="sticker">贴纸</Option>
                </Select>
              </Form.Item>
              
              <Form.Item name="date_range" label="时间范围">
                <RangePicker style={{ width: '100%' }} />
              </Form.Item>
              
              <Form.Item label="其他选项">
                <Space direction="vertical">
                  <Form.Item name="has_media" valuePropName="checked" noStyle>
                    <Switch size="small" />
                    <Text style={{ marginLeft: 8 }}>包含媒体文件</Text>
                  </Form.Item>
                  
                  <Form.Item name="is_forwarded" valuePropName="checked" noStyle>
                    <Switch size="small" />
                    <Text style={{ marginLeft: 8 }}>转发消息</Text>
                  </Form.Item>
                </Space>
              </Form.Item>
              
              <Form.Item style={{ marginBottom: 0 }}>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={loading}
                  block
                >
                  搜索
                </Button>
              </Form.Item>
            </Form>
          </Card>
        )}

        <Divider style={{ margin: '16px 0' }} />

        {/* 搜索结果 */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <Spin size="large" />
              <div style={{ marginTop: 16 }}>
                <Text type="secondary">搜索中...</Text>
              </div>
            </div>
          ) : searchResults.length > 0 ? (
            <>
              <div style={{ marginBottom: 16 }}>
                <Space>
                  <Text strong>搜索结果</Text>
                  <Text type="secondary">
                    共找到 {total} 条消息
                  </Text>
                </Space>
              </div>
              
              <List
                dataSource={searchResults}
                renderItem={renderSearchResult}
                size="small"
                split={false}
                style={{ marginBottom: 16 }}
              />
            </>
          ) : searchQuery && !loading ? (
            <Empty 
              description="没有找到匹配的消息" 
              style={{ marginTop: 40 }}
            />
          ) : (
            <Empty 
              description="输入关键词开始搜索" 
              style={{ marginTop: 40 }}
            />
          )}
        </div>
      </div>
    </Drawer>
  );
};

export default MessageSearchDrawer;