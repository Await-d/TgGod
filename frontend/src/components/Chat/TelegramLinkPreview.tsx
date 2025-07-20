import React, { useState, useEffect } from 'react';
import { Card, Button, Avatar, Typography, Space, message as notification, Spin } from 'antd';
import { 
  TeamOutlined, 
  UserOutlined, 
  LinkOutlined, 
  RightOutlined,
  PlusOutlined,
  CheckOutlined
} from '@ant-design/icons';
import { TelegramGroup } from '../../types';
import { telegramApi } from '../../services/apiService';
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
        setGroupPreview(response);
      }
    } catch (error: any) {
      console.error('Failed to fetch group preview:', error);
      notification.error('无法获取群组信息: ' + (error.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  // 加入群组
  const handleJoinGroup = async () => {
    if (!linkInfo || !groupPreview) return;
    
    setJoining(true);
    try {
      let response;
      
      if (linkInfo.username) {
        // 加入公开群组
        response = await telegramApi.joinGroup(linkInfo.username);
      } else if (linkInfo.inviteHash) {
        // 通过邀请链接加入
        response = await telegramApi.joinGroupByInvite(linkInfo.inviteHash);
      }
      
      if (response) {
        notification.success('成功加入群组！');
        setGroupPreview(prev => prev ? { ...prev, is_joined: true } : null);
      }
    } catch (error: any) {
      console.error('Failed to join group:', error);
      notification.error('加入群组失败: ' + (error.message || '未知错误'));
    } finally {
      setJoining(false);
    }
  };

  // 跳转到群组
  const handleJumpToGroup = () => {
    if (groupPreview && groupPreview.is_joined && onJumpToGroup) {
      onJumpToGroup(groupPreview.id);
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

      if (!groupPreview) {
        return (
          <Card size="small" className="telegram-link-preview error">
            <div className="preview-content">
              <div className="preview-icon">
                <Avatar icon={<TeamOutlined />} style={{ backgroundColor: '#ff4d4f' }} />
              </div>
              <div className="preview-info">
                <Title level={5} style={{ margin: 0 }}>群组信息获取失败</Title>
                <Text type="secondary">无法获取群组详情</Text>
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
              {groupPreview.is_joined ? (
                <Button 
                  type="primary" 
                  size="small"
                  icon={<RightOutlined />}
                  onClick={handleJumpToGroup}
                  disabled={!onJumpToGroup}
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
                >
                  加入群组
                </Button>
              )}
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
    <div className={`telegram-link-preview-wrapper ${className}`}>
      {renderPreviewContent()}
    </div>
  );
};

export default TelegramLinkPreview;