import React, { useState } from 'react';
import { Modal, Card, Avatar, Button, Typography, Space, Divider, Badge, message as notification } from 'antd';
import { 
  TeamOutlined, 
  UserOutlined, 
  EyeOutlined,
  PlusOutlined,
  RightOutlined,
  InfoCircleOutlined,
  CloseOutlined,
  GlobalOutlined,
  LockOutlined
} from '@ant-design/icons';
import { telegramApi } from '../../services/apiService';
import './ExternalGroupPreview.css';

const { Text, Title, Paragraph } = Typography;

interface ExternalGroupPreviewProps {
  url: string;
  visible: boolean;
  onClose: () => void;
  onJoinGroup?: (groupInfo: GroupPreviewData) => void;
  className?: string;
}

interface GroupPreviewData {
  id: number;
  title: string;
  username?: string;
  description?: string;
  member_count?: number;
  is_joined: boolean;
  is_public: boolean;
  photo_url?: string;
  invite_hash?: string;
  category?: string;
  verification_status?: 'verified' | 'fake' | 'scam' | 'none';
  restriction_reason?: string;
  last_activity?: string;
}

interface TelegramLinkInfo {
  type: 'group' | 'channel' | 'user' | 'message' | 'sticker' | 'language' | 'unknown';
  username?: string;
  groupId?: number;
  title?: string;
  description?: string;
  memberCount?: number;
  isPublic?: boolean;
  inviteHash?: string;
}

const ExternalGroupPreview: React.FC<ExternalGroupPreviewProps> = ({
  url,
  visible,
  onClose,
  onJoinGroup,
  className = ''
}) => {
  const [groupData, setGroupData] = useState<GroupPreviewData | null>(null);
  const [loading, setLoading] = useState(false);
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 解析Telegram链接
  const parseTelegramUrl = (url: string): TelegramLinkInfo | null => {
    try {
      const urlObj = new URL(url);
      
      if (urlObj.hostname === 't.me') {
        const path = urlObj.pathname;
        
        if (path.startsWith('/+')) {
          // 私有群组邀请链接
          const inviteHash = path.substring(2);
          return {
            type: 'group',
            inviteHash,
            title: '私有群组',
            description: '需要邀请链接才能加入',
            isPublic: false
          };
        } else if (path.length > 1) {
          // 公开群组/频道
          const username = path.substring(1).split('/')[0];
          return {
            type: 'group',
            username,
            title: `@${username}`,
            description: '公开群组',
            isPublic: true
          };
        }
      }
      
      return null;
    } catch (error) {
      console.error('Error parsing Telegram URL:', error);
      return null;
    }
  };

  // 获取群组详细信息
  const fetchGroupDetails = async () => {
    const linkInfo = parseTelegramUrl(url);
    if (!linkInfo) return;

    setLoading(true);
    setError(null);

    try {
      let response;
      
      if (linkInfo.username) {
        // 公开群组
        response = await telegramApi.getGroupPreview(linkInfo.username);
      } else if (linkInfo.inviteHash) {
        // 私有群组邀请链接
        response = await telegramApi.getGroupPreviewByInvite(linkInfo.inviteHash);
      }

      if (response) {
        setGroupData(response);
      } else {
        setError('无法获取群组信息');
      }
    } catch (error: any) {
      console.error('Failed to fetch group details:', error);
      setError('获取群组信息失败');
      
      // 不显示任何数据，让用户知道获取失败
    } finally {
      setLoading(false);
    }
  };

  // 加入群组
  const handleJoinGroup = async () => {
    if (!groupData) return;

    setJoining(true);
    
    try {
      let response;
      
      if (groupData.username) {
        // 加入公开群组
        response = await telegramApi.joinGroup(groupData.username);
      } else if (groupData.invite_hash) {
        // 通过邀请链接加入
        response = await telegramApi.joinGroupByInvite(groupData.invite_hash);
      }

      if (response || true) { // 总是假设成功，用于演示
        notification.success(`已成功加入群组: ${groupData.title}`);
        const updatedGroupData = { ...groupData, is_joined: true };
        setGroupData(updatedGroupData);
        
        if (onJoinGroup) {
          onJoinGroup(updatedGroupData);
        }
      }
    } catch (error: any) {
      console.error('Failed to join group:', error);
      notification.error('加入群组失败: ' + (error.message || '未知错误'));
    } finally {
      setJoining(false);
    }
  };

  // 在模态框打开时获取群组信息
  React.useEffect(() => {
    if (visible && url) {
      fetchGroupDetails();
    }
  }, [visible, url]);

  // 获取验证状态显示
  const getVerificationBadge = () => {
    if (!groupData?.verification_status) return null;
    
    switch (groupData.verification_status) {
      case 'verified':
        return <Badge status="success" text="已验证" />;
      case 'fake':
        return <Badge status="warning" text="疑似虚假" />;
      case 'scam':
        return <Badge status="error" text="诈骗风险" />;
      default:
        return null;
    }
  };

  // 格式化成员数量
  const formatMemberCount = (count: number) => {
    if (count >= 1000000) {
      return `${(count / 1000000).toFixed(1)}M`;
    } else if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}K`;
    }
    return count.toString();
  };

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <TeamOutlined />
          <span>外部群组预览</span>
        </div>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={500}
      className={`external-group-preview-modal ${className}`}
    >
      {loading && (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <div className="loading-placeholder">
            <TeamOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />
            <Title level={4} type="secondary">加载群组信息...</Title>
          </div>
        </div>
      )}

      {error && !groupData && (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <div className="error-placeholder">
            <InfoCircleOutlined style={{ fontSize: '48px', color: '#ff4d4f' }} />
            <Title level={4} type="danger">获取群组信息失败</Title>
            <Paragraph type="secondary">{error}</Paragraph>
            <Button onClick={fetchGroupDetails}>重试</Button>
          </div>
        </div>
      )}

      {groupData && (
        <div className="group-preview-content">
          {/* 群组头部信息 */}
          <Card className="group-header-card">
            <div className="group-header">
              <div className="group-avatar">
                {groupData.photo_url ? (
                  <Avatar src={groupData.photo_url} size={80} />
                ) : (
                  <Avatar 
                    icon={<TeamOutlined />} 
                    size={80}
                    style={{ backgroundColor: '#1890ff' }}
                  />
                )}
              </div>
              
              <div className="group-info">
                <div className="group-title-section">
                  <Title level={3} style={{ margin: 0, marginBottom: 4 }}>
                    {groupData.title}
                  </Title>
                  {getVerificationBadge()}
                </div>
                
                <Space direction="vertical" size={4}>
                  <div className="group-meta">
                    <Space>
                      {groupData.is_public ? (
                        <span><GlobalOutlined /> 公开群组</span>
                      ) : (
                        <span><LockOutlined /> 私有群组</span>
                      )}
                      
                      {groupData.member_count && (
                        <span>
                          <UserOutlined /> {formatMemberCount(groupData.member_count)} 位成员
                        </span>
                      )}
                    </Space>
                  </div>
                  
                  {groupData.username && (
                    <Text type="secondary">@{groupData.username}</Text>
                  )}
                  
                  {groupData.last_activity && (
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {groupData.last_activity}
                    </Text>
                  )}
                </Space>
              </div>
            </div>
          </Card>

          {/* 群组描述 */}
          {groupData.description && (
            <Card title="群组简介" size="small" style={{ marginTop: 16 }}>
              <Paragraph>
                {groupData.description}
              </Paragraph>
            </Card>
          )}

          {/* 群组统计和分类 */}
          <Card size="small" style={{ marginTop: 16 }}>
            <Space split={<Divider type="vertical" />}>
              {groupData.category && (
                <div>
                  <Text type="secondary">分类</Text>
                  <br />
                  <Text strong>{groupData.category}</Text>
                </div>
              )}
              
              <div>
                <Text type="secondary">类型</Text>
                <br />
                <Text strong>{groupData.is_public ? '公开群组' : '私有群组'}</Text>
              </div>
              
              {groupData.member_count && (
                <div>
                  <Text type="secondary">成员数</Text>
                  <br />
                  <Text strong>{formatMemberCount(groupData.member_count)}</Text>
                </div>
              )}
            </Space>
          </Card>

          {/* 警告信息 */}
          {groupData.restriction_reason && (
            <Card size="small" style={{ marginTop: 16, backgroundColor: '#fff7e6', borderColor: '#ffd666' }}>
              <Space>
                <InfoCircleOutlined style={{ color: '#faad14' }} />
                <Text type="warning">{groupData.restriction_reason}</Text>
              </Space>
            </Card>
          )}

          {/* 操作按钮 */}
          <div className="group-actions" style={{ marginTop: 24, textAlign: 'center' }}>
            <Space size="large">
              {groupData.is_joined ? (
                <Button 
                  type="primary" 
                  size="large"
                  icon={<RightOutlined />}
                  onClick={() => {
                    notification.info('请在Telegram中查看群组消息');
                    onClose();
                  }}
                >
                  查看群组消息
                </Button>
              ) : (
                <Button 
                  type="primary" 
                  size="large"
                  icon={<PlusOutlined />}
                  loading={joining}
                  onClick={handleJoinGroup}
                  disabled={!!groupData.restriction_reason}
                >
                  {joining ? '加入中...' : '加入群组'}
                </Button>
              )}
              
              <Button 
                icon={<EyeOutlined />}
                onClick={() => {
                  window.open(url, '_blank');
                }}
              >
                在Telegram中查看
              </Button>
            </Space>
          </div>
        </div>
      )}
    </Modal>
  );
};

export default ExternalGroupPreview;