import React, { memo, useCallback } from 'react';
import { Image, Button, Typography } from 'antd';
import {
  DownloadOutlined,
  FileOutlined,
  PlayCircleOutlined,
  PictureOutlined,
  FileTextOutlined,
  AudioOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import styles from './MessageItem.module.css';

const { Text } = Typography;

export interface Message {
  id: string;
  type: 'text' | 'image' | 'video' | 'file' | 'audio';
  content: string;
  sender: string;
  timestamp: Date;
  mediaUrl?: string;
  thumbnailUrl?: string;
  fileSize?: number;
  fileName?: string;
  duration?: number;
}

interface MessageItemProps {
  message: Message;
  onClick?: (message: Message) => void;
  onDownload?: (message: Message) => void;
  isSelected?: boolean;
  className?: string;
}

// Format file size
const formatFileSize = (bytes?: number): string => {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
};

// Format duration
const formatDuration = (seconds?: number): string => {
  if (!seconds) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

// Get file icon by type
const getFileIcon = (fileName?: string) => {
  if (!fileName) return <FileOutlined />;
  const ext = fileName.split('.').pop()?.toLowerCase();
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext || '')) return <PictureOutlined />;
  if (['mp4', 'avi', 'mov', 'mkv'].includes(ext || '')) return <PlayCircleOutlined />;
  if (['mp3', 'wav', 'ogg', 'flac'].includes(ext || '')) return <AudioOutlined />;
  if (['txt', 'doc', 'docx', 'pdf'].includes(ext || '')) return <FileTextOutlined />;
  return <FileOutlined />;
};

const MessageItem: React.FC<MessageItemProps> = memo(({
  message,
  onClick,
  onDownload,
  isSelected,
  className
}) => {
  const handleClick = useCallback(() => {
    onClick?.(message);
  }, [onClick, message]);

  const handleDownload = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onDownload?.(message);
  }, [onDownload, message]);

  const renderContent = () => {
    switch (message.type) {
      case 'image':
        return (
          <div className={styles.imageContent}>
            <Image
              src={message.thumbnailUrl || message.mediaUrl}
              alt={message.content}
              preview={{
                src: message.mediaUrl
              }}
              className={styles.image}
              fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mN8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
            />
            {message.content && (
              <Text className={styles.imageCaption}>{message.content}</Text>
            )}
          </div>
        );

      case 'video':
        return (
          <div className={styles.videoContent}>
            <div className={styles.videoThumbnail}>
              {message.thumbnailUrl ? (
                <img src={message.thumbnailUrl} alt="Video thumbnail" />
              ) : (
                <div className={styles.videoPlaceholder}>
                  <PlayCircleOutlined className={styles.playIcon} />
                </div>
              )}
              {message.duration && (
                <span className={styles.duration}>
                  {formatDuration(message.duration)}
                </span>
              )}
            </div>
            {message.content && (
              <Text className={styles.videoCaption}>{message.content}</Text>
            )}
          </div>
        );

      case 'file':
        return (
          <div className={styles.fileContent}>
            <div className={styles.fileIcon}>
              {getFileIcon(message.fileName)}
            </div>
            <div className={styles.fileInfo}>
              <Text className={styles.fileName} ellipsis>
                {message.fileName || 'Unknown file'}
              </Text>
              <Text className={styles.fileSize} type="secondary">
                {formatFileSize(message.fileSize)}
              </Text>
            </div>
            <Button
              type="text"
              icon={<DownloadOutlined />}
              onClick={handleDownload}
              className={styles.downloadBtn}
            />
          </div>
        );

      case 'audio':
        return (
          <div className={styles.audioContent}>
            <AudioOutlined className={styles.audioIcon} />
            <div className={styles.audioInfo}>
              <Text className={styles.audioName}>
                {message.fileName || 'Audio message'}
              </Text>
              <Text className={styles.audioDuration} type="secondary">
                {formatDuration(message.duration)}
              </Text>
            </div>
          </div>
        );

      case 'text':
      default:
        return (
          <Text className={styles.textContent}>{message.content}</Text>
        );
    }
  };

  return (
    <div
      className={`${styles.messageItem} ${isSelected ? styles.selected : ''} ${className || ''}`}
      onClick={handleClick}
    >
      <div className={styles.messageHeader}>
        <Text strong className={styles.sender}>
          {message.sender}
        </Text>
        <Text type="secondary" className={styles.timestamp}>
          {dayjs(message.timestamp).format('HH:mm')}
        </Text>
      </div>
      <div className={styles.messageBody}>
        {renderContent()}
      </div>
    </div>
  );
});

MessageItem.displayName = 'MessageItem';

export default MessageItem;
