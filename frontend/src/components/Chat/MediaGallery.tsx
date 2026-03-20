import React, { useState, useEffect, useCallback } from 'react';
import { Modal, Button, Space, Typography, message as notification } from 'antd';
import {
  CloseOutlined,
  DownloadOutlined,
  LeftOutlined,
  RightOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  RotateRightOutlined,
  FullscreenOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined
} from '@ant-design/icons';
import { TelegramMessage } from '../../types';
import './MediaGallery.css';

const { Text } = Typography;

interface MediaGalleryProps {
  messages: TelegramMessage[];
  currentIndex: number;
  visible: boolean;
  onClose: () => void;
  onIndexChange?: (index: number) => void;
  downloadStates?: Record<number, any>;
}

interface MediaItem {
  message: TelegramMessage;
  url: string;
  type: 'image' | 'video' | 'audio' | 'document';
}

const MediaGallery: React.FC<MediaGalleryProps> = ({
  messages,
  currentIndex,
  visible,
  onClose,
  onIndexChange,
  downloadStates = {}
}) => {
  const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
  const [activeIndex, setActiveIndex] = useState(currentIndex);
  // const [isFullscreen, setIsFullscreen] = useState(false);
  const [imageScale, setImageScale] = useState(1);
  const [imageRotation, setImageRotation] = useState(0);
  const [videoPlaying, setVideoPlaying] = useState(false);

  // 构建媒体URL（修复重复media路径问题，支持downloadUrl）
  const buildMediaUrl = useCallback((message: TelegramMessage): string => {
    // 首先检查是否有下载状态中的URL（优先使用，适用于刚下载完成的文件）
    const messageId = message.id || message.message_id;
    const downloadState = downloadStates[messageId];
    if (downloadState?.downloadUrl) {
      const downloadUrl = downloadState.downloadUrl;

      // 如果downloadUrl已经是完整路径，直接返回
      if (downloadUrl.startsWith('/media/')) {
        return downloadUrl;
      }
      // 如果需要清理和添加前缀
      if (downloadUrl.startsWith('./media/')) {
        return downloadUrl.replace('./media/', '/media/');
      }
      // 如果是相对路径，添加前缀
      return downloadUrl.startsWith('/') ? downloadUrl : `/media/${downloadUrl}`;
    }

    // 使用message.media_path作为后备
    const path = message.media_path;
    if (!path) return '';


    // 如果已经是完整URL，直接返回
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path;
    }

    // 如果路径以 /media/ 开头，直接返回
    if (path.startsWith('/media/')) {
      return path;
    }

    // 如果路径以 media/ 开头，添加前导斜杠
    if (path.startsWith('media/')) {
      const result = `/${path}`;
      return result;
    }

    // 如果路径包含 ./media/ 前缀，清理并返回
    if (path.startsWith('./media/')) {
      const result = path.replace('./media/', '/media/');
      return result;
    }

    // 其他情况，构建完整路径
    const result = `/media/${path}`;
    return result;
  }, [downloadStates]);

  // 获取媒体类型，增加文件扩展名验证
  const getMediaType = useCallback((message: TelegramMessage): 'image' | 'video' | 'audio' | 'document' => {
    const mediaType = message.media_type;
    const mediaPath = message.media_path || '';

    // 根据文件路径后缀判断实际类型
    const getTypeFromExtension = (path: string): 'image' | 'video' | 'audio' | 'document' => {
      // 如果路径为空，则无法判断
      if (!path) return 'document';

      const lowerPath = path.toLowerCase();

      // 视频扩展名
      if (lowerPath.endsWith('.mp4') ||
        lowerPath.endsWith('.mov') ||
        lowerPath.endsWith('.avi') ||
        lowerPath.endsWith('.webm') ||
        lowerPath.endsWith('.mkv') ||
        lowerPath.endsWith('.flv')) {
        return 'video';
      }

      // 图片扩展名
      if (lowerPath.endsWith('.jpg') ||
        lowerPath.endsWith('.jpeg') ||
        lowerPath.endsWith('.png') ||
        lowerPath.endsWith('.gif') ||
        lowerPath.endsWith('.webp') ||
        lowerPath.endsWith('.bmp') ||
        lowerPath.endsWith('.svg')) {
        return 'image';
      }

      // 音频扩展名
      if (lowerPath.endsWith('.mp3') ||
        lowerPath.endsWith('.wav') ||
        lowerPath.endsWith('.ogg') ||
        lowerPath.endsWith('.aac') ||
        lowerPath.endsWith('.flac') ||
        lowerPath.endsWith('.m4a')) {
        return 'audio';
      }

      // 默认为文档
      return 'document';
    };

    // 首先通过文件扩展名判断
    const typeFromExtension = getTypeFromExtension(mediaPath);

    // 记录类型差异
    if (typeFromExtension !== getTypeFromMediaType(mediaType)) {
    }

    // 返回基于文件扩展名的类型（优先级更高）
    return typeFromExtension;
  }, []);

  // 辅助函数：从message.media_type获取媒体类型
  const getTypeFromMediaType = (mediaType: string | undefined): 'image' | 'video' | 'audio' | 'document' => {
    switch (mediaType) {
      case 'photo':
        return 'image';
      case 'video':
        return 'video';
      case 'audio':
      case 'voice':
        return 'audio';
      default:
        return 'document';
    }
  };

  // 初始化媒体项目
  useEffect(() => {
    const items = messages
      .filter(msg => {
        if (!msg.media_type) return false;

        // 检查是否有媒体路径或下载状态中的URL
        const messageId = msg.id || msg.message_id;
        const downloadState = downloadStates[messageId];
        const hasMediaUrl = msg.media_path || downloadState?.downloadUrl;


        return !!hasMediaUrl;
      })
      .map(msg => {
        // 获取媒体类型并构建URL
        const mediaType = getMediaType(msg);
        const mediaUrl = buildMediaUrl(msg);

        // 记录详细信息便于调试

        return {
          message: msg,
          url: mediaUrl,
          type: mediaType
        };
      });

    setMediaItems(items);
  }, [messages, buildMediaUrl, getMediaType, downloadStates]);

  // 同步当前索引
  useEffect(() => {
    setActiveIndex(currentIndex);
  }, [currentIndex]);

  // 重置视图状态
  const resetViewState = useCallback(() => {
    setImageScale(1);
    setImageRotation(0);
    setVideoPlaying(false);
  }, []);

  // 获取当前媒体项
  const getCurrentItem = useCallback((): MediaItem | null => {
    return mediaItems[activeIndex] || null;
  }, [mediaItems, activeIndex]);

  // 导航功能
  const goToPrevious = useCallback(() => {
    const newIndex = activeIndex > 0 ? activeIndex - 1 : mediaItems.length - 1;
    setActiveIndex(newIndex);
    onIndexChange?.(newIndex);
    resetViewState();
  }, [activeIndex, mediaItems.length, onIndexChange, resetViewState]);

  const goToNext = useCallback(() => {
    const newIndex = activeIndex < mediaItems.length - 1 ? activeIndex + 1 : 0;
    setActiveIndex(newIndex);
    onIndexChange?.(newIndex);
    resetViewState();
  }, [activeIndex, mediaItems.length, onIndexChange, resetViewState]);

  // 全屏切换
  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      // setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      // setIsFullscreen(false);
    }
  }, []);

  // 图片控制
  const zoomIn = () => setImageScale(prev => Math.min(prev + 0.25, 3));
  const zoomOut = () => setImageScale(prev => Math.max(prev - 0.25, 0.25));
  const rotateImage = () => setImageRotation(prev => prev + 90);

  // 视频控制
  const toggleVideoPlayback = useCallback(() => {
    const video = document.querySelector('.gallery-video') as HTMLVideoElement;
    if (video) {
      if (video.paused) {
        video.play();
        setVideoPlaying(true);
      } else {
        video.pause();
        setVideoPlaying(false);
      }
    }
  }, []);

  // 下载当前媒体
  const downloadCurrentMedia = () => {
    const currentItem = getCurrentItem();
    if (!currentItem) return;

    const link = document.createElement('a');
    link.href = currentItem.url;
    link.download = currentItem.message.media_filename || `media_${currentItem.message.id}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    notification.success('下载已开始');
  };

  // 渲染媒体内容
  const renderMediaContent = (item: MediaItem) => {
    switch (item.type) {
      case 'image':
        return (
          <div className="gallery-image-container">
            <img
              src={item.url}
              alt={item.message.media_filename || '图片'}
              className="gallery-image"
              style={{
                transform: `scale(${imageScale}) rotate(${imageRotation}deg)`,
                transition: 'transform 0.3s ease'
              }}
              onError={(e) => {
                console.error('Gallery image load error:', e);
                notification.error('图片加载失败');
              }}
            />
          </div>
        );

      case 'video':
        return (
          <div className="gallery-video-container">
            <video
              src={item.url}
              className="gallery-video"
              controls
              preload="metadata"
              onPlay={() => setVideoPlaying(true)}
              onPause={() => setVideoPlaying(false)}
              onError={(e) => {
                console.error('Gallery video load error:', e);
                notification.error('视频加载失败');
              }}
            >
              您的浏览器不支持视频播放
            </video>
          </div>
        );

      case 'audio':
        return (
          <div className="gallery-audio-container">
            <audio
              src={item.url}
              controls
              style={{ width: '100%' }}
              onError={(e) => {
                console.error('Gallery audio load error:', e);
                notification.error('音频加载失败');
              }}
            >
              您的浏览器不支持音频播放
            </audio>
          </div>
        );

      default:
        return (
          <div className="gallery-document-container">
            <div className="document-preview">
              <div className="document-icon">📄</div>
              <div className="document-info">
                <div className="document-name">{item.message.media_filename || '文档'}</div>
                <div className="document-size">
                  {item.message.media_size ? `${(item.message.media_size / 1024 / 1024).toFixed(2)} MB` : '未知大小'}
                </div>
              </div>
            </div>
          </div>
        );
    }
  };

  // 渲染工具栏
  const renderToolbar = () => {
    const currentItem = getCurrentItem();
    if (!currentItem) return null;

    return (
      <div className="gallery-toolbar">
        <div className="toolbar-left">
          <Text style={{ color: '#fff' }}>
            {activeIndex + 1} / {mediaItems.length}
          </Text>
        </div>

        <div className="toolbar-center">
          <Space>
            {/* 导航按钮 */}
            <Button
              type="text"
              icon={<LeftOutlined />}
              onClick={goToPrevious}
              disabled={mediaItems.length <= 1}
              className="gallery-btn"
            />
            <Button
              type="text"
              icon={<RightOutlined />}
              onClick={goToNext}
              disabled={mediaItems.length <= 1}
              className="gallery-btn"
            />

            {/* 图片控制 */}
            {currentItem.type === 'image' && (
              <>
                <Button
                  type="text"
                  icon={<ZoomOutOutlined />}
                  onClick={zoomOut}
                  className="gallery-btn"
                />
                <Button
                  type="text"
                  icon={<ZoomInOutlined />}
                  onClick={zoomIn}
                  className="gallery-btn"
                />
                <Button
                  type="text"
                  icon={<RotateRightOutlined />}
                  onClick={rotateImage}
                  className="gallery-btn"
                />
              </>
            )}

            {/* 视频控制 */}
            {currentItem.type === 'video' && (
              <Button
                type="text"
                icon={videoPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                onClick={toggleVideoPlayback}
                className="gallery-btn"
              />
            )}

            {/* 下载按钮 */}
            <Button
              type="text"
              icon={<DownloadOutlined />}
              onClick={downloadCurrentMedia}
              className="gallery-btn"
            />

            {/* 全屏按钮 */}
            <Button
              type="text"
              icon={<FullscreenOutlined />}
              onClick={toggleFullscreen}
              className="gallery-btn"
            />
          </Space>
        </div>

        <div className="toolbar-right">
          <Button
            type="text"
            icon={<CloseOutlined />}
            onClick={onClose}
            className="gallery-btn gallery-close-btn"
          />
        </div>
      </div>
    );
  };

  // 键盘导航
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (!visible) return;

      switch (e.key) {
        case 'Escape':
          onClose();
          break;
        case 'ArrowLeft':
          goToPrevious();
          break;
        case 'ArrowRight':
          goToNext();
          break;
        case 'f':
        case 'F':
          toggleFullscreen();
          break;
        case ' ':
          e.preventDefault();
          if (getCurrentItem()?.type === 'video') {
            toggleVideoPlayback();
          }
          break;
      }
    };

    document.addEventListener('keydown', handleKeyPress);
    return () => document.removeEventListener('keydown', handleKeyPress);
  }, [visible, onClose, goToPrevious, goToNext, toggleFullscreen, getCurrentItem, toggleVideoPlayback]);

  if (!visible || mediaItems.length === 0) {
    return null;
  }

  const currentItem = getCurrentItem();

  return (
    <Modal
      open={visible}
      onCancel={onClose}
      footer={null}
      width="100vw"
      style={{
        top: 0,
        padding: 0,
        maxWidth: 'none'
      }}
      bodyStyle={{
        padding: 0,
        height: '100vh',
        background: 'rgba(0, 0, 0, 0.95)',
        display: 'flex',
        flexDirection: 'column'
      }}
      mask={false}
      closable={false}
      className="media-gallery-modal"
    >
      {/* 工具栏 */}
      {renderToolbar()}

      {/* 媒体内容 */}
      <div className="gallery-content">
        {currentItem && renderMediaContent(currentItem)}
      </div>

      {/* 媒体信息 */}
      <div className="gallery-info">
        <Text style={{ color: '#fff', fontSize: '14px' }}>
          {currentItem?.message.media_filename || `媒体文件 ${currentItem?.message.id}`}
        </Text>
      </div>
    </Modal>
  );
};

export default MediaGallery;