import React, { useState, useRef, useEffect } from 'react';
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

  // 如果路径以 /media/ 开头，直接返回（已经是完整路径）
  if (path.startsWith('/media/')) {
    return path;
  }

  // 如果路径以 media/ 开头，添加前导斜杠
  if (path.startsWith('media/')) {
    return `/${path}`;
  }

  // 对于其他路径，尝试构建完整URL
  // 首先尝试作为媒体文件路径
  if (!path.startsWith('/')) {
    return `/media/${path}`;
  }

  // 如果是其他相对路径，使用API基础URL
  const apiBase = process.env.REACT_APP_API_URL || '';
  return `${apiBase}${path}`;
};

// 格式化文件大小
const formatFileSize = (bytes: number | string | undefined) => {
  if (bytes === undefined || bytes === null) {
    return '0 KB';  // 替换未知大小为"0 KB"
  }

  if (typeof bytes === 'string') {
    const parsed = parseFloat(bytes);
    if (isNaN(parsed)) return '0 KB';
    bytes = parsed;
  }

  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
};

// 格式化视频时长
const formatDuration = (seconds: number): string => {
  if (isNaN(seconds)) return '00:00';

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  } else {
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
};

interface MediaPreviewProps {
  messageId: number; // 消息ID，用于下载状态追踪
  url: string;
  type: 'image' | 'video';
  filename?: string;
  size?: string | number;
  downloaded?: boolean; // 是否已下载
  duration?: number; // 添加视频时长属性
  className?: string;
}

const MediaPreview: React.FC<MediaPreviewProps> = ({
  messageId,
  url,
  type,
  filename,
  size,
  downloaded = false,
  className,
  duration: initialDuration // 接收外部传入的时长
}) => {
  const [previewVisible, setPreviewVisible] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [loading, setLoading] = useState(false);
  const [alternativeUrls, setAlternativeUrls] = useState<string[]>([]);
  const [currentUrlIndex, setCurrentUrlIndex] = useState(0);
  const [videoDuration, setVideoDuration] = useState<number | undefined>(initialDuration);
  const videoRef = useRef<HTMLVideoElement>(null);

  // 当视频元数据加载完成时获取时长
  const handleVideoMetadata = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    const video = e.currentTarget;
    if (video.duration && !isNaN(video.duration)) {
      setVideoDuration(video.duration);
      console.log('Video duration detected:', video.duration);
    }
  };

  // 下载状态管理
  const {
    downloadStatus,
    isLoading: isDownloading,
    startDownload,
    retryDownload
  } = useMediaDownload({
    messageId,
    autoRefresh: true, // 始终自动刷新状态，以获取准确的下载状态
    onDownloadComplete: (filePath) => {
      message.success('文件下载完成');
      // 可以在这里更新本地状态或触发其他操作
    },
    onDownloadError: (error) => {
      message.error(`下载失败: ${error}`);
    }
  });

  // 生成多个可能的URL
  const generateAlternativeUrls = (originalUrl: string) => {
    const urls = [getMediaUrl(originalUrl)];

    // 如果原始URL不是以/media/开头，尝试添加
    if (!originalUrl.startsWith('/media/') && !originalUrl.startsWith('media/')) {
      urls.push(`/media/${originalUrl}`);
    }

    // 尝试API路径
    const apiBase = process.env.REACT_APP_API_URL || '';
    if (apiBase) {
      urls.push(`${apiBase}/media/${originalUrl.replace(/^\/media\//, '')}`);
      urls.push(`${apiBase}/${originalUrl.startsWith('/') ? originalUrl.slice(1) : originalUrl}`);
    }

    return Array.from(new Set(urls)); // 去重
  };

  // 确定要使用的媒体URL
  // 优先使用已下载文件的URL，然后是备选URLs，最后是原始URL
  const getDisplayUrl = () => {
    // 优先使用下载状态中的URL
    if (downloadStatus.downloadUrl) {
      console.log('Using downloadStatus.downloadUrl:', downloadStatus.downloadUrl);
      return downloadStatus.downloadUrl;
    }
    if (downloadStatus.filePath) {
      const filePathUrl = getMediaUrl(downloadStatus.filePath);
      console.log('Using downloadStatus.filePath as URL:', filePathUrl);
      return filePathUrl;
    }
    // 如果没有下载状态URL，使用备选URLs
    if (alternativeUrls.length > 0) {
      console.log('Using alternative URL:', alternativeUrls[currentUrlIndex]);
      return alternativeUrls[currentUrlIndex];
    }
    // 最后使用原始URL
    const originalUrl = getMediaUrl(url);
    console.log('Using original URL:', originalUrl);
    return originalUrl;
  };

  const mediaUrl = getDisplayUrl();
  const formattedSize = size ? formatFileSize(size) : undefined;

  // 初始化备选URLs
  React.useEffect(() => {
    if (url && alternativeUrls.length === 0) {
      setAlternativeUrls(generateAlternativeUrls(url));
    }
  }, [url, alternativeUrls.length]);

  // 判断是否应该显示媒体内容
  // 1. 如果传入downloaded=true，直接显示
  // 2. 如果downloadStatus显示已下载，也显示
  // 3. 如果文件路径看起来是本地文件(包含media/)，也显示
  // 4. 如果downloadStatus有filePath或downloadUrl，也显示（表示文件已存在）
  const isLocalFile = url && (url.includes('media/') || url.startsWith('/media/'));
  const hasDownloadedFile = downloadStatus.filePath || downloadStatus.downloadUrl;
  const shouldShowMedia = downloaded ||
    downloadStatus.status === 'downloaded' ||
    isLocalFile ||
    hasDownloadedFile;

  // 调试输出
  React.useEffect(() => {
    console.log('MediaPreview debug:', {
      messageId,
      url,
      downloaded,
      downloadStatus,
      isLocalFile,
      hasDownloadedFile,
      shouldShowMedia,
      mediaUrl
    });
  }, [messageId, url, downloaded, downloadStatus, isLocalFile, hasDownloadedFile, shouldShowMedia, mediaUrl]);

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
                onLoadStart={() => setLoading(true)}
                onLoad={() => {
                  setLoading(false);
                  setImageError(false);
                }}
                onError={(e) => {
                  console.error('Image load error:', e, 'URL:', mediaUrl);

                  // 尝试下一个备选URL
                  if (currentUrlIndex < alternativeUrls.length - 1) {
                    setCurrentUrlIndex(prev => prev + 1);
                    console.log('Trying alternative URL:', alternativeUrls[currentUrlIndex + 1]);
                  } else {
                    setImageError(true);
                    setLoading(false);
                  }
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

              {/* 加载状态指示器 */}
              {loading && (
                <div className="media-loading-indicator" style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: 'rgba(0,0,0,0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 8
                }}>
                  <div style={{ color: 'white' }}>加载中...</div>
                </div>
              )}

              {/* 错误状态指示器 */}
              {imageError && (
                <div className="media-error-indicator" style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: 'rgba(255,0,0,0.1)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 8,
                  border: '1px dashed #ff4d4f'
                }}>
                  <FileImageOutlined style={{ fontSize: 24, color: '#ff4d4f', marginBottom: 4 }} />
                  <div style={{ color: '#ff4d4f', fontSize: 12 }}>加载失败</div>
                </div>
              )}

              {!loading && !imageError && (
                <div className="media-overlay">
                  <EyeOutlined style={{ fontSize: 24, color: 'white' }} />
                </div>
              )}
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
              {/* 只有在未下载或下载失败时才显示下载按钮 */}
              {(!shouldShowMedia || downloadStatus.status === 'download_failed') && (
                <Button
                  type="text"
                  icon={<DownloadOutlined />}
                  size="small"
                  onClick={() => startDownload()}
                  loading={isDownloading}
                >
                  {downloadStatus.status === 'download_failed' ? '重新下载' : '下载'}
                </Button>
              )}
              {/* 对于已下载的文件，提供重新下载选项 */}
              {shouldShowMedia && downloadStatus.status === 'downloaded' && (
                <Button
                  type="text"
                  icon={<DownloadOutlined />}
                  size="small"
                  onClick={() => startDownload(true)}
                  loading={isDownloading}
                  style={{ color: '#8c8c8c' }}
                >
                  重新下载
                </Button>
              )}
            </Space>
          </div>
        )}

        {shouldShowMedia && (
          <Modal
            open={previewVisible}
            footer={null}
            onCancel={() => setPreviewVisible(false)}
            width="90%"
            style={{ maxWidth: 1200, top: 20 }}
            centered
            className="media-preview-modal"
          >
            <div style={{ textAlign: 'center' }}>
              <Image
                src={mediaUrl}
                alt={filename}
                style={{ width: '100%', maxHeight: '80vh', objectFit: 'contain' }}
                preview={{
                  mask: '点击放大查看',
                  maskClassName: 'image-zoom-mask'
                }}
              />
              <div style={{ marginTop: 16, color: '#8c8c8c', fontSize: 12 }}>
                {filename && <div>{filename}</div>}
                <div>点击图片可放大查看</div>
              </div>
            </div>
          </Modal>
        )}
      </div>
    );
  }

  if (type === 'video') {
    return (
      <div className={`media-preview video-preview ${className || ''}`}>
        <div className="video-thumbnail" onClick={() => {
          console.log('Open gallery for:', mediaUrl);
          if (shouldShowMedia) {
            setPreviewVisible(true);
          }
        }} style={{ position: 'relative', cursor: shouldShowMedia ? 'pointer' : 'default' }}>
          {shouldShowMedia ? (
            <>
              <video
                ref={videoRef}
                src={mediaUrl}
                style={{ maxWidth: 200, maxHeight: 150, objectFit: 'cover', borderRadius: 8 }}
                muted
                preload="metadata"
                playsInline
                onLoadStart={() => setLoading(true)}
                onLoadedData={() => {
                  setLoading(false);
                  setImageError(false);
                }}
                onCanPlay={() => {
                  console.log('Video can play:', mediaUrl);
                }}
                onError={(e) => {
                  console.error('Video load error:', e);
                  console.error('Video URL:', mediaUrl);
                  console.error('Video element:', e.target);

                  // 检查网络状态
                  if (!navigator.onLine) {
                    console.error('Network is offline');
                  }

                  // 尝试下一个备选URL
                  if (currentUrlIndex < alternativeUrls.length - 1) {
                    setCurrentUrlIndex(prev => prev + 1);
                    console.log('Trying alternative video URL:', alternativeUrls[currentUrlIndex + 1]);
                  } else {
                    setImageError(true);
                    setLoading(false);
                    console.error('All video URLs failed to load');
                  }
                }}
                onLoadedMetadata={(e) => {
                  const video = e.target as HTMLVideoElement;
                  console.log('Video metadata loaded:', {
                    duration: video.duration,
                    videoWidth: video.videoWidth,
                    videoHeight: video.videoHeight,
                    readyState: video.readyState
                  });
                  // 获取视频时长
                  handleVideoMetadata(e as React.SyntheticEvent<HTMLVideoElement>);
                }}
              >
                {/* 添加多种视频格式支持 */}
                <source src={mediaUrl} type="video/mp4" />
                <source src={mediaUrl} type="video/webm" />
                <source src={mediaUrl} type="video/ogg" />
                您的浏览器不支持视频播放
              </video>

              {/* 类型指示器 */}
              <div className="media-type-icon">
                <VideoCameraOutlined />
                <span className="media-type-text">VIDEO</span>
              </div>

              {/* 时长指示器 - 新增 */}
              {videoDuration && (
                <div className="media-duration-indicator">
                  {formatDuration(videoDuration)}
                </div>
              )}

              {/* 大小指示器 */}
              {formattedSize && (
                <div className="media-size-indicator">
                  {formattedSize}
                </div>
              )}

              {/* 加载状态指示器 */}
              {loading && (
                <div className="media-loading-indicator" style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: 'rgba(0,0,0,0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 8
                }}>
                  <div style={{ color: 'white' }}>加载中...</div>
                </div>
              )}

              {/* 错误状态指示器 */}
              {imageError && (
                <div className="media-error-indicator" style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: 'rgba(255,0,0,0.1)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 8,
                  border: '1px dashed #ff4d4f'
                }}>
                  <VideoCameraOutlined style={{ fontSize: 24, color: '#ff4d4f', marginBottom: 4 }} />
                  <div style={{ color: '#ff4d4f', fontSize: 12 }}>加载失败</div>
                </div>
              )}

              {!loading && !imageError && (
                <div className="media-overlay">
                  <PlayCircleOutlined style={{ fontSize: 32, color: 'white' }} />
                </div>
              )}
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

        {(filename || size || videoDuration) && (
          <div className="media-info">
            {filename && <div className="media-filename">{filename}</div>}
            <div className="media-meta">
              {formattedSize && <span className="media-size">{formattedSize}</span>}
              {videoDuration && <span className="media-duration">{formatDuration(videoDuration)}</span>}
            </div>
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
              {/* 只有在未下载或下载失败时才显示下载按钮 */}
              {(!shouldShowMedia || downloadStatus.status === 'download_failed') && (
                <Button
                  type="text"
                  icon={<DownloadOutlined />}
                  size="small"
                  onClick={() => startDownload()}
                  loading={isDownloading}
                >
                  {downloadStatus.status === 'download_failed' ? '重新下载' : '下载'}
                </Button>
              )}
              {/* 对于已下载的文件，提供重新下载选项 */}
              {shouldShowMedia && downloadStatus.status === 'downloaded' && (
                <Button
                  type="text"
                  icon={<DownloadOutlined />}
                  size="small"
                  onClick={() => startDownload(true)}
                  loading={isDownloading}
                  style={{ color: '#8c8c8c' }}
                >
                  重新下载
                </Button>
              )}
            </Space>
          </div>
        )}

        {shouldShowMedia && (
          <Modal
            open={previewVisible}
            footer={null}
            onCancel={() => setPreviewVisible(false)}
            width="90%"
            style={{ maxWidth: 1200, top: 20 }}
            centered
            className="video-preview-modal"
          >
            <div style={{ textAlign: 'center' }}>
              <video
                src={mediaUrl}
                controls
                style={{ width: '100%', maxHeight: '80vh', borderRadius: '8px' }}
                controlsList="nodownload"
                playsInline
                preload="metadata"
                autoPlay={false}
                onError={(e) => {
                  console.error('Video playback error:', e, 'URL:', mediaUrl);
                  const video = e.target as HTMLVideoElement;
                  console.error('Video element details:', {
                    readyState: video.readyState,
                    networkState: video.networkState,
                    error: video.error
                  });

                  // 检查文件是否存在
                  fetch(mediaUrl, { method: 'HEAD' })
                    .then(response => {
                      console.log('Video file check:', {
                        url: mediaUrl,
                        status: response.status,
                        contentType: response.headers.get('content-type'),
                        contentLength: response.headers.get('content-length')
                      });

                      if (response.status !== 200) {
                        message.error(`视频文件不存在或无法访问 (状态码: ${response.status})`);
                      }
                    })
                    .catch(fetchError => {
                      console.error('Failed to check video file:', fetchError);
                      message.error('无法访问视频文件，请检查网络连接');
                    });

                  // 尝试下一个备选URL
                  if (currentUrlIndex < alternativeUrls.length - 1) {
                    setCurrentUrlIndex(prev => prev + 1);
                    console.log('Trying alternative URL for video playback:', alternativeUrls[currentUrlIndex + 1]);
                  } else {
                    message.error('视频播放失败，所有备选URL都无法加载');
                  }
                }}
                onLoadedData={() => {
                  console.log('Video loaded successfully for playback');
                  message.success('视频加载完成，可以播放');
                }}
                onCanPlay={() => {
                  console.log('Video can play in modal');
                }}
                onLoadedMetadata={(e) => {
                  const video = e.target as HTMLVideoElement;
                  console.log('Modal video metadata:', {
                    duration: video.duration,
                    videoWidth: video.videoWidth,
                    videoHeight: video.videoHeight,
                    readyState: video.readyState,
                    src: video.src
                  });
                  // 获取视频时长
                  handleVideoMetadata(e as React.SyntheticEvent<HTMLVideoElement>);
                }}
              >
                您的浏览器不支持视频播放。请尝试使用最新版本的 Chrome、Firefox 或 Safari 浏览器。
              </video>
              <div style={{ marginTop: 16, color: '#8c8c8c', fontSize: 12 }}>
                {filename && <div style={{ marginBottom: 4 }}>{filename}</div>}
                <div className="media-details">
                  {formattedSize && <span>文件大小: {formattedSize}</span>}
                  {videoDuration && <span>时长: {formatDuration(videoDuration)}</span>}
                </div>
                <div style={{ marginTop: 8, fontSize: 11 }}>
                  如果视频无法播放，请检查文件格式是否为 MP4、WebM 或 OGG
                </div>
              </div>
            </div>
          </Modal>
        )}
      </div>
    );
  }

  return null;
};

export default MediaPreview;