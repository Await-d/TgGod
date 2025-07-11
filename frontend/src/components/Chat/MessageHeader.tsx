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
      // 这里暂时用空数组，因为后端可能还没有实现获取置顶消息的API
      setPinnedMessages([]);
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
        size={isMobile ? 32 : 36} 
        style={{ 
          backgroundColor: getAvatarColor(group.title),
          color: 'white',
          fontWeight: 'bold',
          fontSize: isMobile ? '14px' : '16px'
        }}
      >
        {firstChar}
      </Avatar>
    );
  };

  return (
    <div className="message-header">
      {/* 群组基本信息 */}
      <Card 
        size="small" 
        style={{ 
          marginBottom: 8,
          borderRadius: 6,
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
        }}
        bodyStyle={{ padding: '12px 16px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* 群组头像 */}
          {getGroupAvatar()}
          
          {/* 群组信息 */}
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
              <Title level={5} style={{ margin: 0, fontSize: '16px' }}>
                {group.title}
              </Title>
              <Tag 
                color={group.is_active ? 'success' : 'error'} 
                icon={group.is_active ? <CheckCircleOutlined /> : <PauseCircleOutlined />}
                style={{ fontSize: '10px' }}
              >
                {group.is_active ? '活跃' : '暂停'}
              </Tag>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                <TeamOutlined style={{ marginRight: 4 }} />
                {group.member_count?.toLocaleString() || 0} 成员
              </Text>
              {group.username && (
                <Text type="secondary" style={{ fontSize: '11px' }}>
                  @{group.username}
                </Text>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* 群组统计信息 - 紧凑布局 */}
      {groupStats && (
        <Card 
          size="small" 
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <MessageOutlined />
              <span style={{ fontSize: '14px' }}>消息统计</span>
            </div>
          }
          style={{ 
            marginBottom: 12,
            borderRadius: 6,
            boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
          }}
          bodyStyle={{ padding: '12px 16px' }}
          loading={loadingStats}
        >
          <Row gutter={[8, 8]}>
            {/* 第一行：主要统计 */}
            <Col span={isMobile ? 6 : 4}>
              <Statistic
                title="总数"
                value={groupStats.total_messages}
                valueStyle={{ color: '#1890ff', fontSize: '16px' }}
                className="compact-statistic"
              />
            </Col>
            <Col span={isMobile ? 6 : 4}>
              <Statistic
                title="文本"
                value={groupStats.text_messages}
                valueStyle={{ color: '#52c41a', fontSize: '16px' }}
                className="compact-statistic"
              />
            </Col>
            <Col span={isMobile ? 6 : 4}>
              <Statistic
                title="媒体"
                value={groupStats.media_messages}
                valueStyle={{ color: '#faad14', fontSize: '16px' }}
                className="compact-statistic"
              />
            </Col>
            <Col span={isMobile ? 6 : 4}>
              <Statistic
                title="图片"
                value={groupStats.photo_messages}
                valueStyle={{ color: '#13c2c2', fontSize: '16px' }}
                className="compact-statistic"
              />
            </Col>
            {!isMobile && (
              <>
                <Col span={4}>
                  <Statistic
                    title="视频"
                    value={groupStats.video_messages}
                    valueStyle={{ color: '#722ed1', fontSize: '16px' }}
                    className="compact-statistic"
                  />
                </Col>
                <Col span={4}>
                  <Statistic
                    title="转发"
                    value={groupStats.forwarded_messages}
                    valueStyle={{ color: '#fa8c16', fontSize: '16px' }}
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
            marginBottom: 8,
            borderRadius: 6,
            borderColor: '#faad14',
            backgroundColor: '#fffbf0'
          }}
          bodyStyle={{ padding: '8px 12px' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <PushpinOutlined style={{ color: '#faad14', fontSize: '14px' }} />
            <div style={{ flex: 1 }}>
              <Text strong style={{ color: '#faad14', fontSize: '12px' }}>置顶消息</Text>
              <div style={{ marginTop: 2 }}>
                <Text ellipsis style={{ display: 'block', maxWidth: '200px', fontSize: '12px' }}>
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
                    style={{ fontSize: '10px' }}
                  />
                  <Text type="secondary" style={{ fontSize: '10px' }}>
                    {currentPinnedIndex + 1}/{pinnedMessages.length}
                  </Text>
                  <Button 
                    type="text" 
                    size="small" 
                    icon={<RightOutlined />} 
                    onClick={handlePinnedNext}
                    style={{ fontSize: '10px' }}
                  />
                </>
              )}
              <Button 
                type="text" 
                size="small" 
                onClick={handleJumpToPinned}
                style={{ fontSize: '10px' }}
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