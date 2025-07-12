import React, { useState, useCallback, useRef } from 'react';
import { Modal, Button, Space, message, Spin, Progress, Tooltip } from 'antd';
import { 
  EyeOutlined, 
  DownloadOutlined, 
  PlayCircleOutlined, 
  FileImageOutlined, 
  VideoCameraOutlined,
  FileTextOutlined,
  AudioOutlined,
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
  
  // 处理media路径 - 静态文件直接使用 /media/ 前缀
  if (path.startsWith('media/')) {
    return `/${path}`;
  }
  
  const apiBase = process.env.REACT_APP_API_URL || '';
  
  // 处理相对路径
  if (path.startsWith('/')) {
    return `${apiBase}${path}`;
  }
  
  // 默认处理
  return `${apiBase}/${path}`;
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
  mediaPath?: string;  // 本地文件路径（可能为空）
  filename?: string;
  size?: string | number;
  className?: string;
  thumbnail?: boolean;
  onGalleryOpen?: (mediaPath: string) => void;
  style?: React.CSSProperties;
  messageId?: number;  // 新增：消息ID用于按需下载
  fileId?: string;     // 新增：Telegram文件ID
  downloaded?: boolean; // 新增：是否已下载
}

const EnhancedMediaPreview: React.FC<EnhancedMediaPreviewProps> = ({
  mediaType,
  mediaPath,
  filename,
  size,
  className = '',
  thumbnail = false,
  onGalleryOpen,
  style,
  messageId,
  fileId,
  downloaded = false
}) => {
  const [previewVisible, setPreviewVisible] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [downloading, setDownloading] = useState(false);
  const [onDemandDownloading, setOnDemandDownloading] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [currentMediaPath, setCurrentMediaPath] = useState(mediaPath);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  
  const mediaUrl = getMediaUrl(currentMediaPath || '');
  
  // Debug logging
  console.log('MediaPreview Debug:', {
    mediaType,
    mediaPath: currentMediaPath,
    mediaUrl,
    filename,
    size,
    downloaded,
    messageId,
    fileId
  });
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
  
  // 按需下载文件
  const handleOnDemandDownload = useCallback(async () => {
    if (!messageId || !fileId || onDemandDownloading) return;
    
    try {
      setOnDemandDownloading(true);
      
      // 调用后端API开始下载
      const apiBase = process.env.REACT_APP_API_URL || '';
      const response = await fetch(`${apiBase}/api/media/download/${messageId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ force: false })
      });
      
      if (!response.ok) {
        throw new Error('下载请求失败');
      }
      
      const result = await response.json();
      
      if (result.status === 'already_downloaded') {
        // 文件已存在，更新本地路径
        setCurrentMediaPath(result.file_path);
        message.success('文件已存在');
      } else if (result.status === 'download_started') {
        // 下载已开始，显示提示
        message.info('下载已开始，请稍后...');
        
        // 轮询检查下载状态
        const checkStatus = async () => {
          try {
            const statusResponse = await fetch(`${apiBase}/api/media/download-status/${messageId}`);
            const statusResult = await statusResponse.json();
            
            if (statusResult.status === 'downloaded') {
              setCurrentMediaPath(statusResult.file_path);
              message.success('文件下载完成');
              setOnDemandDownloading(false);
              return;
            } else if (statusResult.status === 'download_failed') {
              message.error(`下载失败: ${statusResult.error}`);
              setOnDemandDownloading(false);
              return;
            }
            
            // 继续轮询
            setTimeout(checkStatus, 1000);
          } catch (error) {
            console.error('检查下载状态失败:', error);
            setOnDemandDownloading(false);
          }
        };
        
        setTimeout(checkStatus, 1000);
      }
      
    } catch (error) {
      console.error('按需下载失败:', error);
      message.error('下载失败，请重试');
    } finally {
      // 不在这里设置false，让轮询来控制
    }
  }, [messageId, fileId, onDemandDownloading]);
  
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
    if (!currentMediaPath) {
      // 如果没有媒体路径，触发下载
      handleOnDemandDownload();
      return;
    }
    
    if (onGalleryOpen && currentMediaPath) {
      onGalleryOpen(currentMediaPath);
    } else {
      setPreviewVisible(true);
    }
  }, [onGalleryOpen, currentMediaPath, handleOnDemandDownload]);
  
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
    // 如果没有媒体路径，显示占位符
    if (!currentMediaPath) {
      return (
        <div className="file-thumbnail placeholder" onClick={handleOnDemandDownload}>
          {getFileIcon(fileType, 32)}
          <span className="file-type">{fileType.toUpperCase()}</span>
          <div className="download-hint">点击下载</div>
        </div>
      );
    }
    
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
      if (!currentMediaPath) {
        return (
          <div className="file-thumbnail placeholder" onClick={handleOnDemandDownload}>
            {getFileIcon(fileType, 32)}
            <span className="file-type">{fileType.toUpperCase()}</span>
            <div className="download-hint">点击下载</div>
          </div>
        );
      }
      
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
            {currentMediaPath ? (
              <>
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
              </>
            ) : (
              <Button 
                type="primary" 
                icon={<DownloadOutlined />} 
                size="small"
                onClick={handleOnDemandDownload}
                loading={onDemandDownloading}
              >
                {onDemandDownloading ? '下载中...' : '点击下载'}
              </Button>
            )}
          </Space>
        </div>
      )}
      
      {(downloading && downloadProgress > 0) && (
        <div className="download-progress">
          <Progress percent={Math.round(downloadProgress)} size="small" />
        </div>
      )}
      
      {onDemandDownloading && (
        <div className="download-progress">
          <Progress percent={0} size="small" status="active" />
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