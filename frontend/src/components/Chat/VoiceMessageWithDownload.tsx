import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Button, Progress, Space, message as antMessage, Slider, Tooltip } from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  AudioOutlined,
  DownloadOutlined,
  SoundOutlined,
  FastForwardOutlined,
  FastBackwardOutlined,
  MutedOutlined
} from '@ant-design/icons';
import { useMediaDownload } from '../../hooks/useMediaDownload';
import MediaDownloadOverlay from './MediaDownloadOverlay';
import './EnhancedVoiceMessage.css';

// 获取完整的媒体URL
const getMediaUrl = (path: string): string => {
  if (!path) return '';

  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }

  // 如果路径以 media/ 开头，直接使用 /media/ 前缀（静态文件服务）
  if (path.startsWith('media/')) {
    return `/${path}`;
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

// 格式化时间
const formatTime = (seconds: number): string => {
  if (!isFinite(seconds) || seconds < 0) return '0:00';

  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

interface EnhancedVoiceMessageProps {
  messageId?: number; // 消息ID用于下载状态追踪
  url: string;
  duration?: number;
  filename?: string;
  size?: string | number;
  downloaded?: boolean; // 是否已下载
  className?: string;
  compact?: boolean;
  waveformData?: number[];
}

const EnhancedVoiceMessage: React.FC<EnhancedVoiceMessageProps> = ({
  messageId,
  url,
  duration = 0,
  filename,
  size,
  downloaded = false,
  className = '',
  compact = false,
  waveformData
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [audioDuration, setAudioDuration] = useState(duration);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const audioRef = useRef<HTMLAudioElement>(null);

  // 下载状态管理
  const {
    downloadStatus,
    isLoading: isDownloadLoading,
    startDownload,
    retryDownload
  } = useMediaDownload({
    messageId: messageId || 0,
    autoRefresh: messageId ? !downloaded : false,
    onDownloadComplete: (filePath) => {
      antMessage.success('语音文件下载完成');
    },
    onDownloadError: (error) => {
      antMessage.error(`下载失败: ${error}`);
    }
  });

  const mediaUrl = getMediaUrl(url);
  const formattedSize = size ? formatFileSize(size) : undefined;

  // 判断是否应该显示音频控件
  const shouldShowAudio = downloaded || downloadStatus.status === 'downloaded';

  // 音频事件处理
  const handleLoadedData = useCallback(() => {
    if (audioRef.current) {
      setAudioDuration(audioRef.current.duration || duration);
      setLoading(false);
    }
  }, [duration]);

  const handleTimeUpdate = useCallback(() => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  }, []);

  const handleEnded = useCallback(() => {
    setIsPlaying(false);
    setCurrentTime(0);
  }, []);

  const handleError = useCallback(() => {
    setError(true);
    setLoading(false);
    setIsPlaying(false);
  }, []);

  // 播放/暂停
  const handlePlayPause = useCallback(async () => {
    if (!audioRef.current || !shouldShowAudio) return;

    try {
      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        setLoading(true);
        await audioRef.current.play();
        setIsPlaying(true);
        setLoading(false);
      }
    } catch (err) {
      console.error('Audio play error:', err);
      setError(true);
      setLoading(false);
    }
  }, [isPlaying, shouldShowAudio]);

  // 跳转
  const handleSkip = useCallback((seconds: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = Math.max(0, Math.min(audioDuration, currentTime + seconds));
    }
  }, [currentTime, audioDuration]);

  // 设置音量
  const handleVolumeChange = useCallback((value: number) => {
    setVolume(value);
    if (audioRef.current) {
      audioRef.current.volume = value;
    }
  }, []);

  // 静音切换
  const handleMuteToggle = useCallback(() => {
    setIsMuted(!isMuted);
    if (audioRef.current) {
      audioRef.current.muted = !isMuted;
    }
  }, [isMuted]);

  // 进度百分比
  const progressPercent = audioDuration > 0 ? (currentTime / audioDuration) * 100 : 0;

  // 渲染波形
  const renderWaveform = () => {
    if (compact || !waveformData) return null;

    const bars = waveformData || Array.from({ length: 30 }, () => Math.random() * 100);
    const playedBars = Math.floor((progressPercent / 100) * bars.length);

    return (
      <div className="waveform-container">
        <div className="waveform">
          {bars.map((height, index) => (
            <div
              key={index}
              className={`waveform-bar ${index <= playedBars ? 'played' : ''}`}
              style={{ height: `${Math.max(height * 0.6, 20)}%` }}
            />
          ))}
        </div>
      </div>
    );
  };

  // 处理下载
  const handleDownload = useCallback(async () => {
    if (!shouldShowAudio) {
      startDownload();
      return;
    }

    try {
      const response = await fetch(mediaUrl);
      if (!response.ok) throw new Error('下载失败');

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename || 'voice.ogg';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);

      antMessage.success('文件下载完成');
    } catch (error) {
      antMessage.error('下载失败，请检查网络连接');
      console.error('Download failed:', error);
    }
  }, [mediaUrl, filename, shouldShowAudio, startDownload]);

  if (error) {
    return (
      <div className={`enhanced-voice-message error ${className}`}>
        <div className="voice-error">
          <AudioOutlined style={{ color: '#ff4d4f' }} />
          <span>音频加载失败</span>
          <Button size="small" onClick={handleDownload}>
            <DownloadOutlined /> 下载
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={`enhanced-voice-message ${isPlaying ? 'playing' : ''} ${compact ? 'compact' : ''} ${className}`} style={{ position: 'relative' }}>
      {shouldShowAudio && (
        <audio
          ref={audioRef}
          src={mediaUrl}
          preload="metadata"
          onLoadedData={handleLoadedData}
          onTimeUpdate={handleTimeUpdate}
          onEnded={handleEnded}
          onError={handleError}
        />
      )}

      {shouldShowAudio ? (
        <div className="voice-content">
          {/* 主要控制区域 */}
          <div className="voice-main-controls">
            <Button
              type="text"
              icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
              size={compact ? "middle" : "large"}
              onClick={handlePlayPause}
              className="play-button"
              loading={loading}
              disabled={error}
            />

            <div className="voice-progress-area">
              {/* 波形或进度条 */}
              {renderWaveform()}

              {/* 进度条（紧凑模式或作为备选） */}
              {(compact || !waveformData) && (
                <div className="progress-container">
                  <Progress
                    percent={progressPercent}
                    showInfo={false}
                    strokeColor="#1890ff"
                    trailColor="rgba(0, 0, 0, 0.1)"
                    size="small"
                    className="voice-progress"
                  />
                </div>
              )}

              <div className="voice-time-info">
                <span className="current-time">{formatTime(currentTime)}</span>
                <span className="separator">/</span>
                <span className="total-time">{formatTime(audioDuration)}</span>
              </div>
            </div>
          </div>

          {/* 扩展控制区域（非紧凑模式） */}
          {!compact && (
            <div className="voice-extended-controls">
              <Space size="small">
                <Tooltip title="快退10秒">
                  <Button
                    type="text"
                    icon={<FastBackwardOutlined />}
                    size="small"
                    onClick={() => handleSkip(-10)}
                    disabled={!audioDuration}
                  />
                </Tooltip>

                <Tooltip title="快进10秒">
                  <Button
                    type="text"
                    icon={<FastForwardOutlined />}
                    size="small"
                    onClick={() => handleSkip(10)}
                    disabled={!audioDuration}
                  />
                </Tooltip>

                <Tooltip title={isMuted ? "取消静音" : "静音"}>
                  <Button
                    type="text"
                    icon={isMuted ? <MutedOutlined /> : <SoundOutlined />}
                    size="small"
                    onClick={handleMuteToggle}
                  />
                </Tooltip>

                <div className="volume-control">
                  <Slider
                    min={0}
                    max={1}
                    step={0.1}
                    value={volume}
                    onChange={handleVolumeChange}
                    tooltip={{ formatter: (value) => `${Math.round((value || 0) * 100)}%` }}
                    style={{ width: 60 }}
                  />
                </div>

                <Button
                  type="text"
                  icon={<DownloadOutlined />}
                  size="small"
                  onClick={handleDownload}
                  className="download-button"
                >
                  下载
                </Button>
              </Space>
            </div>
          )}
        </div>
      ) : (
        <>
          {/* 语音文件占位符 */}
          <div className="voice-placeholder" style={{
            width: '100%',
            height: compact ? 50 : 80,
            background: '#f5f5f5',
            borderRadius: 25,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12
          }}>
            <AudioOutlined style={{ fontSize: 20, color: '#d9d9d9' }} />
            <span style={{ color: '#999', fontSize: 14 }}>语音消息</span>
            {formattedSize && (
              <span style={{ color: '#999', fontSize: 12 }}>({formattedSize})</span>
            )}
          </div>
        </>
      )}

      {/* 下载遮罩层 */}
      {!shouldShowAudio && messageId && (
        <MediaDownloadOverlay
          mediaType="audio"
          downloadStatus={downloadStatus}
          fileName={filename}
          fileSize={typeof size === 'number' ? size : undefined}
          isLoading={isDownloadLoading}
          onDownload={startDownload}
          onRetry={retryDownload}
        />
      )}
    </div>
  );
};

export default EnhancedVoiceMessage;