import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Modal, Button, Space, message, Image, Tooltip } from 'antd';
import {
  CloseOutlined,
  LeftOutlined,
  RightOutlined,
  DownloadOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  RotateLeftOutlined,
  RotateRightOutlined,
  FullscreenOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  FileImageOutlined,
  VideoCameraOutlined,
  AudioOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import { TelegramMessage } from '../../types';
import './MediaGallery.css';

// 获取完整的媒体URL
const getMediaUrl = (path: string): string => {
  if (!path) return '';
  
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  
  const apiBase = process.env.REACT_APP_API_URL || '';
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

// 获取媒体类型图标
const getMediaIcon = (mediaType: string) => {
  switch (mediaType) {
    case 'photo': return <FileImageOutlined />;
    case 'video': return <VideoCameraOutlined />;
    case 'audio':
    case 'voice': return <AudioOutlined />;
    default: return <FileTextOutlined />;
  }
};

interface MediaItem {
  id: number;
  mediaType: string;
  mediaPath: string;
  mediaFilename?: string;
  mediaSize?: number;
  text?: string;
  date: string;
  senderName?: string;
}

interface MediaGalleryProps {
  visible: boolean;
  onClose: () => void;
  mediaItems: MediaItem[];
  initialIndex?: number;
  className?: string;
}

const MediaGallery: React.FC<MediaGalleryProps> = ({
  visible,
  onClose,
  mediaItems,
  initialIndex = 0,
  className = ''
}) => {
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isVideoPlaying, setIsVideoPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const galleryRef = useRef<HTMLDivElement>(null);
  
  const currentItem = mediaItems[currentIndex];
  const mediaUrl = currentItem ? getMediaUrl(currentItem.mediaPath) : '';
  
  // 重置状态
  const resetState = useCallback(() => {
    setZoom(1);
    setRotation(0);
    setIsVideoPlaying(false);
    setLoading(false);
    setError(null);
  }, []);
  
  // 当索引变化时重置状态
  useEffect(() => {
    if (visible) {
      resetState();
    }
  }, [currentIndex, visible, resetState]);
  
  // 键盘事件处理
  useEffect(() => {
    if (!visible) return;
    
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowLeft':
          handlePrevious();
          break;
        case 'ArrowRight':
          handleNext();
          break;
        case 'Escape':
          onClose();
          break;
        case '+':
        case '=':
          handleZoom(0.2);
          break;
        case '-':
          handleZoom(-0.2);
          break;
        case '0':
          resetTransform();
          break;
        case 'r':
        case 'R':
          handleRotate(90);
          break;
        case 'f':
        case 'F':
          toggleFullscreen();
          break;
        case ' ':
          e.preventDefault();
          if (currentItem?.mediaType === 'video') {
            toggleVideoPlay();
          }
          break;
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [visible, currentIndex, currentItem]);
  
  // 导航控制
  const handlePrevious = useCallback(() => {
    if (mediaItems.length > 0) {
      setCurrentIndex(prev => prev > 0 ? prev - 1 : mediaItems.length - 1);
    }
  }, [mediaItems.length]);
  
  const handleNext = useCallback(() => {
    if (mediaItems.length > 0) {
      setCurrentIndex(prev => prev < mediaItems.length - 1 ? prev + 1 : 0);
    }
  }, [mediaItems.length]);
  
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
  
  // 全屏控制
  const toggleFullscreen = useCallback(() => {
    if (!isFullscreen) {
      if (galleryRef.current?.requestFullscreen) {
        galleryRef.current.requestFullscreen();
        setIsFullscreen(true);
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
        setIsFullscreen(false);
      }
    }
  }, [isFullscreen]);
  
  // 视频播放控制
  const toggleVideoPlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    
    if (isVideoPlaying) {
      video.pause();
    } else {
      video.play().catch(error => {
        console.error('Video play error:', error);
        message.error('视频播放失败');
      });
    }
    setIsVideoPlaying(!isVideoPlaying);
  }, [isVideoPlaying]);
  
  // 下载当前媒体
  const handleDownload = useCallback(async () => {
    if (!currentItem) return;
    
    try {
      setLoading(true);
      const response = await fetch(mediaUrl);
      if (!response.ok) throw new Error('下载失败');
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = currentItem.mediaFilename || `media_${currentItem.id}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
      message.success('下载完成');
    } catch (error) {
      console.error('Download failed:', error);
      message.error('下载失败，请检查网络连接');
    } finally {
      setLoading(false);
    }
  }, [currentItem, mediaUrl]);
  
  // 渲染媒体内容
  const renderMediaContent = () => {
    if (!currentItem) return null;
    
    const mediaStyle = {
      transform: `scale(${zoom}) rotate(${rotation}deg)`,
      transition: 'transform 0.3s ease'
    };
    
    switch (currentItem.mediaType) {
      case 'photo':
        return (
          <div className="media-container">
            <img
              src={mediaUrl}
              alt={currentItem.mediaFilename}
              style={mediaStyle}
              onLoad={() => setLoading(false)}
              onError={() => {
                setError('图片加载失败');
                setLoading(false);
              }}
              draggable={false}
            />
          </div>
        );
        
      case 'video':
        return (
          <div className="media-container">
            <video
              ref={videoRef}
              src={mediaUrl}
              controls
              style={mediaStyle}
              onLoadedData={() => setLoading(false)}
              onError={() => {
                setError('视频加载失败');
                setLoading(false);
              }}
              onPlay={() => setIsVideoPlaying(true)}
              onPause={() => setIsVideoPlaying(false)}
              onEnded={() => setIsVideoPlaying(false)}
            />
            {!isVideoPlaying && (
              <div className="video-overlay" onClick={toggleVideoPlay}>
                <PlayCircleOutlined style={{ fontSize: 64, color: 'white' }} />
              </div>
            )}
          </div>
        );
        
      case 'audio':
      case 'voice':
        return (
          <div className="audio-container">
            <div className="audio-placeholder">
              {getMediaIcon(currentItem.mediaType)}
              <h3>音频文件</h3>
              <p>{currentItem.mediaFilename}</p>
              <audio src={mediaUrl} controls style={{ marginTop: 16 }} />
            </div>
          </div>
        );
        
      default:
        return (
          <div className="file-container">
            <div className="file-placeholder">
              {getMediaIcon(currentItem.mediaType)}
              <h3>文档文件</h3>
              <p>{currentItem.mediaFilename}</p>
              {currentItem.mediaSize && (
                <p>大小：{formatFileSize(currentItem.mediaSize)}</p>
              )}
              <Button type="primary" onClick={handleDownload} loading={loading}>
                <DownloadOutlined /> 下载文件
              </Button>
            </div>
          </div>
        );
    }
  };
  
  // 渲染缩略图导航
  const renderThumbnails = () => {
    if (mediaItems.length <= 1) return null;
    
    return (
      <div className="thumbnails-container">
        <div className="thumbnails-scroll">
          {mediaItems.map((item, index) => (
            <div
              key={item.id}
              className={`thumbnail ${index === currentIndex ? 'active' : ''}`}
              onClick={() => setCurrentIndex(index)}
            >
              {item.mediaType === 'photo' ? (
                <img src={getMediaUrl(item.mediaPath)} alt="" />
              ) : (
                <div className="thumbnail-placeholder">
                  {getMediaIcon(item.mediaType)}
                </div>
              )}
              <div className="thumbnail-overlay">
                <span>{index + 1}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };
  
  if (!visible || !currentItem) return null;
  
  return (
    <Modal
      open={visible}
      onCancel={onClose}
      footer={null}
      width="100vw"
      style={{ top: 0, paddingBottom: 0 }}
      className={`media-gallery-modal ${className}`}
      closeIcon={null}
      maskStyle={{ backgroundColor: 'rgba(0, 0, 0, 0.9)' }}
    >
      <div ref={galleryRef} className="media-gallery">
        {/* 顶部工具栏 */}
        <div className="gallery-header">
          <div className="header-info">
            <span className="media-counter">
              {currentIndex + 1} / {mediaItems.length}
            </span>
            <div className="media-info">
              <h4>{currentItem.mediaFilename || '未命名文件'}</h4>
              <p>
                {currentItem.senderName && `发送者：${currentItem.senderName} • `}
                {new Date(currentItem.date).toLocaleString('zh-CN')}
                {currentItem.mediaSize && ` • ${formatFileSize(currentItem.mediaSize)}`}
              </p>
            </div>
          </div>
          
          <div className="header-controls">
            <Space size="small">
              {currentItem.mediaType === 'photo' && (
                <>
                  <Tooltip title="放大 (+)">
                    <Button 
                      type="text" 
                      icon={<ZoomInOutlined />} 
                      onClick={() => handleZoom(0.2)}
                    />
                  </Tooltip>
                  <Tooltip title="缩小 (-)">
                    <Button 
                      type="text" 
                      icon={<ZoomOutOutlined />} 
                      onClick={() => handleZoom(-0.2)}
                    />
                  </Tooltip>
                  <Tooltip title="向左旋转 (R)">
                    <Button 
                      type="text" 
                      icon={<RotateLeftOutlined />} 
                      onClick={() => handleRotate(-90)}
                    />
                  </Tooltip>
                  <Tooltip title="向右旋转 (R)">
                    <Button 
                      type="text" 
                      icon={<RotateRightOutlined />} 
                      onClick={() => handleRotate(90)}
                    />
                  </Tooltip>
                  <Button onClick={resetTransform}>重置 (0)</Button>
                </>
              )}
              
              <Tooltip title="全屏 (F)">
                <Button 
                  type="text" 
                  icon={<FullscreenOutlined />} 
                  onClick={toggleFullscreen}
                />
              </Tooltip>
              
              <Tooltip title="下载">
                <Button 
                  type="text" 
                  icon={<DownloadOutlined />} 
                  onClick={handleDownload}
                  loading={loading}
                />
              </Tooltip>
              
              <Tooltip title="关闭 (ESC)">
                <Button 
                  type="text" 
                  icon={<CloseOutlined />} 
                  onClick={onClose}
                />
              </Tooltip>
            </Space>
          </div>
        </div>
        
        {/* 主要内容区域 */}
        <div className="gallery-content">
          {/* 左侧导航 */}
          {mediaItems.length > 1 && (
            <Button
              className="nav-button nav-left"
              type="text"
              icon={<LeftOutlined />}
              onClick={handlePrevious}
              size="large"
            />
          )}
          
          {/* 媒体显示区域 */}
          <div className="media-display">
            {loading && <div className="loading">加载中...</div>}
            {error && <div className="error">{error}</div>}
            {!loading && !error && renderMediaContent()}
          </div>
          
          {/* 右侧导航 */}
          {mediaItems.length > 1 && (
            <Button
              className="nav-button nav-right"
              type="text"
              icon={<RightOutlined />}
              onClick={handleNext}
              size="large"
            />
          )}
        </div>
        
        {/* 消息文本 */}
        {currentItem.text && (
          <div className="message-text">
            <p>{currentItem.text}</p>
          </div>
        )}
        
        {/* 底部缩略图导航 */}
        {renderThumbnails()}
        
        {/* 键盘快捷键提示 */}
        <div className="keyboard-hints">
          <span>快捷键：← → 切换 | + - 缩放 | R 旋转 | F 全屏 | ESC 关闭</span>
        </div>
      </div>
    </Modal>
  );
};

export default MediaGallery;