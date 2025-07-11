import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Modal, Image, Button, Space, message, Spin, Progress, Tooltip } from 'antd';
import { 
  EyeOutlined, 
  DownloadOutlined, 
  PlayCircleOutlined, 
  FileImageOutlined, 
  VideoCameraOutlined,
  FileTextOutlined,
  AudioOutlined,
  FullscreenOutlined,
  CloseOutlined,
  LeftOutlined,
  RightOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  RotateLeftOutlined,
  RotateRightOutlined
} from '@ant-design/icons';
import './EnhancedMediaPreview.css';

// 获取完整的媒体URL
const getMediaUrl = (path: string): string => {
  if (!path) return '';
  
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  
  const apiBase = process.env.REACT_APP_API_URL || 'http://localhost:8001';
  return `${apiBase}/${path.startsWith('/') ? path.slice(1) : path}`;
};

// 格式化文件大小
const formatFileSize = (bytes: number | string): string => {
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

// 检测文件类型
const getFileType = (filename: string, mediaType: string): string => {
  if (mediaType) return mediaType;
  
  const ext = filename?.split('.').pop()?.toLowerCase();
  if (!ext) return 'document';
  
  const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'];
  const videoExts = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'];
  const audioExts = ['mp3', 'wav', 'ogg', 'aac', 'flac', 'm4a'];
  const docExts = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'];
  
  if (imageExts.includes(ext)) return 'photo';
  if (videoExts.includes(ext)) return 'video';
  if (audioExts.includes(ext)) return 'audio';
  if (docExts.includes(ext)) return 'document';
  
  return 'document';
};

// 获取文件图标
const getFileIcon = (mediaType: string, size: number = 16) => {
  const iconProps = { style: { fontSize: size } };
  
  switch (mediaType) {
    case 'photo': return <FileImageOutlined {...iconProps} style={{ ...iconProps.style, color: '#52c41a' }} />;
    case 'video': return <VideoCameraOutlined {...iconProps} style={{ ...iconProps.style, color: '#1890ff' }} />;
    case 'document': return <FileTextOutlined {...iconProps} style={{ ...iconProps.style, color: '#faad14' }} />;
    case 'audio':
    case 'voice': return <AudioOutlined {...iconProps} style={{ ...iconProps.style, color: '#722ed1' }} />;
    default: return <FileTextOutlined {...iconProps} />;
  }
};

interface EnhancedMediaPreviewProps {
  mediaType: string;
  mediaPath: string;
  filename?: string;
  size?: string | number;
  className?: string;
  thumbnail?: boolean;
  onGalleryOpen?: (mediaPath: string) => void;
  style?: React.CSSProperties;
}

const EnhancedMediaPreview: React.FC<EnhancedMediaPreviewProps> = ({
  mediaType,
  mediaPath,
  filename,
  size,
  className = '',
  thumbnail = false,
  onGalleryOpen,
  style
}) => {
  const [previewVisible, setPreviewVisible] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [downloading, setDownloading] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  
  const mediaUrl = getMediaUrl(mediaPath);
  const formattedSize = size ? formatFileSize(size) : undefined;
  const fileType = getFileType(filename || '', mediaType);
  
  // 处理媒体加载
  const handleMediaLoad = useCallback(() => {
    setLoading(false);
    setError(false);
  }, []);
  
  // 处理媒体错误
  const handleMediaError = useCallback((e: any) => {
    console.error('Media load error:', e);
    setLoading(false);
    setError(true);
  }, []);
  
  // 下载文件
  const handleDownload = useCallback(async () => {
    if (downloading) return;
    
    try {
      setDownloading(true);
      setDownloadProgress(0);
      
      const response = await fetch(mediaUrl);
      if (!response.ok) throw new Error('下载失败');
      
      if (!response.body) throw new Error('无法获取文件内容');
      
      const reader = response.body.getReader();
      const contentLength = response.headers.get('Content-Length');
      const total = contentLength ? parseInt(contentLength, 10) : 0;
      
      let received = 0;
      const chunks = [];
      
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        chunks.push(value);
        received += value.length;
        
        if (total > 0) {
          setDownloadProgress((received / total) * 100);
        }
      }
      
      const blob = new Blob(chunks);
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename || 'download';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
      message.success('下载完成');
    } catch (error) {
      console.error('Download failed:', error);
      message.error('下载失败，请检查网络连接');
    } finally {
      setDownloading(false);
      setDownloadProgress(0);
    }
  }, [mediaUrl, filename, downloading]);
  
  // 打开预览
  const handlePreview = useCallback(() => {
    if (onGalleryOpen) {
      onGalleryOpen(mediaPath);
    } else {
      setPreviewVisible(true);
    }
  }, [onGalleryOpen, mediaPath]);
  
  // 缩放控制
  const handleZoom = useCallback((delta: number) => {
    setZoom(prev => Math.max(0.1, Math.min(5, prev + delta)));
  }, []);
  
  // 旋转控制
  const handleRotate = useCallback((degrees: number) => {
    setRotation(prev => (prev + degrees) % 360);
  }, []);
  
  // 重置变换
  const resetTransform = useCallback(() => {
    setZoom(1);
    setRotation(0);
  }, []);
  
  // 渲染缩略图模式
  const renderThumbnail = () => {
    if (fileType === 'photo') {
      return (
        <div className={`media-thumbnail ${error ? 'error' : ''} ${loading ? 'loading' : ''}`} onClick={handlePreview}>
          {loading && <Spin size="small" />}
          {error ? (
            <div className="error-placeholder">
              {getFileIcon(fileType, 24)}
              <span>加载失败</span>
            </div>
          ) : (
            <>
              <img
                src={mediaUrl}
                alt={filename}
                onLoad={handleMediaLoad}
                onError={handleMediaError}
                style={{ opacity: loading ? 0 : 1 }}
              />
              <div className="media-overlay">
                <EyeOutlined style={{ fontSize: 20, color: 'white' }} />
              </div>
            </>
          )}
        </div>
      );
    }
    
    if (fileType === 'video') {
      return (
        <div className={`media-thumbnail video-thumbnail`} onClick={handlePreview}>
          <video
            ref={videoRef}
            src={mediaUrl}
            muted
            onLoadedData={handleMediaLoad}
            onError={handleMediaError}
          />
          <div className="media-overlay">
            <PlayCircleOutlined style={{ fontSize: 32, color: 'white' }} />
          </div>
        </div>
      );
    }
    
    // 其他文件类型的缩略图
    return (
      <div className="file-thumbnail" onClick={handlePreview}>
        {getFileIcon(fileType, 32)}
        <span className="file-type">{fileType.toUpperCase()}</span>
      </div>
    );
  };
  
  // 渲染完整预览
  const renderFullPreview = () => {
    const mediaStyle = {
      transform: `scale(${zoom}) rotate(${rotation}deg)`,
      transition: 'transform 0.3s ease'
    };
    
    if (fileType === 'photo') {
      return (
        <div className="enhanced-preview">
          <div className="preview-controls">
            <Space>
              <Tooltip title="放大">
                <Button type="text" icon={<ZoomInOutlined />} onClick={() => handleZoom(0.2)} />
              </Tooltip>
              <Tooltip title="缩小">
                <Button type="text" icon={<ZoomOutOutlined />} onClick={() => handleZoom(-0.2)} />
              </Tooltip>
              <Tooltip title="向左旋转">
                <Button type="text" icon={<RotateLeftOutlined />} onClick={() => handleRotate(-90)} />
              </Tooltip>
              <Tooltip title="向右旋转">
                <Button type="text" icon={<RotateRightOutlined />} onClick={() => handleRotate(90)} />
              </Tooltip>
              <Button onClick={resetTransform}>重置</Button>
              <Button type="primary" onClick={handleDownload} loading={downloading}>
                <DownloadOutlined /> 下载
              </Button>
            </Space>
          </div>
          <div className="preview-content">
            <img 
              src={mediaUrl} 
              alt={filename} 
              style={mediaStyle}
              draggable={false}
            />
          </div>
        </div>
      );
    }
    
    if (fileType === 'video') {
      return (
        <div className="enhanced-preview">
          <div className="preview-controls">
            <Space>
              <Button type="primary" onClick={handleDownload} loading={downloading}>
                <DownloadOutlined /> 下载
              </Button>
            </Space>
          </div>
          <div className="preview-content">
            <video 
              src={mediaUrl} 
              controls 
              autoPlay
              style={{ width: '100%', maxHeight: '70vh' }}
              onLoadedData={handleMediaLoad}
              onError={handleMediaError}
            />
          </div>
        </div>
      );
    }
    
    // 其他文件类型的预览
    return (
      <div className="file-preview">
        <div className="file-info">
          {getFileIcon(fileType, 64)}
          <h3>{filename}</h3>
          {formattedSize && <p>大小：{formattedSize}</p>}
        </div>
        <Button type="primary" size="large" onClick={handleDownload} loading={downloading}>
          <DownloadOutlined /> 下载文件
        </Button>
      </div>
    );
  };
  
  // 如果是缩略图模式，只渲染缩略图
  if (thumbnail) {
    return (
      <div className={`enhanced-media-preview thumbnail-mode ${className}`} style={style}>
        {renderThumbnail()}
        {(filename || formattedSize) && (
          <div className="media-info">
            {filename && <div className="media-filename">{filename}</div>}
            {formattedSize && <div className="media-size">{formattedSize}</div>}
          </div>
        )}
      </div>
    );
  }
  
  return (
    <div className={`enhanced-media-preview ${className}`} style={style}>
      {renderThumbnail()}
      
      {(filename || formattedSize) && (
        <div className="media-info">
          {filename && <div className="media-filename">{filename}</div>}
          {formattedSize && <div className="media-size">{formattedSize}</div>}
          <Space size="small">
            <Button 
              type="text" 
              icon={<EyeOutlined />} 
              size="small"
              onClick={handlePreview}
            >
              预览
            </Button>
            <Button 
              type="text" 
              icon={<DownloadOutlined />} 
              size="small"
              onClick={handleDownload}
              loading={downloading}
            >
              下载
            </Button>
          </Space>
        </div>
      )}
      
      {downloading && downloadProgress > 0 && (
        <div className="download-progress">
          <Progress percent={Math.round(downloadProgress)} size="small" />
        </div>
      )}
      
      <Modal
        open={previewVisible}
        footer={null}
        onCancel={() => setPreviewVisible(false)}
        width="90%"
        style={{ maxWidth: 1200 }}
        centered
        className="enhanced-media-modal"
      >
        {renderFullPreview()}
      </Modal>
    </div>
  );
};

export default EnhancedMediaPreview;