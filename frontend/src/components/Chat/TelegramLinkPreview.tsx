import React, { useState, useEffect } from 'react';
import { Card, Button, Avatar, Typography, Space, message as notification, Spin } from 'antd';
import { 
  TeamOutlined, 
  UserOutlined, 
  LinkOutlined, 
  RightOutlined,
  PlusOutlined,
  CheckOutlined,
  EyeOutlined
} from '@ant-design/icons';
import { TelegramGroup } from '../../types';
import { telegramApi } from '../../services/apiService';
import ExternalGroupPreview from './ExternalGroupPreview';
import './TelegramLinkPreview.css';

const { Text, Title } = Typography;

interface TelegramLinkPreviewProps {
  url: string;
  onJumpToGroup?: (groupId: number) => void;
  className?: string;
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

interface GroupPreviewData {
  id: number;
  title: string;
  description?: string;
  member_count?: number;
  is_joined: boolean;
  is_public: boolean;
  photo_url?: string;
}

const TelegramLinkPreview: React.FC<TelegramLinkPreviewProps> = ({
  url,
  onJumpToGroup,
  className = ''
}) => {
  const [linkInfo, setLinkInfo] = useState<TelegramLinkInfo | null>(null);
  const [groupPreview, setGroupPreview] = useState<GroupPreviewData | null>(null);
  const [loading, setLoading] = useState(false);
  const [joining, setJoining] = useState(false);
  const [showExternalPreview, setShowExternalPreview] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // 解析Telegram链接
  const parseTelegramUrl = (url: string): TelegramLinkInfo | null => {
    try {
      const urlObj = new URL(url);
      
      // 处理 t.me 域名
      if (urlObj.hostname === 't.me') {
        const path = urlObj.pathname;
        const searchParams = urlObj.searchParams;
        
        // 语言设置链接：https://t.me/setlanguage/zhlangcn
        if (path.startsWith('/setlanguage/')) {
          const langCode = path.split('/')[2];
          return {
            type: 'language',
            title: '语言设置',
            description: `设置语言为: ${langCode}`,
            username: langCode
          };
        }
        
        // 群组/频道链接：https://t.me/username
        if (path.startsWith('/+')) {
          // 私有群组邀请链接
          const inviteHash = path.substring(2);
          return {
            type: 'group',
            inviteHash,
            title: '私有群组',
            description: '点击查看群组详情',
            isPublic: false
          };
        } else if (path.length > 1) {
          // 公开群组/频道
          const username = path.substring(1).split('/')[0];
          return {
            type: 'group',
            username,
            title: `@${username}`,
            description: '点击查看群组详情',
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

  // 获取群组预览信息
  const fetchGroupPreview = async (linkInfo: TelegramLinkInfo) => {
    if (linkInfo.type !== 'group') return;
    
    setLoading(true);
    setApiError(null);
    console.log('TelegramLinkPreview - fetchGroupPreview called', linkInfo);
    
    try {
      let response;
      
      if (linkInfo.username) {
        // 公开群组
        console.log('TelegramLinkPreview - fetching public group preview:', linkInfo.username);
        response = await telegramApi.getGroupPreview(linkInfo.username);
      } else if (linkInfo.inviteHash) {
        // 私有群组邀请链接
        console.log('TelegramLinkPreview - fetching private group preview:', linkInfo.inviteHash);
        response = await telegramApi.getGroupPreviewByInvite(linkInfo.inviteHash);
      }
      
      if (response) {
        console.log('TelegramLinkPreview - group preview response:', response);
        setGroupPreview(response);
      }
    } catch (error: any) {
      console.error('Failed to fetch group preview:', error);
      setApiError(error?.response?.status === 404 ? 'API接口未实现' : '网络错误');
      // 不使用模拟数据，保持 groupPreview 为 null
    } finally {
      setLoading(false);
    }
  };

  // 加入群组
  const handleJoinGroup = async () => {
    if (!linkInfo || !groupPreview) return;
    
    setJoining(true);
    console.log('TelegramLinkPreview - attempting to join group', { linkInfo, groupPreview });
    
    try {
      let response;
      
      if (linkInfo.username) {
        // 加入公开群组
        console.log('TelegramLinkPreview - joining public group:', linkInfo.username);
        response = await telegramApi.joinGroup(linkInfo.username);
      } else if (linkInfo.inviteHash) {
        // 通过邀请链接加入
        console.log('TelegramLinkPreview - joining via invite:', linkInfo.inviteHash);
        response = await telegramApi.joinGroupByInvite(linkInfo.inviteHash);
      }
      
      if (response) {
        console.log('TelegramLinkPreview - join success response:', response);
        notification.success('已成功加入群组');
        setGroupPreview(prev => prev ? { ...prev, is_joined: true } : null);
      }
    } catch (error: any) {
      console.error('Failed to join group:', error);
      if (error?.response?.status === 404) {
        notification.error('API接口未实现，请在Telegram中手动加入');
      } else {
        notification.error('加入群组失败: ' + (error.message || '未知错误'));
      }
    } finally {
      setJoining(false);
    }
  };

  // 跳转到群组
  const handleJumpToGroup = () => {
    console.log('TelegramLinkPreview - handleJumpToGroup called', {
      groupPreview,
      isJoined: groupPreview?.is_joined,
      hasOnJumpToGroup: !!onJumpToGroup
    });
    
    if (groupPreview && groupPreview.is_joined && onJumpToGroup) {
      console.log('TelegramLinkPreview - jumping to group:', groupPreview.id);
      onJumpToGroup(groupPreview.id);
    } else {
      console.log('TelegramLinkPreview - cannot jump to group, missing conditions');
      if (!groupPreview) console.log('TelegramLinkPreview - no group preview');
      if (!groupPreview?.is_joined) console.log('TelegramLinkPreview - not joined to group');
      if (!onJumpToGroup) console.log('TelegramLinkPreview - no onJumpToGroup callback');
    }
  };

  // 初始化
  useEffect(() => {
    const info = parseTelegramUrl(url);
    setLinkInfo(info);
    
    if (info) {
      fetchGroupPreview(info);
    }
  }, [url]);

  // 渲染不同类型的预览
  const renderPreviewContent = () => {
    if (!linkInfo) {
      return (
        <Card size="small" className="telegram-link-preview unknown">
          <Space>
            <LinkOutlined style={{ color: '#8c8c8c' }} />
            <Text type="secondary">无法识别的Telegram链接</Text>
          </Space>
        </Card>
      );
    }

    if (linkInfo.type === 'language') {
      return (
        <Card size="small" className="telegram-link-preview language">
          <div className="preview-content">
            <div className="preview-icon">
              <Avatar icon={<LinkOutlined />} style={{ backgroundColor: '#1890ff' }} />
            </div>
            <div className="preview-info">
              <Title level={5} style={{ margin: 0 }}>{linkInfo.title}</Title>
              <Text type="secondary">{linkInfo.description}</Text>
            </div>
            <div className="preview-action">
              <Button 
                type="primary" 
                size="small" 
                href={url} 
                target="_blank"
                icon={<LinkOutlined />}
              >
                打开链接
              </Button>
            </div>
          </div>
        </Card>
      );
    }

    if (linkInfo.type === 'group') {
      if (loading) {
        return (
          <Card size="small" className="telegram-link-preview loading">
            <div className="preview-content">
              <Spin size="small" />
              <Text type="secondary" style={{ marginLeft: 8 }}>加载群组信息...</Text>
            </div>
          </Card>
        );
      }

      if (apiError) {
        return (
          <Card size="small" className="telegram-link-preview error">
            <div className="preview-content">
              <div className="preview-icon">
                <Avatar icon={<TeamOutlined />} style={{ backgroundColor: '#ff4d4f' }} />
              </div>
              <div className="preview-info">
                <Title level={5} style={{ margin: 0 }}>
                  {linkInfo.username ? `@${linkInfo.username}` : '私有群组'}
                </Title>
                <Text type="secondary">{apiError}</Text>
              </div>
              <div className="preview-action">
                <Button 
                  type="default" 
                  size="small"
                  href={url}
                  target="_blank"
                  icon={<LinkOutlined />}
                >
                  在浏览器中打开
                </Button>
              </div>
            </div>
          </Card>
        );
      }

      if (!groupPreview) {
        return (
          <Card size="small" className="telegram-link-preview basic">
            <div className="preview-content">
              <div className="preview-icon">
                <Avatar icon={<TeamOutlined />} style={{ backgroundColor: '#1890ff' }} />
              </div>
              <div className="preview-info">
                <Title level={5} style={{ margin: 0 }}>
                  {linkInfo.username ? `@${linkInfo.username}` : '私有群组'}
                </Title>
                <Text type="secondary">
                  {linkInfo.isPublic ? '公开群组' : '私有群组'}
                </Text>
              </div>
              <div className="preview-action">
                <Button 
                  type="primary" 
                  size="small"
                  href={url}
                  target="_blank"
                  icon={<LinkOutlined />}
                >
                  在Telegram中打开
                </Button>
              </div>
            </div>
          </Card>
        );
      }

      return (
        <Card size="small" className="telegram-link-preview group">
          <div className="preview-content">
            <div className="preview-icon">
              {groupPreview.photo_url ? (
                <Avatar src={groupPreview.photo_url} size={48} />
              ) : (
                <Avatar 
                  icon={<TeamOutlined />} 
                  size={48}
                  style={{ backgroundColor: '#1890ff' }}
                />
              )}
            </div>
            
            <div className="preview-info">
              <Title level={5} style={{ margin: 0 }} title={groupPreview.title}>
                {groupPreview.title}
              </Title>
              <Text type="secondary">
                {groupPreview.member_count ? `${groupPreview.member_count} 位成员` : ''}
                {groupPreview.is_public ? ' • 公开群组' : ' • 私有群组'}
              </Text>
              {groupPreview.description && (
                <Text 
                  type="secondary" 
                  style={{ 
                    display: 'block', 
                    marginTop: 4,
                    fontSize: '12px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}
                  title={groupPreview.description}
                >
                  {groupPreview.description}
                </Text>
              )}
            </div>
            
            <div className="preview-action">
              <Space direction="vertical" size={4}>
                <Button 
                  type="primary" 
                  size="small"
                  icon={<EyeOutlined />}
                  onClick={() => setShowExternalPreview(true)}
                  style={{ width: '100%' }}
                >
                  查看详情
                </Button>
                
                {groupPreview.is_joined ? (
                  <Button 
                    type="default" 
                    size="small"
                    icon={<RightOutlined />}
                    onClick={handleJumpToGroup}
                    disabled={!onJumpToGroup}
                    style={{ width: '100%' }}
                  >
                    进入群组
                  </Button>
                ) : (
                  <Button 
                    type="default" 
                    size="small"
                    icon={joining ? <Spin size="small" /> : <PlusOutlined />}
                    onClick={handleJoinGroup}
                    loading={joining}
                    style={{ width: '100%' }}
                  >
                    快速加入
                  </Button>
                )}
              </Space>
            </div>
          </div>
          
          {groupPreview.is_joined && (
            <div className="joined-indicator">
              <CheckOutlined style={{ color: '#52c41a', marginRight: 4 }} />
              <Text style={{ color: '#52c41a', fontSize: '12px' }}>已加入</Text>
            </div>
          )}
        </Card>
      );
    }

    return null;
  };

  return (
    <>
      <div className={`telegram-link-preview-wrapper ${className}`}>
        {renderPreviewContent()}
      </div>
      
      {/* 外部群组详细预览模态框 */}
      <ExternalGroupPreview
        url={url}
        visible={showExternalPreview}
        onClose={() => setShowExternalPreview(false)}
        onJoinGroup={(groupInfo) => {
          console.log('TelegramLinkPreview - group joined from external preview:', groupInfo);
          setGroupPreview(prev => prev ? { ...prev, is_joined: true } : null);
          notification.success(`已成功加入群组: ${groupInfo.title}`);
        }}
      />
    </>
  );
};

export default TelegramLinkPreview;