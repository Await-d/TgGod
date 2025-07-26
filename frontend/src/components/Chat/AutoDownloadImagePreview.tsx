import React, { useState } from 'react';
import { Image, Spin, Progress, Tag, Button, Tooltip } from 'antd';
import { DownloadOutlined, EyeOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { TelegramMessage } from '../../types';
import { useImageAutoDownload } from '../../hooks/useImageAutoDownload';

interface AutoDownloadImagePreviewProps {
  message: TelegramMessage;
  className?: string;
  maxAutoDownloadSize?: number; // 最大自动下载大小，默认2MB
  onPreview?: (imageUrl: string) => void;
  compact?: boolean;
}

const AutoDownloadImagePreview: React.FC<AutoDownloadImagePreviewProps> = ({
  message,
  className = '',
  maxAutoDownloadSize = 2 * 1024 * 1024, // 2MB
  onPreview,
  compact = false
}) => {
  const [imageError, setImageError] = useState(false);

  // 使用自动下载Hook
  const {
    isAutoDownloading,
    downloadProgress,
    downloadUrl,
    error,
    isEligibleForAutoDownload,
    fileSizeMB
  } = useImageAutoDownload(message, {
    maxSize: maxAutoDownloadSize,
    enabled: true
  });

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  };

  // 获取图片URL
  const getImageUrl = (): string | null => {
    if (downloadUrl) return downloadUrl;
    if (message.media_downloaded && message.media_path) {
      return message.media_path;
    }
    if (message.media_filename) {
      return `/api/media/download/${message.group_id}/${message.message_id}`;
    }
    return null;
  };

  const imageUrl = getImageUrl();
  const canShowImage = imageUrl && !imageError;

  // 手动下载处理
  const handleManualDownload = async () => {
    // 这里可以触发手动下载逻辑
    console.log('手动下载图片:', message.id);
  };

  // 预览处理
  const handlePreview = () => {
    if (imageUrl && onPreview) {
      onPreview(imageUrl);
    }
  };

  return (
    <div className={`auto-download-image-preview ${className}`}>
      {/* 图片容器 */}
      <div className="image-container" style={{
        position: 'relative',
        maxWidth: compact ? 200 : 300,
        maxHeight: compact ? 150 : 200,
        backgroundColor: '#f5f5f5',
        borderRadius: 8,
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        {/* 自动下载进行中 */}
        {isAutoDownloading && (
          <div style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.7)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 2
          }}>
            <Spin size="large" />
            <Progress
              percent={downloadProgress}
              size="small"
              status="active"
              style={{
                width: '80%',
                marginTop: 16,
                color: 'white'
              }}
            />
            <div style={{ color: 'white', marginTop: 8, fontSize: 12 }}>
              自动下载中... {downloadProgress}%
            </div>
          </div>
        )}

        {/* 显示图片 */}
        {canShowImage ? (
          <Image
            src={imageUrl}
            alt={message.media_filename || '图片'}
            style={{
              maxWidth: '100%',
              maxHeight: '100%',
              objectFit: 'cover'
            }}
            preview={{
              mask: (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <EyeOutlined />
                  <span>预览</span>
                </div>
              )
            }}
            onError={() => setImageError(true)}
            onClick={handlePreview}
          />
        ) : (
          /* 占位符或错误状态 */
          <div style={{
            width: '100%',
            height: compact ? 150 : 200,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#999',
            fontSize: compact ? 12 : 14
          }}>
            {error ? (
              <>
                <ExclamationCircleOutlined style={{ fontSize: 24, marginBottom: 8 }} />
                <div>自动下载失败</div>
                <div style={{ fontSize: 10, color: '#ff4d4f' }}>{error}</div>
                <Button
                  size="small"
                  type="primary"
                  icon={<DownloadOutlined />}
                  onClick={handleManualDownload}
                  style={{ marginTop: 8 }}
                >
                  手动下载
                </Button>
              </>
            ) : imageError ? (
              <>
                <ExclamationCircleOutlined style={{ fontSize: 24, marginBottom: 8 }} />
                <div>图片加载失败</div>
              </>
            ) : (
              <>
                <EyeOutlined style={{ fontSize: 24, marginBottom: 8 }} />
                <div>图片预览</div>
                {message.media_size && (
                  <div style={{ fontSize: 10 }}>
                    {formatFileSize(message.media_size)}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* 文件信息标签 */}
      <div style={{
        marginTop: 8,
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        flexWrap: 'wrap'
      }}>
        {/* 自动下载标签 */}
        {isEligibleForAutoDownload && (
          <Tag color="green">
            <DownloadOutlined style={{ marginRight: 2 }} />
            自动下载
          </Tag>
        )}

        {/* 文件大小标签 */}
        {message.media_size && (
          <Tag>
            {formatFileSize(message.media_size)}
          </Tag>
        )}

        {/* 下载状态标签 */}
        {message.media_downloaded && (
          <Tag color="blue">
            已下载
          </Tag>
        )}

        {/* 文件名 */}
        {message.media_filename && (
          <Tooltip title={message.media_filename}>
            <span style={{
              fontSize: 11,
              color: '#666',
              maxWidth: compact ? 150 : 200,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}>
              {message.media_filename}
            </span>
          </Tooltip>
        )}
      </div>
    </div>
  );
};

export default AutoDownloadImagePreview;