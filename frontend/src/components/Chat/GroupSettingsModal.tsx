import React, { useState, useEffect } from 'react';
import { 
  Modal, 
  Form, 
  Input, 
  Switch, 
  Button, 
  Space, 
  Card,
  Typography,
  Row,
  Col,
  message,
  Divider,
  Avatar,
  Descriptions,
  Tag,
  Statistic,
  Tabs,
  List,
  Badge
} from 'antd';
import { 
  SettingOutlined, 
  UserOutlined, 
  MessageOutlined, 
  FileImageOutlined,
  ClockCircleOutlined,
  TeamOutlined,
  SafetyOutlined,
  InfoCircleOutlined,
  EditOutlined,
  SyncOutlined
} from '@ant-design/icons';
import { TelegramGroup, GroupStats } from '../../types';
import { groupApi, messageApi } from '../../services/apiService';

const { Text, Paragraph } = Typography;
const { TabPane } = Tabs;

interface GroupSettingsModalProps {
  visible: boolean;
  onClose: () => void;
  selectedGroup: TelegramGroup | null;
  onGroupUpdate?: (group: TelegramGroup) => void;
  isMobile?: boolean;
}

const GroupSettingsModal: React.FC<GroupSettingsModalProps> = ({
  visible,
  onClose,
  selectedGroup,
  onGroupUpdate,
  isMobile = false
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [groupStats, setGroupStats] = useState<GroupStats | null>(null);
  const [activeTab, setActiveTab] = useState('info');

  // 获取群组统计信息
  const fetchGroupStats = async () => {
    if (!selectedGroup) return;
    
    try {
      const stats = await groupApi.getGroupStats(selectedGroup.id);
      setGroupStats(stats);
    } catch (error: any) {
      console.error('获取群组统计失败:', error);
    }
  };

  // 同步群组信息
  const handleSyncGroup = async () => {
    if (!selectedGroup) return;
    
    setSyncing(true);
    try {
      const updatedGroup = await groupApi.syncGroup(selectedGroup.id);
      message.success('群组信息同步成功！');
      onGroupUpdate?.(updatedGroup);
      fetchGroupStats();
    } catch (error: any) {
      message.error('同步群组信息失败: ' + error.message);
      console.error('同步群组信息失败:', error);
    } finally {
      setSyncing(false);
    }
  };

  // 更新群组设置
  const handleUpdateSettings = async (values: any) => {
    if (!selectedGroup) return;
    
    setLoading(true);
    try {
      const updatedGroup = await groupApi.updateGroup(selectedGroup.id, {
        is_active: values.is_active,
        description: values.description,
      });
      
      message.success('群组设置更新成功！');
      onGroupUpdate?.(updatedGroup);
      onClose();
    } catch (error: any) {
      message.error('更新群组设置失败: ' + error.message);
      console.error('更新群组设置失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 生成群组头像
  const generateGroupAvatar = (title: string) => {
    const firstChar = title.charAt(0).toUpperCase();
    const colors = [
      '#f56a00', '#7265e6', '#ffbf00', '#00a2ae', 
      '#87d068', '#1890ff', '#722ed1', '#eb2f96',
      '#52c41a', '#faad14', '#13c2c2', '#f5222d'
    ];
    
    let hash = 0;
    for (let i = 0; i < title.length; i++) {
      hash = title.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    const color = colors[Math.abs(hash) % colors.length];
    
    return (
      <Avatar 
        size={64} 
        style={{ 
          backgroundColor: color,
          color: 'white',
          fontWeight: 'bold',
          fontSize: 28
        }}
      >
        {firstChar}
      </Avatar>
    );
  };

  // 当模态框打开时初始化
  useEffect(() => {
    if (visible && selectedGroup) {
      fetchGroupStats();
      form.setFieldsValue({
        is_active: selectedGroup.is_active,
        description: selectedGroup.description || '',
      });
    }
  }, [visible, selectedGroup]);

  if (!selectedGroup) return null;

  return (
    <Modal
      title={
        <Space>
          <SettingOutlined />
          群组设置
          <Text type="secondary">
            - {selectedGroup.title}
          </Text>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={isMobile ? '100%' : 800}
      style={isMobile ? { top: 20 } : {}}
      destroyOnClose
    >
      <Tabs 
        activeKey={activeTab} 
        onChange={setActiveTab}
        tabPosition={isMobile ? 'top' : 'left'}
      >
        <TabPane 
          tab={
            <Space>
              <InfoCircleOutlined />
              基本信息
            </Space>
          } 
          key="info"
        >
          <div style={{ padding: '0 16px' }}>
            <Card>
              <Row gutter={24} align="middle">
                <Col>
                  {generateGroupAvatar(selectedGroup.title)}
                </Col>
                <Col flex="auto">
                  <div style={{ marginBottom: 8 }}>
                    <Text strong style={{ fontSize: 18 }}>
                      {selectedGroup.title}
                    </Text>
                    <Tag 
                      color={selectedGroup.is_active ? 'green' : 'red'}
                      style={{ marginLeft: 8 }}
                    >
                      {selectedGroup.is_active ? '活跃' : '暂停'}
                    </Tag>
                  </div>
                  
                  {selectedGroup.username && (
                    <div style={{ marginBottom: 8 }}>
                      <Text type="secondary">
                        @{selectedGroup.username}
                      </Text>
                    </div>
                  )}
                  
                  <div style={{ marginBottom: 8 }}>
                    <Space>
                      <TeamOutlined />
                      <Text type="secondary">
                        {selectedGroup.member_count?.toLocaleString() || 0} 成员
                      </Text>
                    </Space>
                  </div>
                  
                  <div>
                    <Space>
                      <ClockCircleOutlined />
                      <Text type="secondary">
                        创建时间: {new Date(selectedGroup.created_at).toLocaleString('zh-CN')}
                      </Text>
                    </Space>
                  </div>
                </Col>
                <Col>
                  <Button 
                    type="primary" 
                    icon={<SyncOutlined />}
                    loading={syncing}
                    onClick={handleSyncGroup}
                  >
                    同步信息
                  </Button>
                </Col>
              </Row>
            </Card>
            
            <Divider />
            
            <Descriptions title="详细信息" bordered>
              <Descriptions.Item label="Telegram ID">
                {selectedGroup.telegram_id}
              </Descriptions.Item>
              <Descriptions.Item label="内部ID">
                {selectedGroup.id}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Badge 
                  status={selectedGroup.is_active ? 'success' : 'error'}
                  text={selectedGroup.is_active ? '活跃' : '暂停'}
                />
              </Descriptions.Item>
              <Descriptions.Item label="权限" span={3}>
                <Space wrap>
                  {selectedGroup.can_send_messages !== false ? (
                    <Tag color="green">可发送消息</Tag>
                  ) : (
                    <Tag color="red">禁止发送消息</Tag>
                  )}
                  {selectedGroup.permissions?.can_send_media !== false ? (
                    <Tag color="green">可发送媒体</Tag>
                  ) : (
                    <Tag color="red">禁止发送媒体</Tag>
                  )}
                  {selectedGroup.permissions?.can_send_stickers !== false ? (
                    <Tag color="green">可发送贴纸</Tag>
                  ) : (
                    <Tag color="red">禁止发送贴纸</Tag>
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={3}>
                {selectedGroup.description || '无描述'}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间" span={2}>
                {new Date(selectedGroup.created_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {new Date(selectedGroup.updated_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
            </Descriptions>
          </div>
        </TabPane>
        
        <TabPane 
          tab={
            <Space>
              <MessageOutlined />
              消息统计
            </Space>
          } 
          key="stats"
        >
          <div style={{ padding: '0 16px' }}>
            {groupStats ? (
              <>
                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col xs={12} sm={6}>
                    <Card>
                      <Statistic
                        title="总消息数"
                        value={groupStats.total_messages}
                        prefix={<MessageOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col xs={12} sm={6}>
                    <Card>
                      <Statistic
                        title="媒体消息"
                        value={groupStats.media_messages}
                        prefix={<FileImageOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col xs={12} sm={6}>
                    <Card>
                      <Statistic
                        title="文本消息"
                        value={groupStats.text_messages}
                        prefix={<EditOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col xs={12} sm={6}>
                    <Card>
                      <Statistic
                        title="群组成员"
                        value={groupStats.member_count}
                        prefix={<TeamOutlined />}
                      />
                    </Card>
                  </Col>
                </Row>
                
                <Card title="消息分布">
                  <Row gutter={16}>
                    <Col xs={24} sm={12}>
                      <div style={{ textAlign: 'center' }}>
                        <Text strong>媒体消息占比</Text>
                        <div style={{ marginTop: 8 }}>
                          <Text style={{ fontSize: 24, color: '#1890ff' }}>
                            {groupStats.total_messages > 0 
                              ? ((groupStats.media_messages / groupStats.total_messages) * 100).toFixed(1)
                              : 0}%
                          </Text>
                        </div>
                      </div>
                    </Col>
                    <Col xs={24} sm={12}>
                      <div style={{ textAlign: 'center' }}>
                        <Text strong>文本消息占比</Text>
                        <div style={{ marginTop: 8 }}>
                          <Text style={{ fontSize: 24, color: '#52c41a' }}>
                            {groupStats.total_messages > 0 
                              ? ((groupStats.text_messages / groupStats.total_messages) * 100).toFixed(1)
                              : 0}%
                          </Text>
                        </div>
                      </div>
                    </Col>
                  </Row>
                </Card>
              </>
            ) : (
              <Card>
                <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                  <MessageOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
                  <div style={{ marginTop: 16 }}>
                    <Text type="secondary">
                      暂无统计数据
                    </Text>
                  </div>
                </div>
              </Card>
            )}
          </div>
        </TabPane>
        
        <TabPane 
          tab={
            <Space>
              <EditOutlined />
              群组设置
            </Space>
          } 
          key="settings"
        >
          <div style={{ padding: '0 16px' }}>
            <Form
              form={form}
              layout="vertical"
              onFinish={handleUpdateSettings}
            >
              <Form.Item
                name="is_active"
                label="群组状态"
                valuePropName="checked"
              >
                <Switch 
                  checkedChildren="活跃" 
                  unCheckedChildren="暂停"
                />
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    暂停状态下将停止监听此群组的消息
                  </Text>
                </div>
              </Form.Item>
              
              <Form.Item
                name="description"
                label="群组描述"
              >
                <Input.TextArea
                  placeholder="请输入群组描述"
                  rows={4}
                  maxLength={500}
                  showCount
                />
              </Form.Item>
              
              <Form.Item style={{ marginBottom: 0 }}>
                <Space>
                  <Button onClick={onClose}>
                    取消
                  </Button>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    loading={loading}
                  >
                    保存设置
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </div>
        </TabPane>
      </Tabs>
    </Modal>
  );
};

export default GroupSettingsModal;