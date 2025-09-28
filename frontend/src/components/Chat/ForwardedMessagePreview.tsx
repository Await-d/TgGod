import React, { useState, useCallback } from 'react';
import { Space, Tag, Button, Tooltip, message as antMessage, Badge, Modal } from 'antd';
import {
  ShareAltOutlined,
  MessageOutlined,
  UserOutlined,
  ClockCircleOutlined,
  RightOutlined,
  TeamOutlined,
  SoundOutlined,
  SearchOutlined,
  HistoryOutlined,
  EyeOutlined
} from '@ant-design/icons';
import { TelegramMessage } from '../../types';
import { telegramApi, messageApi } from '../../services/apiService';
import styles from './ForwardedMessagePreview.module.css';

interface ForwardedMessagePreviewProps {
  message: TelegramMessage;

  onJumpToGroup?: (groupId: number) => void;
  onJumpToMessage?: (messageId: number) => void;
  className?: string;
  compact?: boolean;
  showOriginalContent?: boolean;
  isMobile?: boolean;
}

const ForwardedMessagePreview: React.FC<ForwardedMessagePreviewProps> = ({
  message,
  onJumpToGroup,
  onJumpToMessage,
  className = '',
  compact = false,
  showOriginalContent = true,
  isMobile = false
}) => {
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [foundGroupId, setFoundGroupId] = useState<number | null>(null);
  // const [foundMessageId, setFoundMessageId] = useState<number | null>(null);
  const [searching, setSearching] = useState(false);

  const [jumpHistoryVisible, setJumpHistoryVisible] = useState(false);
  const [jumpHistory, setJumpHistory] = useState<Array<{ type: string, id: number, title?: string }>>([]);
  const [previewModalVisible, setPreviewModalVisible] = useState(false);

  // 跳转到转发来源群组
  const handleJumpToSourceGroup = useCallback(async () => {
    if (!message.forwarded_from_id || message.forwarded_from_type === 'user') {
      antMessage.info('无法跳转到用户私聊');
      return;
    }

    if (!onJumpToGroup) {
      antMessage.warning('跳转功能不可用');
      return;
    }

    setLoading(true);
    try {
      // 查找对应的群组
      const group = await telegramApi.searchGroupByTelegramId(message.forwarded_from_id);
      if (group) {
        // 保存找到的群组ID
        setFoundGroupId(group.id);

        // 将当前跳转添加到历史记录
        setJumpHistory(prev => [...prev, {
          type: message.forwarded_from_type === 'channel' ? '频道' : '群组',
          id: group.id,
          title: group.title
        }]);

        onJumpToGroup(group.id);
        antMessage.success(`跳转到${message.forwarded_from_type === 'channel' ? '频道' : '群组'}：${group.title}`);
      } else {
        antMessage.warning('未找到对应的群组，可能未加入该群组');
      }
    } catch (error: any) {
      console.error('跳转群组失败:', error);
      antMessage.error('跳转失败');
    } finally {
      setLoading(false);
    }
  }, [message.forwarded_from_id, message.forwarded_from_type, onJumpToGroup]);

  // 查找和跳转到原始消息
  const findAndJumpToOriginalMessage = useCallback(async () => {
    // 确保有足够的信息
    if (!foundGroupId || !message.forwarded_date || !onJumpToMessage) {
      antMessage.info('无法定位原始消息');
      return;
    }

    setSearching(true);

    try {
      // 获取转发消息的发送日期
      const forwardedDate = new Date(message.forwarded_date);

      // 设置搜索范围（转发时间前后各10天）
      const startDate = new Date(forwardedDate);
      startDate.setDate(startDate.getDate() - 10);

      const endDate = new Date(forwardedDate);
      endDate.setDate(endDate.getDate() + 10);

      // 构建搜索参数
      const searchParams = {
        sender_username: message.forwarded_from_type === 'user' ? message.forwarded_from : undefined,
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
        // 如果有文本内容，可以用它来缩小搜索范围
        query: message.text && message.text.length > 10 ? message.text.substring(0, 20) : undefined,
        media_type: message.media_type
      };

      // 搜索消息
      const searchResponse = await messageApi.searchMessages(foundGroupId, searchParams);

      // 处理响应数据，确保我们有一个消息数组
      const searchResults = Array.isArray(searchResponse) ? searchResponse : [];

      if (searchResults.length > 0) {
        // 尝试找到最匹配的消息
        let bestMatch = searchResults[0];

        if (message.text) {
          // 如果有文本，寻找文本完全匹配的消息
          const exactMatch = searchResults.find(m => m.text === message.text);
          if (exactMatch) {
            bestMatch = exactMatch;
          }
        }

        // 保存找到的消息ID
        // setFoundMessageId(bestMatch.message_id);


        // 将当前跳转添加到历史记录
        setJumpHistory(prev => [...prev, {
          type: '消息',
          id: bestMatch.message_id,
          title: bestMatch.text ? bestMatch.text.substring(0, 20) + '...' : '媒体消息'
        }]);

        // 跳转到该消息
        onJumpToMessage(bestMatch.message_id);
        antMessage.success('已跳转到原始消息');

        return;
      }

      antMessage.info('未找到匹配的原始消息');

    } catch (error) {
      console.error('搜索原始消息失败:', error);
      antMessage.error('查找原始消息失败');
    } finally {
      setSearching(false);
    }
  }, [foundGroupId, message, onJumpToMessage]);

  // 获取转发来源类型图标
  const getForwardSourceIcon = () => {
    switch (message.forwarded_from_type) {
      case 'channel':
        return <SoundOutlined style={{ color: '#1890ff' }} />;
      case 'group':
        return <TeamOutlined style={{ color: '#52c41a' }} />;
      case 'user':
        return <UserOutlined style={{ color: '#8c8c8c' }} />;
      default:
        return <UserOutlined style={{ color: '#8c8c8c' }} />;
    }
  };

  // 获取转发来源类型名称
  const getForwardSourceTypeName = () => {
    switch (message.forwarded_from_type) {
      case 'channel':
        return '频道';
      case 'group':
        return '群组';
      case 'user':
        return '用户';
      default:
        return '未知来源';
    }
  };

  // 切换展开/收起
  const toggleExpanded = useCallback(() => {
    setExpanded(!expanded);
  }, [expanded]);

  // 打开/关闭跳转历史记录
  const toggleJumpHistory = useCallback(() => {
    setJumpHistoryVisible(!jumpHistoryVisible);
  }, [jumpHistoryVisible]);

  // 打开/关闭预览模态框
  const togglePreviewModal = useCallback(() => {
    setPreviewModalVisible(!previewModalVisible);
  }, [previewModalVisible]);

  // 从历史记录跳转
  const jumpToHistoryItem = useCallback((item: { type: string, id: number }) => {
    if (item.type === '消息' && onJumpToMessage) {
      onJumpToMessage(item.id);
      setJumpHistoryVisible(false);
    } else if ((item.type === '频道' || item.type === '群组') && onJumpToGroup) {
      onJumpToGroup(item.id);
      setJumpHistoryVisible(false);
    }
  }, [onJumpToMessage, onJumpToGroup]);

  // 格式化时间
  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // 渲染转发标识
  const renderForwardBadge = () => (
    <div className={styles.forwardBadge}>
      <ShareAltOutlined className={styles.icon} />
      <span>转发</span>
    </div>
  );

  // 渲染转发来源信息
  const renderForwardSource = () => (
    <div className={styles.forwardSource}>
      <Space size="small" wrap>
        {getForwardSourceIcon()}
        <span>
          转发自{getForwardSourceTypeName()}：{message.forwarded_from || '未知来源'}
        </span>
        {message.forwarded_date && (
          <Tag color="blue">
            <ClockCircleOutlined style={{ marginRight: 4 }} />
            {formatTime(message.forwarded_date)}
          </Tag>
        )}

        {/* 跳转到群组按钮 */}
        {message.forwarded_from_id && message.forwarded_from_type !== 'user' && (
          <Tooltip title={`跳转到${getForwardSourceTypeName()}`}>
            <Button
              type="text"
              size="small"
              icon={<RightOutlined />}
              onClick={handleJumpToSourceGroup}
              loading={loading}
              className={styles.jumpButton}
            >
              跳转群组
            </Button>
          </Tooltip>
        )}

        {/* 查找原始消息按钮 - 当已经找到群组ID时显示 */}
        {foundGroupId && onJumpToMessage && (
          <Tooltip title="查找原始消息">
            <Button
              type="text"
              size="small"
              icon={<SearchOutlined spin={searching} />}
              onClick={findAndJumpToOriginalMessage}
              loading={searching}
              className={styles.jumpButton}
            >
              查找原始消息
            </Button>
          </Tooltip>
        )}

        {/* 增强预览按钮 */}
        <Tooltip title="增强预览">
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={togglePreviewModal}
            className={styles.enhancedButton}
          >
            增强预览
          </Button>
        </Tooltip>

        {/* 查看跳转历史按钮 - 仅当有历史记录时显示 */}
        {jumpHistory.length > 0 && (
          <Tooltip title="查看跳转历史">
            <Badge count={jumpHistory.length} size="small">
              <Button
                type="text"
                size="small"
                icon={<HistoryOutlined />}
                onClick={toggleJumpHistory}
                className={styles.historyButton}
              >
                跳转历史
              </Button>
            </Badge>
          </Tooltip>
        )}

        {/* 内容预览按钮 */}
        {showOriginalContent && (message.text || message.media_type) && (
          <Tooltip title={expanded ? "收起内容" : "展开内容"}>
            <Button
              type="text"
              size="small"
              icon={<MessageOutlined />}
              onClick={toggleExpanded}
              className={styles.expandButton}
            >
              {expanded ? '收起' : '预览'}
            </Button>
          </Tooltip>
        )}
      </Space>
    </div>
  );

  // 渲染转发消息内容
  const renderForwardedContent = () => {
    if (!showOriginalContent || !expanded) return null;

    return (
      <div className={styles.forwardedContent}>
        <div className={styles.contentHeader}>
          <Space size="small">
            <MessageOutlined style={{ color: '#1890ff' }} />
            <span className={styles.contentLabel}>转发内容</span>
          </Space>
        </div>

        <div className={`${styles.contentBody} ${compact ? styles.compact : ''}`}>
          {message.text && (
            <div className={styles.textContent}>
              {message.text.length > 200 && compact
                ? `${message.text.substring(0, 200)}...`
                : message.text}
            </div>
          )}

          {message.media_type && (
            <div className={styles.mediaInfo}>
              <Tag color="green">
                {message.media_type.toUpperCase()}
              </Tag>
              {message.media_filename && (
                <span className={styles.filename}>
                  {message.media_filename}
                </span>
              )}
            </div>
          )}

          {message.sender_name && (
            <div className={styles.senderInfo}>
              <UserOutlined style={{ marginRight: 4 }} />
              原发送者：{message.sender_name}
            </div>
          )}
        </div>
      </div>
    );
  };

  // 如果不是转发消息，不显示
  if (!message.is_forwarded) {
    return null;
  }

  // 紧凑模式布局
  if (compact) {
    return (
      <div className={`${styles.forwardedPreview} ${styles.compact} ${className}`}>
        <div className={styles.forwardHeader}>
          {renderForwardBadge()}
          {renderForwardSource()}
        </div>
        {showOriginalContent && renderForwardedContent()}
      </div>
    );
  }

  // 渲染跳转历史记录
  const renderJumpHistoryModal = () => {
    return (
      <Modal
        title={<><HistoryOutlined /> 跳转历史记录</>}
        open={jumpHistoryVisible}
        onCancel={toggleJumpHistory}
        footer={null}
        width={350}
      >
        {jumpHistory.length > 0 ? (
          <div className={styles.jumpHistoryList}>
            {jumpHistory.map((item, index) => (
              <div
                key={index}
                className={styles.jumpHistoryItem}
                onClick={() => jumpToHistoryItem(item)}
              >
                <div className={styles.jumpHistoryIcon}>
                  {item.type === '消息' ? <MessageOutlined /> :
                    item.type === '频道' ? <SoundOutlined /> : <TeamOutlined />}
                </div>
                <div className={styles.jumpHistoryContent}>
                  <div className={styles.jumpHistoryType}>{item.type}</div>
                  <div className={styles.jumpHistoryTitle}>{item.title || `ID: ${item.id}`}</div>
                </div>
                <RightOutlined className={styles.jumpHistoryArrow} />
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.emptyHistory}>
            <p>暂无跳转历史记录</p>
          </div>
        )}
      </Modal>
    );
  };

  // 渲染增强预览模态框
  const renderPreviewModal = () => {
    return (
      <Modal
        title={<><EyeOutlined /> 转发消息内容预览</>}
        open={previewModalVisible}
        onCancel={togglePreviewModal}
        footer={null}
        width={520}
      >
        <div className={styles.previewModalContent}>
          <div className={styles.previewModalHeader}>
            <Space>
              {getForwardSourceIcon()}
              <span className={styles.previewModalTitle}>
                来源：{message.forwarded_from || '未知来源'}
                {message.forwarded_from_type && ` (${getForwardSourceTypeName()})`}
              </span>
            </Space>
            {message.forwarded_date && (
              <div className={styles.previewModalTime}>
                <ClockCircleOutlined /> {formatTime(message.forwarded_date)}
              </div>
            )}
          </div>

          <div className={styles.previewModalBody}>
            {message.text && (
              <div className={styles.previewModalText}>
                {message.text}
              </div>
            )}

            {message.media_type && (
              <div className={styles.previewModalMedia}>
                <div className={styles.mediaTypeTag}>
                  <Tag color="blue">{message.media_type.toUpperCase()}</Tag>
                </div>
                {message.media_filename && (
                  <div className={styles.mediaFilename}>
                    {message.media_filename}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className={styles.previewModalFooter}>
            <Space>
              {foundGroupId && (
                <Button
                  type="primary"
                  icon={<SearchOutlined />}
                  onClick={findAndJumpToOriginalMessage}
                  loading={searching}
                >
                  查找原始消息
                </Button>
              )}

              {message.forwarded_from_id && message.forwarded_from_type !== 'user' && (
                <Button
                  icon={<RightOutlined />}
                  onClick={handleJumpToSourceGroup}
                  loading={loading}
                >
                  跳转到{getForwardSourceTypeName()}
                </Button>
              )}
            </Space>
          </div>
        </div>
      </Modal>
    );
  };

  // 标准模式布局
  return (
    <div className={`${styles.forwardedPreview} ${className}`}>
      <div className={styles.forwardHeader}>
        {renderForwardBadge()}
        {renderForwardSource()}
      </div>

      {showOriginalContent && (
        <div className={styles.contentContainer}>
          {renderForwardedContent()}
        </div>
      )}

      {/* 添加跳转历史浮动按钮 */}
      {jumpHistory.length > 0 && (
        <div className={styles.historyFloatingButton} onClick={toggleJumpHistory}>
          <Badge count={jumpHistory.length} size="small">
            <Button shape="circle" icon={<HistoryOutlined />} size="small" />
          </Badge>
        </div>
      )}

      {/* 渲染跳转历史模态框 */}
      {renderJumpHistoryModal()}

      {/* 渲染预览模态框 */}
      {renderPreviewModal()}
    </div>
  );
};

export default ForwardedMessagePreview;