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
  LoadingOutlined
} from '@ant-design/icons';
import { TelegramMessage } from '../../types';
import apiService, { mediaApi } from '../../services/apiService';
import './MediaDownloadPreview.css';

interface MediaDownloadPreviewProps {
  message: TelegramMessage;
  className?: string;
  onPreview?: (mediaPath: string) => void;
}

interface DownloadState {
  status: 'not_downloaded' | 'downloading' | 'downloaded' | 'error';
  progress?: number;
  error?: string;
  downloadUrl?: string;
  downloadedSize?: number;
  totalSize?: number;
}

const MediaDownloadPreview: React.FC<MediaDownloadPreviewProps> = ({
  message,
  className = '',
  onPreview
}) => {
  const [downloadState, setDownloadState] = useState<DownloadState>(() => {
    const initialState = {
      status: message.media_downloaded ? 'downloaded' : 'not_downloaded' as DownloadState['status'],
      downloadUrl: message.media_path
    };
    console.log('MediaDownloadPreview - initial state', {
      messageId: message.id,
      mediaDownloaded: message.media_downloaded,
      mediaPath: message.media_path,
      initialState
    });
    return initialState;
  });
  
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  
  // 监听 message 变化，更新下载状态
  useEffect(() => {
    console.log('MediaDownloadPreview - message updated', {
      messageId: message.id,
      mediaDownloaded: message.media_downloaded,
      mediaPath: message.media_path,
      currentDownloadState: downloadState
    });
    
    const newStatus = message.media_downloaded ? 'downloaded' : 'not_downloaded';
    if (downloadState.status !== newStatus || downloadState.downloadUrl !== message.media_path) {
      console.log('MediaDownloadPreview - updating download state', {
        oldStatus: downloadState.status,
        newStatus,
        oldUrl: downloadState.downloadUrl,
        newUrl: message.media_path
      });
      setDownloadState({
        status: newStatus,
        downloadUrl: message.media_path
      });
    }
  }, [message.media_downloaded, message.media_path, message.id]);

  // 获取媒体类型图标
  const getMediaIcon = (mediaType: string) => {
    const iconProps = { size: 48 };
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
    if (!bytes) return '未知大小';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  // 下载媒体文件
  const handleDownload = async () => {
    if (downloadState.status === 'downloading') return;
    
    setDownloadState({ status: 'downloading', progress: 0 });
    
    try {
      // 启动下载任务
      const response = await mediaApi.downloadMedia(message.id);
      
      if (response.status === 'already_downloaded') {
        setDownloadState({
          status: 'downloaded',
          downloadUrl: response.download_url
        });
        notification.success('文件已存在');
        return;
      }
      
      // 开始轮询下载状态
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await mediaApi.getDownloadStatus(message.id);
          
          if (statusResponse.status === 'downloaded') {
            setDownloadState({
              status: 'downloaded',
              downloadUrl: statusResponse.download_url
            });
            notification.success('文件下载完成');
            clearInterval(pollInterval);
          } else if (statusResponse.status === 'download_failed') {
            setDownloadState({
              status: 'error',
              error: statusResponse.error || '下载失败'
            });
            notification.error('下载失败: ' + (statusResponse.error || '未知错误'));
            clearInterval(pollInterval);
          }
          // 继续轮询其他状态
        } catch (error) {
          console.error('轮询下载状态失败:', error);
          setDownloadState({
            status: 'error',
            error: '获取下载状态失败'
          });
          clearInterval(pollInterval);
        }
      }, 2000); // 每2秒轮询一次
      
      // 设置超时
      setTimeout(() => {
        clearInterval(pollInterval);
        if (downloadState.status === 'downloading') {
          setDownloadState({
            status: 'error',
            error: '下载超时'
          });
          notification.error('下载超时，请重试');
        }
      }, 60000); // 60秒超时
      
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
    console.log('MediaDownloadPreview - handlePreview called', {
      messageId: message.id,
      downloadState,
      onPreview: !!onPreview,
      mediaType: message.media_type,
      mediaPath: message.media_path,
      mediaDownloaded: message.media_downloaded
    });
    
    // 检查是否有可用的媒体URL
    const hasMediaUrl = downloadState.downloadUrl || (message.media_downloaded && message.media_path);
    const mediaUrlForPreview = downloadState.downloadUrl || message.media_path;
    
    if (hasMediaUrl && mediaUrlForPreview) {
      if (onPreview) {
        console.log('MediaDownloadPreview - calling onPreview with URL:', mediaUrlForPreview);
        onPreview(mediaUrlForPreview);
      } else {
        console.log('MediaDownloadPreview - opening preview modal');
        // 打开预览模态框
        setShowPreviewModal(true);
      }
    } else {
      console.log('MediaDownloadPreview - media not downloaded, starting download');
      // 需要先下载
      handleDownload();
    }
  };

  // 获取完整的媒体URL（与MediaPreview组件保持一致）
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
    // 检查是否有可用的媒体URL（优先检查实际状态）
    const hasMediaUrl = downloadState.downloadUrl || (message.media_downloaded && message.media_path);
    const isActuallyDownloaded = hasMediaUrl || downloadState.status === 'downloaded';
    
    console.log('renderDownloadStatus called', {
      downloadStateStatus: downloadState.status,
      hasMediaUrl,
      isActuallyDownloaded,
      messageMediaDownloaded: message.media_downloaded
    });
    
    // 如果实际上已经下载，显示预览按钮
    if (isActuallyDownloaded) {
      const mediaUrlForDownload = downloadState.downloadUrl || message.media_path;
      return (
        <div className="download-actions">
          <Button 
            type="primary" 
            icon={<EyeOutlined />}
            onClick={(e) => {
              console.log('MediaDownloadPreview - preview button clicked', e);
              handlePreview();
            }}
            style={{ marginRight: 8 }}
            size="small"
          >
            预览
          </Button>
          {mediaUrlForDownload && (
            <Button 
              icon={<DownloadOutlined />}
              href={getFullMediaUrl(mediaUrlForDownload)}
              download={message.media_filename || undefined}
              target="_blank"
              size="small"
            >
              下载
            </Button>
          )}
        </div>
      );
    }
    
    switch (downloadState.status) {
      case 'downloading':
        return (
          <div className="download-progress">
            <Card size="small" style={{ width: '100%', textAlign: 'center' }}>
              <Spin 
                indicator={<LoadingOutlined style={{ fontSize: 18 }} spin />}
                tip={
                  <div>
                    <div>下载中...</div>
                    {downloadState.downloadedSize && downloadState.totalSize && (
                      <div style={{ fontSize: '11px', color: '#8c8c8c', marginTop: 4 }}>
                        {formatFileSize(downloadState.downloadedSize)} / {formatFileSize(downloadState.totalSize)}
                      </div>
                    )}
                  </div>
                }
              >
                <div style={{ height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {downloadState.progress !== undefined && (
                    <Progress
                      percent={downloadState.progress}
                      size="small"
                      style={{ width: '120px' }}
                      strokeColor={{
                        '0%': '#108ee9',
                        '100%': '#87d068',
                      }}
                    />
                  )}
                </div>
              </Spin>
            </Card>
          </div>
        );
        
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

  // 渲染媒体缩略图（对于已下载的图片和视频）
  const renderMediaThumbnail = () => {
    // 检查是否有可用的媒体URL（已下载或有路径）
    const hasMediaUrl = downloadState.downloadUrl || (message.media_downloaded && message.media_path);
    const mediaUrl = downloadState.downloadUrl || message.media_path;
    
    console.log('renderMediaThumbnail called', {
      hasMediaUrl,
      mediaUrl,
      downloadStatus: downloadState.status,
      messageMediaDownloaded: message.media_downloaded,
      messageMediaPath: message.media_path
    });
    
    if (!hasMediaUrl || !mediaUrl) {
      return (
        <div className="media-icon">
          {getMediaIcon(message.media_type || 'document')}
        </div>
      );
    }

    const fullUrl = getFullMediaUrl(mediaUrl);

    switch (message.media_type) {
      case 'photo':
        return (
          <div className="media-thumbnail" onClick={(e) => {
            console.log('MediaDownloadPreview - photo thumbnail clicked', e);
            handlePreview();
          }} style={{ cursor: 'pointer' }}>
            <img 
              src={fullUrl} 
              alt={message.media_filename || '图片'}
              style={{ 
                width: '100%', 
                height: '100%', 
                objectFit: 'cover', 
                borderRadius: '8px' 
              }}
              onError={(e) => {
                console.error('Thumbnail load error:', e, 'URL:', fullUrl);
                // 回退到图标显示
                e.currentTarget.style.display = 'none';
                e.currentTarget.parentElement!.innerHTML = getMediaIcon(message.media_type || 'document')?.props?.children || '';
              }}
              onLoad={() => {
                console.log('Thumbnail loaded successfully');
              }}
            />
            <div className="thumbnail-overlay">
              <EyeOutlined style={{ color: 'white', fontSize: '16px' }} />
            </div>
          </div>
        );
      case 'video':
        return (
          <div className="media-thumbnail" onClick={(e) => {
            console.log('MediaDownloadPreview - video thumbnail clicked', e);
            handlePreview();
          }} style={{ cursor: 'pointer' }}>
            <video 
              src={fullUrl}
              style={{ 
                width: '100%', 
                height: '100%', 
                objectFit: 'cover', 
                borderRadius: '6px' 
              }}
              muted
              preload="metadata"
              onError={(e) => {
                console.error('Video thumbnail load error:', e, 'URL:', fullUrl);
                // 回退到图标显示
                e.currentTarget.style.display = 'none';
                e.currentTarget.parentElement!.innerHTML = getMediaIcon(message.media_type || 'document')?.props?.children || '';
              }}
            />
            <div className="thumbnail-overlay">
              <PlayCircleOutlined style={{ color: 'white', fontSize: '20px' }} />
            </div>
          </div>
        );
      default:
        return (
          <div className="media-icon">
            {getMediaIcon(message.media_type || 'document')}
          </div>
        );
    }
  };

  return (
    <>
      <div className={`media-download-preview ${className}`}>
        {/* 媒体信息 */}
        <div className="media-info">
          {renderMediaThumbnail()}
          
          <div className="media-details">
            <div className="media-filename">
              {message.media_filename || `${message.media_type}_${message.id}`}
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