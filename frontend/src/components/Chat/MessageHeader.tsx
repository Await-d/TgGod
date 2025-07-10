import React from 'react';
import { Space, Button, Typography, Tag, Avatar, Tooltip } from 'antd';
import { 
  ReloadOutlined, 
  SyncOutlined, 
  SettingOutlined, 
  TeamOutlined,
  CheckCircleOutlined,
  PauseCircleOutlined 
} from '@ant-design/icons';
import { TelegramGroup } from '../../types';

const { Title, Text } = Typography;

interface MessageHeaderProps {
  group: TelegramGroup;
  onRefresh: () => void;
  onSync: () => void;
  loading?: boolean;
  isMobile?: boolean;
}

const MessageHeader: React.FC<MessageHeaderProps> = ({
  group,
  onRefresh,
  onSync,
  loading = false,
  isMobile = false
}) => {
  
  // 获取群组头像
  const getGroupAvatar = () => {
    const firstChar = group.title.charAt(0).toUpperCase();
    return (
      <Avatar 
        size={isMobile ? 32 : 40} 
        style={{ 
          backgroundColor: '#1890ff',
          color: 'white',
          fontWeight: 'bold'
        }}
      >
        {firstChar}
      </Avatar>
    );
  };

  // 获取状态图标
  const getStatusIcon = () => {
    if (group.is_active) {
      return (
        <Tooltip title="群组活跃">
          <CheckCircleOutlined style={{ color: '#52c41a' }} />
        </Tooltip>
      );
    } else {
      return (
        <Tooltip title="群组暂停">
          <PauseCircleOutlined style={{ color: '#ff4d4f' }} />
        </Tooltip>
      );
    }
  };

  return (
    <div className="message-header">
      {/* 左侧群组信息 */}
      <div className="header-group-info">
        {getGroupAvatar()}
        <div className="group-details">
          <div className="group-title">
            <Title level={isMobile ? 5 : 4} style={{ margin: 0 }}>
              {group.title}
            </Title>
            {getStatusIcon()}
          </div>
          
          <div className="group-meta">
            <Space size="small" wrap>
              <Text type="secondary">@{group.username}</Text>
              
              <div className="member-info">
                <TeamOutlined style={{ marginRight: 4 }} />
                <Text type="secondary">{group.member_count?.toLocaleString() || 0} 成员</Text>
              </div>
              
              <Tag 
                color={group.is_active ? 'success' : 'error'}
              >
                {group.is_active ? '活跃' : '暂停'}
              </Tag>
            </Space>
          </div>
          
          {group.description && !isMobile && (
            <div className="group-description">
              <Text type="secondary" ellipsis>
                {group.description}
              </Text>
            </div>
          )}
        </div>
      </div>

      {/* 右侧操作按钮 */}
      <div className="header-actions">
        <Space size="small">
          <Tooltip title="刷新消息">
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={onRefresh}
              loading={loading}
              size={isMobile ? 'small' : 'middle'}
            />
          </Tooltip>
          
          <Tooltip title="同步消息">
            <Button
              type="text"
              icon={<SyncOutlined />}
              onClick={onSync}
              size={isMobile ? 'small' : 'middle'}
            />
          </Tooltip>
          
          {!isMobile && (
            <Tooltip title="群组设置">
              <Button
                type="text"
                icon={<SettingOutlined />}
                size="middle"
              />
            </Tooltip>
          )}
        </Space>
      </div>
    </div>
  );
};

export default MessageHeader;