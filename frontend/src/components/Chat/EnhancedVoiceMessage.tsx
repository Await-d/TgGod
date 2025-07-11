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
import './EnhancedVoiceMessage.css';

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

interface EnhancedVoiceMessageProps {
  url: string;
  duration?: number;
  filename?: string;
  size?: string | number;
  className?: string;
  compact?: boolean;
  waveformData?: number[];
}

const EnhancedVoiceMessage: React.FC<EnhancedVoiceMessageProps> = ({
  url,
  duration = 0,
  filename,
  size,
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
  const [downloading, setDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [audioBuffer, setAudioBuffer] = useState<AudioBuffer | null>(null);
  
  const audioRef = useRef<HTMLAudioElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  
  const mediaUrl = getMediaUrl(url);
  const formattedSize = size ? formatFileSize(size) : undefined;
  
  // 初始化音频上下文和分析器
  useEffect(() => {
    if (typeof window !== 'undefined' && window.AudioContext) {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
    
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);
  
  // 设置音频事件监听器
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleLoadedMetadata = () => {
      setAudioDuration(audio.duration);
      setLoading(false);
      setError(false);
    };

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    const handleError = () => {
      setError(true);
      setLoading(false);
      antMessage.error('音频文件播放失败');
      setIsPlaying(false);
    };
    
    const handleLoadStart = () => {
      setLoading(true);
    };

    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);
    audio.addEventListener('loadstart', handleLoadStart);

    return () => {
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
      audio.removeEventListener('loadstart', handleLoadStart);
    };
  }, []);
  
  // 音量控制
  useEffect(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);
  
  // 播放速度控制
  useEffect(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.playbackRate = playbackRate;
    }
  }, [playbackRate]);

  // 播放/暂停控制
  const handlePlayPause = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio) return;

    try {
      if (isPlaying) {
        audio.pause();
      } else {
        // 确保音频上下文已恢复（用户交互要求）
        if (audioContextRef.current?.state === 'suspended') {
          await audioContextRef.current.resume();
        }
        await audio.play();
      }
      setIsPlaying(!isPlaying);
    } catch (error) {
      console.error('Audio play error:', error);
      antMessage.error('音频播放失败');
      setIsPlaying(false);
    }
  }, [isPlaying]);

  // 跳转到特定时间
  const handleSeek = useCallback((time: number) => {
    const audio = audioRef.current;
    if (audio && audioDuration > 0) {
      const seekTime = Math.max(0, Math.min(time, audioDuration));
      audio.currentTime = seekTime;
      setCurrentTime(seekTime);
    }
  }, [audioDuration]);
  
  // 快进/快退
  const handleSkip = useCallback((seconds: number) => {
    const newTime = currentTime + seconds;
    handleSeek(newTime);
  }, [currentTime, handleSeek]);
  
  // 切换静音
  const handleMute = useCallback(() => {
    setIsMuted(prev => !prev);
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
      link.download = filename || 'audio.mp3';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
      antMessage.success('下载完成');
    } catch (error) {
      console.error('Download failed:', error);
      antMessage.error('下载失败，请检查网络连接');
    } finally {
      setDownloading(false);
      setDownloadProgress(0);
    }
  }, [mediaUrl, filename, downloading]);

  // 格式化时间
  const formatTime = (time: number): string => {
    if (isNaN(time)) return '0:00';
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  // 计算进度百分比
  const progressPercent = audioDuration > 0 ? (currentTime / audioDuration) * 100 : 0;
  
  // 生成简单的波形可视化
  const renderWaveform = () => {
    if (compact) return null;
    
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

  if (error) {
    return (
      <div className={`enhanced-voice-message error ${className}`}>
        <div className="voice-error">
          <AudioOutlined style={{ color: '#ff4d4f' }} />
          <span>音频加载失败</span>
          {filename && (
            <Button size="small" onClick={handleDownload} loading={downloading}>
              <DownloadOutlined /> 下载
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={`enhanced-voice-message ${isPlaying ? 'playing' : ''} ${compact ? 'compact' : ''} ${className}`}>
      <audio ref={audioRef} src={mediaUrl} preload="metadata" />
      
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
                  onClick={handleMute}
                />
              </Tooltip>
              
              <div className="volume-control">
                <Slider
                  min={0}
                  max={1}
                  step={0.1}
                  value={isMuted ? 0 : volume}
                  onChange={setVolume}
                  style={{ width: 60 }}
                  tooltip={{ formatter: (value) => `${Math.round((value || 0) * 100)}%` }}
                />
              </div>
              
              <Tooltip title="播放速度">
                <Button
                  type="text"
                  size="small"
                  onClick={() => {
                    const rates = [0.5, 0.75, 1, 1.25, 1.5, 2];
                    const currentIndex = rates.indexOf(playbackRate);
                    const nextIndex = (currentIndex + 1) % rates.length;
                    setPlaybackRate(rates[nextIndex]);
                  }}
                >
                  {playbackRate}x
                </Button>
              </Tooltip>
            </Space>
          </div>
        )}
        
        {/* 文件信息和下载 */}
        {(filename || formattedSize) && (
          <div className="voice-file-info">
            {filename && <div className="voice-filename">{filename}</div>}
            {formattedSize && <div className="voice-size">{formattedSize}</div>}
            <Button
              type="text"
              icon={<DownloadOutlined />}
              size="small"
              onClick={handleDownload}
              loading={downloading}
              className="download-button"
            >
              下载
            </Button>
          </div>
        )}
        
        {/* 下载进度 */}
        {downloading && downloadProgress > 0 && (
          <div className="download-progress">
            <Progress percent={Math.round(downloadProgress)} size="small" />
          </div>
        )}
      </div>
    </div>
  );
};

export default EnhancedVoiceMessage;