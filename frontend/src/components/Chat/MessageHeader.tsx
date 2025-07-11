import React, { useState, useCallback, useEffect } from 'react';
import { Space, Button, Typography, Tag, Avatar, Tooltip, Card, Row, Col, Statistic, Spin } from 'antd';
import { 
  TeamOutlined,
  CheckCircleOutlined,
  PauseCircleOutlined,
  PushpinOutlined,
  LeftOutlined,
  RightOutlined,
  MessageOutlined,
  FileImageOutlined,
  VideoCameraOutlined,
  FileTextOutlined,
  AudioOutlined,
  ShareAltOutlined,
  HeartOutlined
} from '@ant-design/icons';
import { TelegramGroup, TelegramMessage } from '../../types';
import { messageApi, telegramApi } from '../../services/apiService';
import './MessageArea.css'; // 导入CSS样式

const { Title, Text } = Typography;

interface MessageHeaderProps {
  group: TelegramGroup;
  onJumpToMessage?: (messageId: number) => void;
  onRefresh?: () => Promise<void>;
  onSync?: () => Promise<void>;
  loading?: boolean;
  isMobile?: boolean;
}

const MessageHeader: React.FC<MessageHeaderProps> = ({
  group,
  onJumpToMessage,
  onRefresh,
  onSync,
  loading = false,
  isMobile = false
}) => {
  
  // 置顶消息状态
  const [pinnedMessages, setPinnedMessages] = useState<TelegramMessage[]>([]);
  const [currentPinnedIndex, setCurrentPinnedIndex] = useState(0);
  const [loadingPinned, setLoadingPinned] = useState(false);
  
  // 群组统计信息状态
  const [groupStats, setGroupStats] = useState<any>(null);
  const [loadingStats, setLoadingStats] = useState(false);

  // 获取置顶消息
  const fetchPinnedMessages = useCallback(async () => {
    if (!group) return;
    
    setLoadingPinned(true);
    try {
      const pinnedMessages = await messageApi.getPinnedMessages(group.id);
      setPinnedMessages(pinnedMessages || []);
      setCurrentPinnedIndex(0);
    } catch (error: any) {
      console.error('获取置顶消息失败:', error);
      setPinnedMessages([]);
    } finally {
      setLoadingPinned(false);
    }
  }, [group]);

  // 获取群组统计信息
  const fetchGroupStats = useCallback(async () => {
    if (!group) return;
    
    setLoadingStats(true);
    try {
      const stats = await telegramApi.getGroupStats(group.id);
      setGroupStats(stats);
    } catch (error: any) {
      console.error('获取群组统计信息失败:', error);
      setGroupStats(null);
    } finally {
      setLoadingStats(false);
    }
  }, [group]);

  // 当群组变化时获取信息
  useEffect(() => {
    if (group) {
      fetchPinnedMessages();
      fetchGroupStats();
    }
  }, [group, fetchPinnedMessages, fetchGroupStats]);

  // 切换置顶消息
  const handlePinnedPrevious = () => {
    setCurrentPinnedIndex(prev => prev > 0 ? prev - 1 : pinnedMessages.length - 1);
  };

  const handlePinnedNext = () => {
    setCurrentPinnedIndex(prev => prev < pinnedMessages.length - 1 ? prev + 1 : 0);
  };

  // 跳转到置顶消息
  const handleJumpToPinned = () => {
    if (pinnedMessages.length > 0 && onJumpToMessage) {
      onJumpToMessage(pinnedMessages[currentPinnedIndex].message_id);
    }
  };

  // 获取群组头像
  const getGroupAvatar = () => {
    const firstChar = group.title.charAt(0).toUpperCase();
    const getAvatarColor = (name: string) => {
      const colors = [
        '#f56a00', '#7265e6', '#ffbf00', '#00a2ae', 
        '#87d068', '#1890ff', '#722ed1', '#eb2f96'
      ];
      let hash = 0;
      for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
      }
      return colors[Math.abs(hash) % colors.length];
    };
    
    return (
      <Avatar 
        size={isMobile ? 36 : 42} 
        style={{ 
          backgroundColor: getAvatarColor(group.title),
          color: 'white',
          fontWeight: 'bold',
          fontSize: isMobile ? '14px' : '18px'
        }}
      >
        {firstChar}
      </Avatar>
    );
  };

  return (
    <div className="message-header">
      {/* 群组基本信息 - 无卡片包裹 */}
      <div style={{ 
        marginBottom: 8,
        padding: '12px 16px',
        background: 'transparent'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* 群组头像 */}
          {getGroupAvatar()}
          
          {/* 群组信息 */}
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <Title level={4} style={{ margin: 0, fontSize: '18px', lineHeight: '24px', color: '#262626' }}>
                {group.title}
              </Title>
              <Tag 
                color={group.is_active ? 'success' : 'error'} 
                icon={group.is_active ? <CheckCircleOutlined /> : <PauseCircleOutlined />}
                style={{ fontSize: '11px', padding: '2px 6px', lineHeight: '16px' }}
              >
                {group.is_active ? '活跃' : '暂停'}
              </Tag>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Text type="secondary" style={{ fontSize: '13px', lineHeight: '18px' }}>
                <TeamOutlined style={{ marginRight: 4, fontSize: '12px' }} />
                {group.member_count?.toLocaleString() || 0} 成员
              </Text>
              {group.username && (
                <Text type="secondary" style={{ fontSize: '12px', lineHeight: '18px' }}>
                  @{group.username}
                </Text>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 群组统计信息 - 紧凑布局 */}
      {groupStats && (
        <Card 
          size="small" 
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <MessageOutlined style={{ fontSize: '12px' }} />
              <span style={{ fontSize: '12px' }}>消息统计</span>
            </div>
          }
          style={{ 
            marginBottom: 6,
            borderRadius: 4,
            boxShadow: '0 1px 2px rgba(0,0,0,0.08)'
          }}
          bodyStyle={{ padding: '8px 12px' }}
          headStyle={{ padding: '6px 12px', minHeight: '32px' }}
          loading={loadingStats}
        >
          <Row gutter={[6, 6]}>
            {/* 第一行：主要统计 */}
            <Col span={isMobile ? 6 : 4}>
              <Statistic
                title="总数"
                value={groupStats.total_messages}
                valueStyle={{ color: '#1890ff', fontSize: '14px' }}
                className="compact-statistic"
              />
            </Col>
            <Col span={isMobile ? 6 : 4}>
              <Statistic
                title="文本"
                value={groupStats.text_messages}
                valueStyle={{ color: '#52c41a', fontSize: '14px' }}
                className="compact-statistic"
              />
            </Col>
            <Col span={isMobile ? 6 : 4}>
              <Statistic
                title="媒体"
                value={groupStats.media_messages}
                valueStyle={{ color: '#faad14', fontSize: '14px' }}
                className="compact-statistic"
              />
            </Col>
            <Col span={isMobile ? 6 : 4}>
              <Statistic
                title="图片"
                value={groupStats.photo_messages}
                valueStyle={{ color: '#13c2c2', fontSize: '14px' }}
                className="compact-statistic"
              />
            </Col>
            {!isMobile && (
              <>
                <Col span={4}>
                  <Statistic
                    title="视频"
                    value={groupStats.video_messages}
                    valueStyle={{ color: '#722ed1', fontSize: '14px' }}
                    className="compact-statistic"
                  />
                </Col>
                <Col span={4}>
                  <Statistic
                    title="转发"
                    value={groupStats.forwarded_messages}
                    valueStyle={{ color: '#fa8c16', fontSize: '14px' }}
                    className="compact-statistic"
                  />
                </Col>
              </>
            )}
          </Row>
        </Card>
      )}

      {/* 置顶消息 */}
      {pinnedMessages.length > 0 && (
        <Card 
          size="small"
          style={{ 
            marginBottom: 6,
            borderRadius: 4,
            borderColor: '#faad14',
            backgroundColor: '#fffbf0'
          }}
          bodyStyle={{ padding: '6px 10px' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <PushpinOutlined style={{ color: '#faad14', fontSize: '12px' }} />
            <div style={{ flex: 1 }}>
              <Text strong style={{ color: '#faad14', fontSize: '11px' }}>置顶消息</Text>
              <div style={{ marginTop: 1 }}>
                <Text ellipsis style={{ display: 'block', maxWidth: '200px', fontSize: '11px' }}>
                  {pinnedMessages[currentPinnedIndex]?.text || '媒体消息'}
                </Text>
              </div>
            </div>
            
            <Space size="small">
              {pinnedMessages.length > 1 && (
                <>
                  <Button 
                    type="text" 
                    size="small" 
                    icon={<LeftOutlined />} 
                    onClick={handlePinnedPrevious}
                    style={{ fontSize: '9px', padding: '2px 4px' }}
                  />
                  <Text type="secondary" style={{ fontSize: '9px' }}>
                    {currentPinnedIndex + 1}/{pinnedMessages.length}
                  </Text>
                  <Button 
                    type="text" 
                    size="small" 
                    icon={<RightOutlined />} 
                    onClick={handlePinnedNext}
                    style={{ fontSize: '9px', padding: '2px 4px' }}
                  />
                </>
              )}
              <Button 
                type="text" 
                size="small" 
                onClick={handleJumpToPinned}
                style={{ fontSize: '9px', padding: '2px 6px' }}
              >
                跳转
              </Button>
            </Space>
          </div>
        </Card>
      )}
    </div>
  );
};

export default MessageHeader;