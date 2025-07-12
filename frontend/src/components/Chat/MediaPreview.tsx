import React, { useState } from 'react';
import { Modal, Image, Button, Space, message } from 'antd';
import { EyeOutlined, DownloadOutlined, PlayCircleOutlined, FileImageOutlined, VideoCameraOutlined } from '@ant-design/icons';
import { useMediaDownload } from '../../hooks/useMediaDownload';
import MediaDownloadOverlay from './MediaDownloadOverlay';
import './MediaPreview.css';

// 获取完整的媒体URL
const getMediaUrl = (path: string) => {
  if (!path) return '';
  
  // 如果已经是完整URL，直接返回
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  
  // 如果路径以 media/ 开头，直接使用 /media/ 前缀（静态文件服务）
  if (path.startsWith('media/')) {
    return `/${path}`;
  }
  
  // 如果是其他相对路径，使用API基础URL
  const apiBase = process.env.REACT_APP_API_URL || '';
  return `${apiBase}/${path.startsWith('/') ? path.slice(1) : path}`;
};

// 格式化文件大小
const formatFileSize = (bytes: number | string) => {
  if (typeof bytes === 'string') {
    const parsed = parseFloat(bytes);
    if (isNaN(parsed)) return bytes;
    bytes = parsed;
  }
  
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
};

interface MediaPreviewProps {
  messageId: number; // 消息ID，用于下载状态追踪
  url: string;
  type: 'image' | 'video';
  filename?: string;
  size?: string | number;
  downloaded?: boolean; // 是否已下载
  className?: string;
}

const MediaPreview: React.FC<MediaPreviewProps> = ({
  messageId,
  url,
  type,
  filename,
  size,
  downloaded = false,
  className
}) => {
  const [previewVisible, setPreviewVisible] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // 下载状态管理
  const {
    downloadStatus,
    isLoading: isDownloading,
    startDownload,
    retryDownload
  } = useMediaDownload({
    messageId,
    autoRefresh: !downloaded, // 如果未下载才自动刷新状态
    onDownloadComplete: (filePath) => {
      message.success('文件下载完成');
      // 可以在这里更新本地状态或触发其他操作
    },
    onDownloadError: (error) => {
      message.error(`下载失败: ${error}`);
    }
  });
  
  const mediaUrl = getMediaUrl(url);
  const formattedSize = size ? formatFileSize(size) : undefined;
  
  // 判断是否应该显示媒体内容
  const shouldShowMedia = downloaded || downloadStatus.status === 'downloaded';
  
  // 将媒体类型转换为下载组件需要的格式
  const mediaType = type === 'image' ? 'photo' : type;

  const handleDownload = async () => {
    try {
      const response = await fetch(getMediaUrl(url));
      if (!response.ok) {
        throw new Error('下载失败');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename || 'download';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      message.error('下载失败，请检查网络连接');
      console.error('Download failed:', error);
    }
  };

  if (type === 'image') {
    return (
      <div className={`media-preview image-preview ${className || ''} ${imageError ? 'error' : ''} ${loading ? 'loading' : ''}`}>
        <div className="media-thumbnail" onClick={() => shouldShowMedia && setPreviewVisible(true)} style={{ position: 'relative' }}>
          {shouldShowMedia ? (
            <>
              <Image
                src={mediaUrl}
                alt={filename}
                style={{ maxWidth: 200, maxHeight: 150, objectFit: 'cover', borderRadius: 8 }}
                preview={false}
                onLoad={() => setLoading(false)}
                onError={(e) => {
                  console.error('Image load error:', e);
                  setImageError(true);
                  setLoading(false);
                }}
              />
              
              {/* 类型指示器 */}
              <div className="media-type-icon">
                <FileImageOutlined />
                IMAGE
              </div>
              
              {/* 大小指示器 */}
              {formattedSize && (
                <div className="media-size-indicator">
                  {formattedSize}
                </div>
              )}
              
              <div className="media-overlay">
                <EyeOutlined style={{ fontSize: 24, color: 'white' }} />
              </div>
            </>
          ) : (
            <>
              {/* 占位符 */}
              <div 
                style={{ 
                  width: 200, 
                  height: 150, 
                  borderRadius: 8, 
                  background: '#f5f5f5',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <FileImageOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
              </div>
            </>
          )}
          
          {/* 下载遮罩层 */}
          {!shouldShowMedia && (
            <MediaDownloadOverlay
              mediaType={mediaType}
              downloadStatus={downloadStatus}
              fileName={filename}
              fileSize={typeof size === 'number' ? size : undefined}
              isLoading={isDownloading}
              onDownload={startDownload}
              onRetry={retryDownload}
            />
          )}
        </div>
        
        {(filename || size) && (
          <div className="media-info">
            {filename && <div className="media-filename">{filename}</div>}
            {formattedSize && <div className="media-size">{formattedSize}</div>}
            <Space size={4}>
              <Button 
                type="text" 
                icon={<EyeOutlined />} 
                size="small"
                onClick={() => setPreviewVisible(true)}
                disabled={!shouldShowMedia}
              >
                预览
              </Button>
              <Button 
                type="text" 
                icon={<DownloadOutlined />} 
                size="small"
                onClick={shouldShowMedia ? handleDownload : () => startDownload()}
                loading={isDownloading}
              >
                下载
              </Button>
            </Space>
          </div>
        )}
        
        {shouldShowMedia && (
          <Modal
            open={previewVisible}
            footer={null}
            onCancel={() => setPreviewVisible(false)}
            width="80%"
            style={{ maxWidth: 800 }}
            centered
          >
            <Image src={mediaUrl} alt={filename} style={{ width: '100%' }} />
          </Modal>
        )}
      </div>
    );
  }

  if (type === 'video') {
    return (
      <div className={`media-preview video-preview ${className || ''}`}>
        <div className="video-thumbnail" onClick={() => shouldShowMedia && setPreviewVisible(true)} style={{ position: 'relative' }}>
          {shouldShowMedia ? (
            <>
              <video
                src={mediaUrl}
                style={{ maxWidth: 200, maxHeight: 150, objectFit: 'cover', borderRadius: 8 }}
                muted
                poster={mediaUrl} // 可以添加视频缩略图
                onError={(e) => {
                  console.error('Video load error:', e);
                }}
              />
              
              {/* 类型指示器 */}
              <div className="media-type-icon">
                <VideoCameraOutlined />
                VIDEO
              </div>
              
              {/* 大小指示器 */}
              {formattedSize && (
                <div className="media-size-indicator">
                  {formattedSize}
                </div>
              )}
              
              <div className="media-overlay">
                <PlayCircleOutlined style={{ fontSize: 32, color: 'white' }} />
              </div>
            </>
          ) : (
            <>
              {/* 占位符 */}
              <div 
                style={{ 
                  width: 200, 
                  height: 150, 
                  borderRadius: 8, 
                  background: '#f5f5f5',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <VideoCameraOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
              </div>
            </>
          )}
          
          {/* 下载遮罩层 */}
          {!shouldShowMedia && (
            <MediaDownloadOverlay
              mediaType={mediaType}
              downloadStatus={downloadStatus}
              fileName={filename}
              fileSize={typeof size === 'number' ? size : undefined}
              isLoading={isDownloading}
              onDownload={startDownload}
              onRetry={retryDownload}
            />
          )}
        </div>
        
        {(filename || size) && (
          <div className="media-info">
            {filename && <div className="media-filename">{filename}</div>}
            {formattedSize && <div className="media-size">{formattedSize}</div>}
            <Space size={4}>
              <Button 
                type="text" 
                icon={<PlayCircleOutlined />} 
                size="small"
                onClick={() => setPreviewVisible(true)}
                disabled={!shouldShowMedia}
              >
                播放
              </Button>
              <Button 
                type="text" 
                icon={<DownloadOutlined />} 
                size="small"
                onClick={shouldShowMedia ? handleDownload : () => startDownload()}
                loading={isDownloading}
              >
                下载
              </Button>
            </Space>
          </div>
        )}
        
        {shouldShowMedia && (
          <Modal
            open={previewVisible}
            footer={null}
            onCancel={() => setPreviewVisible(false)}
            width="80%"
            style={{ maxWidth: 800 }}
            centered
          >
            <video 
              src={mediaUrl} 
              controls 
              style={{ width: '100%', maxHeight: '70vh' }}
              autoPlay
            />
          </Modal>
        )}
      </div>
    );
  }

  return null;
};

export default MediaPreview;