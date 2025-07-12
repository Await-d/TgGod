import React from 'react';
import { Button, Progress, Space, Typography, Tooltip } from 'antd';
import {
  DownloadOutlined,
  ReloadOutlined,
  CloseOutlined,
  FileImageOutlined,
  VideoCameraOutlined,
  AudioOutlined,
  FileTextOutlined,
  WarningOutlined
} from '@ant-design/icons';
import { MediaDownloadStatus } from '../../hooks/useMediaDownload';
import './MediaDownloadOverlay.css';

const { Text } = Typography;

interface MediaDownloadOverlayProps {
  mediaType: 'photo' | 'video' | 'audio' | 'document' | 'voice';
  downloadStatus: MediaDownloadStatus;
  fileName?: string;
  fileSize?: number;
  isLoading?: boolean;
  onDownload: () => void;
  onRetry: () => void;
  onCancel?: () => void;
  className?: string;
}

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
};

// 获取媒体类型图标
const getMediaIcon = (mediaType: string) => {
  switch (mediaType) {
    case 'photo': return <FileImageOutlined />;
    case 'video': return <VideoCameraOutlined />;
    case 'audio':
    case 'voice': return <AudioOutlined />;
    case 'document': return <FileTextOutlined />;
    default: return <FileTextOutlined />;
  }
};

// 获取媒体类型文本
const getMediaTypeText = (mediaType: string) => {
  switch (mediaType) {
    case 'photo': return '图片';
    case 'video': return '视频';
    case 'audio': return '音频';
    case 'voice': return '语音';
    case 'document': return '文档';
    default: return '文件';
  }
};

const MediaDownloadOverlay: React.FC<MediaDownloadOverlayProps> = ({
  mediaType,
  downloadStatus,
  fileName,
  fileSize,
  isLoading,
  onDownload,
  onRetry,
  onCancel,
  className
}) => {
  const { status, progress, error } = downloadStatus;

  // 如果已下载，不显示遮罩
  if (status === 'downloaded') {
    return null;
  }

  const renderContent = () => {
    switch (status) {
      case 'not_downloaded':
        return (
          <div className="download-overlay-content">
            <div className="media-icon">
              {getMediaIcon(mediaType)}
            </div>
            <div className="media-info">
              <Text className="media-type">{getMediaTypeText(mediaType)}</Text>
              {fileName && <Text className="file-name">{fileName}</Text>}
              {fileSize && <Text className="file-size">{formatFileSize(fileSize)}</Text>}
            </div>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              loading={isLoading}
              onClick={onDownload}
              size="large"
              className="download-button"
            >
              下载{getMediaTypeText(mediaType)}
            </Button>
          </div>
        );

      case 'downloading':
        return (
          <div className="download-overlay-content downloading">
            <div className="progress-container">
              <Progress
                type="circle"
                percent={Math.round(progress)}
                size={80}
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
                trailColor="#f0f0f0"
              />
            </div>
            <div className="download-info">
              <Text className="download-text">正在下载{getMediaTypeText(mediaType)}...</Text>
              {fileName && <Text className="file-name">{fileName}</Text>}
              {fileSize && (
                <Text className="file-size">
                  {formatFileSize(Math.round(fileSize * progress / 100))} / {formatFileSize(fileSize)}
                </Text>
              )}
            </div>
            {onCancel && (
              <Button
                type="text"
                icon={<CloseOutlined />}
                onClick={onCancel}
                className="cancel-button"
                size="small"
              >
                取消
              </Button>
            )}
          </div>
        );

      case 'download_failed':
        return (
          <div className="download-overlay-content failed">
            <div className="error-icon">
              <WarningOutlined />
            </div>
            <div className="error-info">
              <Text className="error-title">下载失败</Text>
              {error && <Text className="error-message">{error}</Text>}
              {fileName && <Text className="file-name">{fileName}</Text>}
            </div>
            <Space>
              <Button
                type="primary"
                icon={<ReloadOutlined />}
                onClick={onRetry}
                size="large"
                className="retry-button"
              >
                重试下载
              </Button>
              {onCancel && (
                <Button
                  type="default"
                  icon={<CloseOutlined />}
                  onClick={onCancel}
                  size="large"
                >
                  取消
                </Button>
              )}
            </Space>
          </div>
        );

      case 'file_missing':
        return (
          <div className="download-overlay-content missing">
            <div className="error-icon">
              <WarningOutlined />
            </div>
            <div className="error-info">
              <Text className="error-title">文件丢失</Text>
              <Text className="error-message">本地文件已丢失，需要重新下载</Text>
              {fileName && <Text className="file-name">{fileName}</Text>}
            </div>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={onRetry}
              size="large"
              className="redownload-button"
            >
              重新下载
            </Button>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className={`media-download-overlay ${className || ''} ${status}`}>
      {renderContent()}
    </div>
  );
};

export default MediaDownloadOverlay;