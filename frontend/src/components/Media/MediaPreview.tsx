import React, { useState, useEffect } from 'react';
import { 
  Modal, 
  Button, 
  Image, 
  message as antMessage, 
  Spin, 
  Space, 
  Typography, 
  Card, 
  Progress,
  Tooltip 
} from 'antd';
import { 
  DownloadOutlined, 
  EyeOutlined, 
  PlayCircleOutlined,
  FileImageOutlined,
  VideoCameraOutlined,
  FileTextOutlined,
  AudioOutlined,
  CloseOutlined
} from '@ant-design/icons';
import { TelegramMessage } from '../../types';
import { mediaApi } from '../../services/apiService';
import './MediaPreview.css';

const { Text } = Typography;

interface MediaPreviewProps {
  message: TelegramMessage;
  showPreview?: boolean;
  showDownload?: boolean;
  size?: 'small' | 'default' | 'large';
  className?: string;
}

const MediaPreview: React.FC<MediaPreviewProps> = ({
  message,
  showPreview = true,
  showDownload = true,
  size = 'default',
  className
}) => {
  const [previewVisible, setPreviewVisible] = useState(false);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [downloadStatus, setDownloadStatus] = useState<any>(null);
  const [downloadProgress, setDownloadProgress] = useState(0);

  // 获取媒体类型图标
  const getMediaIcon = (mediaType: string) => {
    const iconProps = { style: { fontSize: size === 'small' ? 16 : 20 } };
    switch (mediaType) {
      case 'photo': 
        return <FileImageOutlined {...iconProps} style={{ ...iconProps.style, color: '#52c41a' }} />;
      case 'video': 
        return <VideoCameraOutlined {...iconProps} style={{ ...iconProps.style, color: '#1890ff' }} />;
      case 'document': 
        return <FileTextOutlined {...iconProps} style={{ ...iconProps.style, color: '#faad14' }} />;
      case 'audio': 
        return <AudioOutlined {...iconProps} style={{ ...iconProps.style, color: '#722ed1' }} />;
      default: 
        return <FileTextOutlined {...iconProps} />;
    }
  };

  // 获取文件大小显示
  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  };

  // 下载媒体文件
  const handleDownload = async () => {
    if (!message.message_id) {
      antMessage.error('消息ID不存在');
      return;
    }

    setDownloadLoading(true);
    setDownloadProgress(0);

    try {
      // 开始下载
      const result = await mediaApi.downloadMedia(message.message_id);
      
      if (result.status === 'success') {
        antMessage.success('下载完成！');
        if (result.download_url) {
          // 如果有下载链接，直接下载
          const link = document.createElement('a');
          link.href = result.download_url;
          link.download = message.media_filename || `media_${message.message_id}`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }
      } else if (result.status === 'downloading') {
        antMessage.info('文件正在下载中...');
        // 开始轮询下载状态
        pollDownloadStatus();
      } else if (result.status === 'exists') {
        antMessage.success('文件已存在！');
        if (result.download_url) {
          // 直接下载已存在的文件
          const link = document.createElement('a');
          link.href = result.download_url;
          link.download = message.media_filename || `media_${message.message_id}`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }
      } else {
        antMessage.error(result.message || '下载失败');
      }
    } catch (error: any) {
      antMessage.error(`下载失败: ${error.message}`);
    } finally {
      setDownloadLoading(false);
    }
  };

  // 轮询下载状态
  const pollDownloadStatus = async () => {
    if (!message.message_id) return;

    try {
      const status = await mediaApi.getDownloadStatus(message.message_id);
      setDownloadStatus(status);

      if (status.progress) {
        setDownloadProgress(status.progress);
      }

      if (status.status === 'completed') {
        antMessage.success('下载完成！');
        if (status.download_url) {
          const link = document.createElement('a');
          link.href = status.download_url;
          link.download = message.media_filename || `media_${message.message_id}`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }
        setDownloadLoading(false);
      } else if (status.status === 'failed') {
        antMessage.error(`下载失败: ${status.error || '未知错误'}`);
        setDownloadLoading(false);
      } else if (status.status === 'downloading') {
        // 继续轮询
        setTimeout(pollDownloadStatus, 2000);
      }
    } catch (error: any) {
      console.error('获取下载状态失败:', error);
      setDownloadLoading(false);
    }
  };

  // 停止轮询
  useEffect(() => {
    return () => {
      // 组件卸载时清理
      setDownloadLoading(false);
    };
  }, []);

  // 如果不是媒体消息，不显示预览
  if (!message.media_type) {
    return null;
  }

  // 检查是否为可预览的媒体类型
  const isPreviewable = ['photo', 'video'].includes(message.media_type);

  return (
    <div className={`media-preview ${size} ${className || ''}`}>
      <Card 
        size="small" 
        className="media-preview-card"
        actions={[
          showPreview && isPreviewable && (
            <Tooltip title="预览" key="preview">
              <Button
                type="text"
                icon={message.media_type === 'video' ? <PlayCircleOutlined /> : <EyeOutlined />}
                onClick={() => setPreviewVisible(true)}
              />
            </Tooltip>
          ),
          showDownload && (
            <Tooltip title="下载" key="download">
              <Button
                type="text"
                icon={<DownloadOutlined />}
                loading={downloadLoading}
                onClick={handleDownload}
              />
            </Tooltip>
          ),
        ].filter(Boolean)}
      >
        <div className="media-info">
          <Space>
            {getMediaIcon(message.media_type)}
            <div className="media-details">
              <Text strong>{message.media_type}</Text>
              {message.media_filename && (
                <Text type="secondary" className="media-filename">
                  {message.media_filename}
                </Text>
              )}
              {message.media_size && (
                <Text type="secondary" className="media-size">
                  {formatFileSize(message.media_size)}
                </Text>
              )}
            </div>
          </Space>
        </div>

        {downloadLoading && downloadProgress > 0 && (
          <div className="download-progress">
            <Progress 
              percent={downloadProgress} 
              size="small" 
              status="active"
            />
            {downloadStatus && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                {downloadStatus.download_speed && `${formatFileSize(downloadStatus.download_speed)}/s`}
                {downloadStatus.estimated_time_remaining && ` - 剩余 ${Math.round(downloadStatus.estimated_time_remaining)}s`}
              </Text>
            )}
          </div>
        )}
      </Card>

      {/* 预览模态框 */}
      <Modal
        title={
          <Space>
            {getMediaIcon(message.media_type)}
            <span>媒体预览</span>
            {message.media_filename && (
              <Text type="secondary">- {message.media_filename}</Text>
            )}
          </Space>
        }
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="download" icon={<DownloadOutlined />} onClick={handleDownload} loading={downloadLoading}>
            下载
          </Button>,
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            关闭
          </Button>,
        ]}
        width="80%"
        style={{ maxWidth: 1000 }}
        centered
      >
        <div className="media-preview-content">
          {message.media_type === 'photo' && (message.media_download_url || message.media_thumbnail_path) && (
            <Image
              src={message.media_download_url || message.media_thumbnail_path}
              alt={message.media_filename || '图片'}
              width="100%"
              placeholder={
                <div className="image-placeholder">
                  <Spin size="large" />
                </div>
              }
              fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMIAAADDCAYAAADQvc6UAAABRWlDQ1BJQ0MgUHJvZmlsZQAAKJFjYGASSSwoyGFhYGDIzSspCnJ3UoiIjFJgf8LAwSDCIMogwMCcmFxc4BgQ4ANUwgCjUcG3awyMIPqyLsis7PPOq3QdDFcvjV3jOD1boQVTPQrgSkktTgbSf4A4LbmgqISBgTEFyFYuLykAsTuAbJEioKOA7DkgdjqEvQHEToKwj4DVhAQ5A9k3gGyB5IxEoBmML4BsnSQk8XQkNtReEOBxcfXxUQg1Mjc0dyHgXNJBSWpFCYh2zi+oLMpMzyhRcASGUqqCZ16yno6CkYGRAQMDKMwhqj/fAIcloxgHQqxAjIHBEugw5sUIsSQpBobtQPdLciLEVJYzMPBHMDBsayhILEqEO4DxG0txmrERhM29nYGBddr//5/DGRjYNRkY/l7////39v///y4Dmn+LgeHANwDrkl1AuO+pmgAAADhlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAAqACAAQAAAABAAAAwqADAAQAAAABAAAAwwAAAAD9b/HnAAAHlklEQVR4Ae3dP3Ik1RUG8O+L2hYSFRqYCZ9QaVx..."
            />
          )}

          {message.media_type === 'video' && (message.media_download_url || message.video?.file_path) && (
            <video
              src={message.media_download_url || message.video?.file_path}
              controls
              width="100%"
              style={{ maxHeight: '70vh' }}
            >
              您的浏览器不支持视频播放。
            </video>
          )}

          {!isPreviewable && (
            <div className="non-previewable">
              <div className="media-icon-large">
                {getMediaIcon(message.media_type)}
              </div>
              <Text>此类型文件不支持预览，可以下载查看</Text>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};

export default MediaPreview;