import React, { useState, useEffect } from 'react';
import { Button, Spin, Progress, message as notification, Modal, Card } from 'antd';
import {
  DownloadOutlined,
  PlayCircleOutlined,
  FileImageOutlined,
  FileTextOutlined,
  VideoCameraOutlined,
  AudioOutlined,
  EyeOutlined,
  LoadingOutlined,
  CloseOutlined
} from '@ant-design/icons';
import { TelegramMessage } from '../../types';
import { mediaApi } from '../../services/apiService';
import './MediaDownloadPreview.css';

interface MediaDownloadPreviewProps {
  message: TelegramMessage;
  className?: string;
  compact?: boolean; // 紧凑模式，用于多媒体网格显示
  onPreview?: (mediaPath: string) => void;
  onUpdateDownloadState?: (messageId: number, state: any) => void;
}

interface DownloadState {
  status: 'not_downloaded' | 'downloading' | 'downloaded' | 'error';
  progress?: number;
  error?: string;
  downloadUrl?: string;
  downloadedSize?: number;
  totalSize?: number;
  downloadSpeed?: number; // 下载速度 B/s
  estimatedTimeRemaining?: number; // 预计剩余时间 秒
  lastProgressUpdate?: number; // 上次进度更新时间
}

const MediaDownloadPreview: React.FC<MediaDownloadPreviewProps> = ({
  message,
  className = '',
  compact = false,
  onPreview,
  onUpdateDownloadState
}) => {
  const [downloadState, setDownloadState] = useState<DownloadState>(() => {
    const initialState = {
      status: message.media_downloaded ? 'downloaded' : 'not_downloaded' as DownloadState['status'],
      downloadUrl: message.media_path
    };
    return initialState;
  });

  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null);

  // 状态管理 - 添加缩略图加载失败状态
  const [thumbnailError, setThumbnailError] = useState(false);
  const [forceRefresh, setForceRefresh] = useState(0); // 强制刷新计数器

  // 当下载状态改变时，通知父组件
  useEffect(() => {
    if (onUpdateDownloadState) {
      onUpdateDownloadState(message.message_id, downloadState);
    }
  }, [downloadState, message.message_id, onUpdateDownloadState]);

  // 监听强制刷新，确保下载完成后UI立即更新
  useEffect(() => {
    if (forceRefresh > 0) {
      console.log('Force refresh triggered', { forceRefresh, downloadState });
      // 强制重新评估组件状态
      setTimeout(() => {
        // 延迟执行确保状态更新完成
        console.log('Force refresh completed');
      }, 100);
    }
  }, [forceRefresh, downloadState]);

  // 监听 message 变化，更新下载状态
  useEffect(() => {
    const newStatus = message.media_downloaded ? 'downloaded' : 'not_downloaded';

    // 🔥 重要修复：只在非下载状态时才更新状态，避免打断正在进行的下载
    const shouldUpdateState = (
      downloadState.status !== 'downloading' && // 不打断正在下载的状态
      (downloadState.status !== newStatus || downloadState.downloadUrl !== message.media_path)
    );

    if (shouldUpdateState) {
      console.log('Message state changed, updating download state', {
        messageId: message.message_id,
        oldStatus: downloadState.status,
        newStatus,
        mediaDownloaded: message.media_downloaded,
        mediaPath: message.media_path
      });

      setDownloadState({
        status: newStatus,
        downloadUrl: message.media_path
      });

      // 当下载状态改变时，重置缩略图错误状态
      if (newStatus === 'downloaded') {
        setThumbnailError(false);
      }
    }
  }, [message.media_downloaded, message.media_path, message.message_id]);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [pollInterval]);

  // 获取媒体类型图标
  const getMediaIcon = (mediaType: string) => {
    switch (mediaType) {
      case 'photo':
        return <FileImageOutlined style={{ color: '#52c41a', fontSize: '48px' }} />;
      case 'video':
        return <VideoCameraOutlined style={{ color: '#1890ff', fontSize: '48px' }} />;
      case 'document':
        return <FileTextOutlined style={{ color: '#faad14', fontSize: '48px' }} />;
      case 'audio':
      case 'voice':
        return <AudioOutlined style={{ color: '#722ed1', fontSize: '48px' }} />;
      default:
        return <FileTextOutlined style={{ color: '#8c8c8c', fontSize: '48px' }} />;
    }
  };

  // 格式化文件大小
  const formatFileSize = (bytes?: number) => {
    if (bytes === undefined || bytes === null) {
      return '0 KB'; // 替换"未知大小"为"0 KB"
    }

    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  // 格式化下载速度
  const formatDownloadSpeed = (bytesPerSecond?: number) => {
    if (!bytesPerSecond) return '计算中...';
    const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
    let speed = bytesPerSecond;
    let unitIndex = 0;

    while (speed >= 1024 && unitIndex < units.length - 1) {
      speed /= 1024;
      unitIndex++;
    }

    return `${speed.toFixed(1)} ${units[unitIndex]}`;
  };

  // 格式化剩余时间
  const formatTimeRemaining = (seconds?: number) => {
    if (!seconds || seconds === Infinity) return '计算中...';

    if (seconds < 60) {
      return `${Math.ceil(seconds)}秒`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = Math.ceil(seconds % 60);
      return `${minutes}分${remainingSeconds > 0 ? remainingSeconds + '秒' : ''}`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${hours}小时${minutes > 0 ? minutes + '分' : ''}`;
    }
  };

  // Note: calculateDownloadStats function removed as it's no longer used
  // The backend now provides download speed and estimated time directly

  // 取消下载
  const handleCancelDownload = async () => {
    try {
      // 清理前端定时器
      if (pollInterval) {
        clearInterval(pollInterval);
        setPollInterval(null);
      }

      // 调用后端API取消下载
      const response = await mediaApi.cancelDownload(message.message_id);

      if (response.status === 'cancelled') {
        notification.success('下载已取消');
      } else {
        console.warn('后端取消下载失败，但前端状态已重置');
        notification.info('下载已取消，但后端可能仍在处理');
      }
    } catch (error) {
      console.error('取消下载时发生错误:', error);
      notification.info('下载已取消');
    } finally {
      // 重置前端状态
      setDownloadState({
        status: 'not_downloaded',
        progress: 0
      });
    }
  };

  // 已移除模拟进度功能，现在使用后端真实进度数据

  // 下载媒体文件
  const handleDownload = async () => {
    if (downloadState.status === 'downloading') return;

    console.log('Starting download for message:', message.message_id);
    const initialDownloadState = {
      status: 'downloading' as const,
      progress: 0,
      lastProgressUpdate: Date.now()
    };

    console.log('Setting initial download state:', initialDownloadState);
    setDownloadState(initialDownloadState);

    try {
      // 启动下载任务
      const response = await mediaApi.downloadMedia(message.message_id);

      if (response.status === 'already_downloaded') {
        setDownloadState({
          status: 'downloaded',
          downloadUrl: response.download_url
        });
        notification.success('文件已存在，无需重新下载');
        return;
      }

      // 开始轮询下载状态
      const newPollInterval = setInterval(async () => {
        try {
          const statusResponse = await mediaApi.getDownloadStatus(message.message_id);

          if (statusResponse.status === 'downloaded') {
            const newDownloadState = {
              status: 'downloaded' as const,
              downloadUrl: statusResponse.download_url,
              progress: 100,
              downloadedSize: statusResponse.downloaded_size || statusResponse.file_size,
              totalSize: statusResponse.total_size || statusResponse.file_size
            };

            setDownloadState(newDownloadState);

            // 重置缩略图错误状态，允许重新尝试显示
            setThumbnailError(false);

            // 强制组件重新渲染以确保UI更新
            setForceRefresh(prev => prev + 1);

            // 通知父组件更新消息状态
            if (onUpdateDownloadState) {
              onUpdateDownloadState(message.message_id, {
                ...newDownloadState,
                media_downloaded: true,
                media_path: statusResponse.download_url
              });
            }

            console.log('Download completed successfully', {
              messageId: message.message_id,
              downloadUrl: statusResponse.download_url,
              newState: newDownloadState
            });

            notification.success('下载完成，可以预览了！');
            clearInterval(newPollInterval);
            setPollInterval(null);
          } else if (statusResponse.status === 'download_failed') {
            setDownloadState({
              status: 'error',
              error: statusResponse.error || '下载失败'
            });
            notification.error('下载失败: ' + (statusResponse.error || '未知错误'));
            clearInterval(newPollInterval);
            setPollInterval(null);
          } else if (statusResponse.status === 'downloading') {
            // 使用后端返回的真实进度数据
            const newState = {
              status: 'downloading' as const,
              progress: statusResponse.progress || 0,
              downloadedSize: statusResponse.downloaded_size || 0,
              totalSize: statusResponse.total_size || message.media_size || 0,
              downloadSpeed: statusResponse.download_speed || 0,
              estimatedTimeRemaining: statusResponse.estimated_time_remaining || 0,
              lastProgressUpdate: Date.now()
            };

            console.log('Updating download progress:', newState);
            setDownloadState(prevState => {
              const updatedState = { ...prevState, ...newState };
              console.log('Download state will be updated from', prevState, 'to', updatedState);
              return updatedState;
            });
          }
          // 继续轮询其他状态
        } catch (error) {
          console.error('轮询下载状态失败:', error);
          setDownloadState({
            status: 'error',
            error: '获取下载状态失败'
          });
          clearInterval(newPollInterval);
          setPollInterval(null);
        }
      }, 1000); // 每1秒轮询一次，更频繁的更新

      setPollInterval(newPollInterval);

    } catch (error: any) {
      console.error('下载请求失败:', error);
      setDownloadState({
        status: 'error',
        error: error.response?.data?.detail || '下载请求失败'
      });
      notification.error('下载失败: ' + (error.response?.data?.detail || '网络错误'));
    }
  };

  // 预览媒体
  const handlePreview = () => {
    console.log('handlePreview called', {
      messageId: message.message_id,
      downloadState,
      message_media_downloaded: message.media_downloaded,
      message_media_path: message.media_path
    });

    // 检查是否有可用的媒体URL - 优先使用downloadState
    const hasDownloadUrl = !!downloadState.downloadUrl;
    const hasMessageMediaPath = message.media_downloaded && message.media_path;
    const hasMediaUrl = hasDownloadUrl || hasMessageMediaPath;

    // 优先使用downloadState中的URL，然后使用message中的path
    const mediaUrlForPreview = downloadState.downloadUrl || message.media_path;

    console.log('Preview check result', {
      hasDownloadUrl,
      hasMessageMediaPath,
      hasMediaUrl,
      mediaUrlForPreview,
      downloadStatus: downloadState.status
    });

    if (hasMediaUrl && mediaUrlForPreview) {
      console.log('Starting preview with URL:', mediaUrlForPreview);
      if (onPreview) {
        onPreview(mediaUrlForPreview);
      } else {
        // 打开预览模态框
        setShowPreviewModal(true);
      }
    } else {
      console.log('No media URL available, starting download');
      // 需要先下载
      handleDownload();
    }
  };

  // 获取完整的媒体URL（修复重复media路径问题）
  const getFullMediaUrl = (path: string) => {
    if (!path) return '';

    // 如果已经是完整URL，直接返回
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path;
    }

    // 如果路径以 /media/ 开头，直接返回（已经是完整路径）
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

    // 对于其他路径，尝试构建完整URL
    // 首先尝试作为媒体文件路径
    if (!path.startsWith('/')) {
      const result = `/media/${path}`;
      return result;
    }

    // 如果是其他相对路径，使用API基础URL
    const apiBase = process.env.REACT_APP_API_URL || '';
    const result = `${apiBase}${path}`;
    return result;
  };

  // 渲染预览内容
  const renderPreviewContent = () => {
    if (!downloadState.downloadUrl) return null;

    const fullUrl = getFullMediaUrl(downloadState.downloadUrl);

    switch (message.media_type) {
      case 'photo':
        return (
          <img
            src={fullUrl}
            alt={message.media_filename || '图片'}
            style={{ maxWidth: '100%', maxHeight: '70vh' }}
            onError={(e) => {
              console.error('Image load error in preview modal:', e, 'URL:', fullUrl);
              // 可以设置错误处理，比如显示错误提示
            }}
            onLoad={() => {
              console.log('Image loaded successfully in preview modal');
            }}
          />
        );
      case 'video':
        return (
          <video
            controls
            style={{ maxWidth: '100%', maxHeight: '70vh' }}
            preload="metadata"
            onError={(e) => {
              console.error('Video load error in preview modal:', e, 'URL:', fullUrl);
            }}
            onLoadedData={() => {
              console.log('Video loaded successfully in preview modal');
            }}
          >
            <source src={fullUrl} />
            您的浏览器不支持视频播放
          </video>
        );
      case 'audio':
      case 'voice':
        return (
          <audio controls style={{ width: '100%' }}>
            <source src={fullUrl} />
            您的浏览器不支持音频播放
          </audio>
        );
      default:
        return (
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <FileTextOutlined style={{ fontSize: '64px', color: '#8c8c8c' }} />
            <div style={{ marginTop: '16px' }}>
              <a href={fullUrl} download={message.media_filename} target="_blank" rel="noopener noreferrer">
                <Button type="primary" icon={<DownloadOutlined />}>
                  下载文件
                </Button>
              </a>
            </div>
          </div>
        );
    }
  };

  // 渲染下载状态
  const renderDownloadStatus = () => {
    console.log('renderDownloadStatus called', {
      messageId: message.message_id,
      downloadStatus: downloadState.status,
      progress: downloadState.progress,
      downloadedSize: downloadState.downloadedSize,
      totalSize: downloadState.totalSize
    });

    // 首先检查是否正在下载，优先显示进度条
    if (downloadState.status === 'downloading') {
      return (
        <div className="download-progress">
          <Card size="small" style={{ width: '100%' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ marginBottom: 8 }}>
                <LoadingOutlined style={{ fontSize: 16, color: '#1890ff' }} spin />
                <span style={{ marginLeft: 8, fontWeight: 500 }}>下载中...</span>
              </div>

              {/* 进度条 */}
              <Progress
                percent={downloadState.progress || 0}
                size="small"
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
                trailColor="#f5f5f5"
                style={{ marginBottom: 8 }}
              />

              {/* 下载信息 */}
              <div className="download-info">
                <span>
                  {downloadState.downloadedSize && downloadState.totalSize ? (
                    `${formatFileSize(downloadState.downloadedSize)} / ${formatFileSize(downloadState.totalSize)}`
                  ) : (
                    `${downloadState.progress || 0}%`
                  )}
                </span>
                <span className="download-speed">
                  {downloadState.downloadSpeed && downloadState.downloadSpeed > 0 ? (
                    formatDownloadSpeed(downloadState.downloadSpeed)
                  ) : (
                    '计算中...'
                  )}
                </span>
              </div>

              {/* 预计剩余时间 */}
              {downloadState.estimatedTimeRemaining && downloadState.estimatedTimeRemaining > 0 && (
                <div className="remaining-time">
                  剩余时间: {formatTimeRemaining(downloadState.estimatedTimeRemaining)}
                </div>
              )}

              {/* 取消下载按钮 */}
              <div style={{ marginTop: 8, textAlign: 'center' }}>
                <Button
                  size="small"
                  type="text"
                  danger
                  icon={<CloseOutlined />}
                  onClick={handleCancelDownload}
                  style={{ fontSize: '11px' }}
                >
                  取消下载
                </Button>
              </div>
            </div>
          </Card>
        </div>
      );
    }

    // 检查是否已下载完成
    const hasDownloadedFile = downloadState.downloadUrl || (message.media_downloaded && message.media_path);
    const isDownloadStatusComplete = downloadState.status === 'downloaded';
    const isActuallyDownloaded = hasDownloadedFile || isDownloadStatusComplete;

    // 如果文件已下载，显示预览和下载按钮
    if (isActuallyDownloaded) {
      const mediaUrlForDownload = downloadState.downloadUrl || message.media_path;
      const fullMediaUrl = mediaUrlForDownload ? getFullMediaUrl(mediaUrlForDownload) : null;

      return (
        <div className="download-actions downloaded-actions">
          <Button
            type="primary"
            icon={<EyeOutlined />}
            onClick={handlePreview}
            size="small"
            style={{
              background: 'linear-gradient(135deg, #52c41a 0%, #389e0d 100%)',
              border: 'none'
            }}
          >
            预览
          </Button>
          {fullMediaUrl && (
            <Button
              icon={<DownloadOutlined />}
              href={fullMediaUrl}
              download={message.media_filename || `media_${message.message_id}`}
              target="_blank"
              size="small"
              style={{
                borderColor: '#52c41a',
                color: '#52c41a'
              }}
            >
              保存
            </Button>
          )}
          <div className="download-status-indicator">
            ✓ 已下载
          </div>
        </div>
      );
    }

    switch (downloadState.status) {
      case 'error':
        return (
          <div className="download-error">
            <Card size="small" style={{ backgroundColor: '#fff2f0', borderColor: '#ffccc7' }}>
              <div style={{ color: '#ff4d4f', marginBottom: 8, fontSize: '12px', textAlign: 'center' }}>
                ❌ {downloadState.error}
              </div>
              <div style={{ textAlign: 'center' }}>
                <Button
                  size="small"
                  type="primary"
                  danger
                  onClick={handleDownload}
                  icon={<DownloadOutlined />}
                >
                  重试下载
                </Button>
              </div>
            </Card>
          </div>
        );

      default:
        return (
          <div className="download-placeholder">
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={handleDownload}
              size="small"
              style={{
                background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)',
                border: 'none',
                boxShadow: '0 2px 4px rgba(24, 144, 255, 0.2)'
              }}
            >
              下载查看
            </Button>
          </div>
        );
    }
  };

  // 获取缩略图URL - 优先使用新的缩略图URL字段
  const getThumbnailUrl = () => {
    // 如果文件已下载，优先使用下载的文件作为缩略图
    if (downloadState.downloadUrl) {
      console.log('Using downloaded file URL for thumbnail:', downloadState.downloadUrl);
      return getFullMediaUrl(downloadState.downloadUrl);
    }

    if (message.media_downloaded && message.media_path) {
      console.log('Using media path URL for thumbnail:', message.media_path);
      return getFullMediaUrl(message.media_path);
    }

    // 最后再尝试使用缩略图URL（可能不可用）
    if (message.media_thumbnail_url) {
      console.log('Using thumbnail URL (fallback):', message.media_thumbnail_url);
      return message.media_thumbnail_url;
    }

    return null;
  };

  // 渲染媒体缩略图（对于已下载的图片和视频）
  const renderMediaThumbnail = () => {
    const thumbnailUrl = getThumbnailUrl();
    // 检查是否有可用的媒体URL（缩略图或已下载）
    const hasMediaUrl = thumbnailUrl || downloadState.downloadUrl || (message.media_downloaded && message.media_path);
    const isFileDownloaded = downloadState.downloadUrl || (message.media_downloaded && message.media_path);

    // 如果没有任何媒体URL，显示默认图标
    if (!hasMediaUrl) {
      return (
        <div className="media-icon">
          {getMediaIcon(message.media_type || 'document')}
        </div>
      );
    }

    // 如果文件已下载，直接显示预览（不依赖缩略图API）
    if (isFileDownloaded && ['photo', 'video'].includes(message.media_type || '')) {
      const fileUrl = downloadState.downloadUrl || message.media_path;
      if (fileUrl) {
        const fullFileUrl = getFullMediaUrl(fileUrl);

        switch (message.media_type) {
          case 'photo':
            return (
              <div className="media-thumbnail downloaded-media" onClick={handlePreview} style={{ cursor: 'pointer' }}>
                <img
                  src={fullFileUrl}
                  alt={message.media_filename || '图片'}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    borderRadius: '8px'
                  }}
                  onError={(e) => {
                    console.error('Downloaded image load error:', e, 'URL:', fullFileUrl);
                    // 回退到图标显示
                    setThumbnailError(true);
                  }}
                  onLoad={() => {
                    console.log('Downloaded image loaded successfully:', fullFileUrl);
                    setThumbnailError(false);
                  }}
                />
                <div className="thumbnail-overlay">
                  <EyeOutlined style={{ color: 'white', fontSize: '16px' }} />
                  <div className="downloaded-indicator">已下载</div>
                </div>
              </div>
            );
          case 'video':
            return (
              <div className="media-thumbnail downloaded-media" onClick={handlePreview} style={{ cursor: 'pointer' }}>
                <video
                  src={fullFileUrl}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    borderRadius: '6px'
                  }}
                  muted
                  preload="metadata"
                  onError={(e) => {
                    console.error('Downloaded video load error:', e, 'URL:', fullFileUrl);
                    setThumbnailError(true);
                  }}
                  onLoadedData={() => {
                    console.log('Downloaded video loaded successfully:', fullFileUrl);
                    setThumbnailError(false);
                  }}
                />
                <div className="thumbnail-overlay">
                  <PlayCircleOutlined style={{ color: 'white', fontSize: '20px' }} />
                  <div className="downloaded-indicator">已下载</div>
                </div>
              </div>
            );
        }
      }
    }

    // 如果缩略图已失败或文件未下载，尝试使用缩略图URL
    if (!thumbnailError && thumbnailUrl && ['photo', 'video'].includes(message.media_type || '')) {
      switch (message.media_type) {
        case 'photo':
          return (
            <div className="media-thumbnail" onClick={handlePreview} style={{ cursor: 'pointer' }}>
              <img
                src={thumbnailUrl}
                alt={message.media_filename || '图片'}
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  borderRadius: '8px'
                }}
                onError={(e) => {
                  console.error('Thumbnail load error:', e, 'URL:', thumbnailUrl);
                  setThumbnailError(true);
                }}
                onLoad={() => {
                  console.log('Thumbnail loaded successfully:', thumbnailUrl);
                  setThumbnailError(false);
                }}
              />
              <div className="thumbnail-overlay">
                <EyeOutlined style={{ color: 'white', fontSize: '16px' }} />
              </div>
            </div>
          );
        case 'video':
          return (
            <div className="media-thumbnail" onClick={handlePreview} style={{ cursor: 'pointer' }}>
              <video
                src={thumbnailUrl}
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  borderRadius: '6px'
                }}
                muted
                preload="metadata"
                onError={(e) => {
                  console.error('Video thumbnail load error:', e, 'URL:', thumbnailUrl);
                  setThumbnailError(true);
                }}
                onLoadedData={() => {
                  console.log('Video thumbnail loaded successfully:', thumbnailUrl);
                  setThumbnailError(false);
                }}
              />
              <div className="thumbnail-overlay">
                <PlayCircleOutlined style={{ color: 'white', fontSize: '20px' }} />
              </div>
            </div>
          );
      }
    }

    // 最终回退：显示带错误提示的图标
    return (
      <div className="media-icon error-fallback" onClick={handlePreview} style={{ cursor: 'pointer' }}>
        {getMediaIcon(message.media_type || 'document')}
        {thumbnailError && (
          <div className="error-overlay">
            <small>点击加载原图</small>
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      <div
        className={`media-download-preview ${compact ? 'compact' : ''} ${className}`}
        key={`media-${message.message_id}-${forceRefresh}`}
      >
        {/* 媒体信息 */}
        <div className="media-info">
          {renderMediaThumbnail()}

          <div className="media-details">
            <div
              className="media-filename"
              title={message.media_filename || `${message.media_type}_${message.message_id}`} // 悬浮显示完整文件名
            >
              {message.media_filename || `${message.media_type}_${message.message_id}`}
            </div>
            <div className="media-meta">
              <span className="media-size">{formatFileSize(message.media_size)}</span>
              {message.media_type && (
                <span className="media-type">
                  {message.media_type.toUpperCase()}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* 下载状态和操作 */}
        <div className="media-actions">
          {renderDownloadStatus()}
        </div>
      </div>

      {/* 预览模态框 */}
      <Modal
        title={message.media_filename || '媒体预览'}
        open={showPreviewModal}
        onCancel={() => setShowPreviewModal(false)}
        footer={null}
        width="90%"
        style={{ maxWidth: '800px' }}
        centered
      >
        {renderPreviewContent()}
      </Modal>
    </>
  );
};

export default MediaDownloadPreview;