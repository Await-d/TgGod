import React, { useState, useEffect } from 'react';
import { 
  Modal, 
  Button, 
  Image, 
  Spin, 
  Space, 
  Typography, 
  Tooltip,
  Progress 
} from 'antd';
import { 
  DownloadOutlined, 
  ExpandOutlined, 
  PlayCircleOutlined,
  PauseCircleOutlined,
  FileImageOutlined,
  VideoCameraOutlined,
  FileTextOutlined,
  AudioOutlined
} from '@ant-design/icons';
import { TelegramMessage } from '../../types';
import { mediaApi } from '../../services/apiService';
import './InlineMediaPreview.css';

const { Text } = Typography;

interface InlineMediaPreviewProps {
  message: TelegramMessage;
  size?: 'small' | 'default' | 'large';
  className?: string;
  lazyLoad?: boolean;
  onClick?: () => void;
}

const InlineMediaPreview: React.FC<InlineMediaPreviewProps> = ({
  message,
  size = 'default',
  className,
  lazyLoad = true,
  onClick
}) => {
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [videoPlaying, setVideoPlaying] = useState(false);
  const [inView, setInView] = useState(!lazyLoad);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const videoRef = React.useRef<HTMLVideoElement>(null);

  // 检查元素是否在视口中
  useEffect(() => {
    if (!lazyLoad) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setInView(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );

    const currentElement = document.getElementById(`media-preview-${message.message_id}`);
    if (currentElement) {
      observer.observe(currentElement);
    }

    return () => {
      observer.disconnect();
    };
  }, [message.message_id, lazyLoad]);

  // 获取媒体类型图标
  const getMediaIcon = (mediaType: string) => {
    const iconProps = { style: { fontSize: size === 'small' ? 16 : 24 } };
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
  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (!message.message_id) return;

    setDownloadLoading(true);
    setDownloadProgress(0);

    try {
      const result = await mediaApi.downloadMedia(message.message_id);
      
      if (result.status === 'success' || result.status === 'exists') {
        if (result.download_url) {
          const link = document.createElement('a');
          link.href = result.download_url;
          link.download = message.media_filename || `media_${message.message_id}`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }
      } 
    } catch (error: any) {
      console.error('下载失败:', error);
    } finally {
      setDownloadLoading(false);
    }
  };

  // 处理视频播放/暂停
  const handleVideoToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (!videoRef.current) return;
    
    if (videoPlaying) {
      videoRef.current.pause();
    } else {
      videoRef.current.play();
    }
    
    setVideoPlaying(!videoPlaying);
  };

  // 获取媒体URL - 优先使用缩略图
  const getMediaUrl = () => {
    // 优先使用缩略图
    if (message.media_thumbnail_url) {
      return message.media_thumbnail_url;
    }
    
    // 如果文件已下载且有本地路径
    if (message.media_downloaded && message.media_path) {
      return `/api/media/download/${message.message_id}`;
    }
    
    // 最后使用下载URL
    return message.media_download_url || message.media_thumbnail_path || null;
  };

  // 计算媒体预览容器的样式
  const getContainerStyle = () => {
    const style: React.CSSProperties = {};
    const maxWidth = size === 'small' ? 120 : size === 'large' ? 240 : 180;
    
    style.maxWidth = expanded ? '100%' : `${maxWidth}px`;
    
    return style;
  };

  // 检查是否为可预览的媒体类型
  const isPreviewable = message.media_type ? ['photo', 'video'].includes(message.media_type) : false;
  const mediaUrl = inView ? getMediaUrl() : null;

  // 如果不是媒体消息或不支持预览，不显示
  if (!message.media_type || !isPreviewable) {
    return null;
  }

  return (
    <div 
      id={`media-preview-${message.message_id}`}
      className={`inline-media-preview ${size} ${className || ''} ${expanded ? 'expanded' : ''}`}
      onClick={onClick}
      style={getContainerStyle()}
    >
      {/* 图片预览 */}
      {message.media_type === 'photo' && inView && (
        <div className="media-preview-container">
          <Image
            src={mediaUrl || undefined}
            alt={message.media_filename || '图片'}
            width="100%"
            style={{ objectFit: 'cover', borderRadius: '6px' }}
            placeholder={
              <div className="image-placeholder">
                <Spin size="small" />
              </div>
            }
            onLoad={() => setLoading(false)}
            preview={{
              mask: (
                <Space>
                  <ExpandOutlined />
                  <span>预览</span>
                </Space>
              ),
            }}
            fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMIAAADDCAYAAADQvc6UAAABRWlDQ1BJQ0MgUHJvZmlsZQAAKJFjYGASSSwoyGFhYGDIzSspCnJ3UoiIjFJgf8LAwSDCIMogwMCcmFxc4BgQ4ANUwgCjUcG3awyMIPqyLsis7PPOq3QdDFcvjV3jOD1boQVTPQrgSkktTgbSf4A4LbmgqISBgTEFyFYuLykAsTuAbJEioKOA7DkgdjqEvQHEToKwj4DVhAQ5A9k3gGyB5IxEoBmML4BsnSQk8XQkNtReEOBxcfXxUQg1Mjc0dyHgXNJBSWpFCYh2zi+oLMpMzyhRcASGUqqCZ16yno6CkYGRAQMDKMwhqj/fAIcloxgHQqxAjIHBEugw5sUIsSQpBobtQPdLciLEVJYzMPBHMDBsayhILEqEO4DxG0txmrERhM29nYGBddr//5/DGRjYNRkY/l7////39v///y4Dmn+LgeHANwDrkl1AuO+pmgAAADhlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAAqACAAQAAAABAAAAwqADAAQAAAABAAAAwwAAAAD9b/HnAAAHlklEQVR4Ae3dP3Ik1RUG8O+L2hYSFRqYCZ9QaVx..."
          />

          {/* 悬浮控制栏 */}
          <div className="media-controls">
            <Button
              type="primary"
              size="small"
              icon={<ExpandOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                setExpanded(!expanded);
              }}
            />
            <Button
              type="primary"
              size="small"
              icon={<DownloadOutlined />}
              loading={downloadLoading}
              onClick={handleDownload}
            />
          </div>
        </div>
      )}

      {/* 视频预览 */}
      {message.media_type === 'video' && inView && (
        <div className="media-preview-container">
          <div className="video-container">
            <video
              ref={videoRef}
              src={mediaUrl || undefined}
              preload="metadata"
              width="100%"
              style={{ borderRadius: '6px' }}
              onClick={(e) => e.stopPropagation()}
              onLoadStart={() => setLoading(true)}
              onLoadedData={() => setLoading(false)}
              onPlay={() => setVideoPlaying(true)}
              onPause={() => setVideoPlaying(false)}
            />
            
            {loading && (
              <div className="video-loading">
                <Spin size="small" />
              </div>
            )}

            {/* 播放按钮覆盖层 */}
            <div 
              className="video-play-overlay"
              onClick={handleVideoToggle}
            >
              {!videoPlaying && (
                <div className="play-button">
                  <PlayCircleOutlined />
                </div>
              )}
            </div>
            
            {/* 悬浮控制栏 */}
            <div className="media-controls">
              <Button
                type="primary"
                size="small"
                icon={videoPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                onClick={handleVideoToggle}
              />
              <Button
                type="primary"
                size="small"
                icon={<ExpandOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  setExpanded(!expanded);
                }}
              />
              <Button
                type="primary"
                size="small"
                icon={<DownloadOutlined />}
                loading={downloadLoading}
                onClick={handleDownload}
              />
            </div>
          </div>
        </div>
      )}

      {/* 文件大小显示 */}
      {message.media_size && (
        <div className="file-info">
          <Text type="secondary" className="file-size">
            {formatFileSize(message.media_size)}
          </Text>
        </div>
      )}

      {/* 下载进度 */}
      {downloadLoading && downloadProgress > 0 && (
        <div className="download-progress">
          <Progress 
            percent={downloadProgress} 
            size="small" 
            status="active"
            showInfo={false}
          />
        </div>
      )}

      {/* 媒体不可用时的占位符 */}
      {isPreviewable && !mediaUrl && (
        <div className="media-unavailable">
          {getMediaIcon(message.media_type)}
        </div>
      )}
    </div>
  );
};

export default InlineMediaPreview;