import React, { useState, useRef, useEffect } from 'react';
import { Button, Progress, Space, message as antMessage } from 'antd';
import { 
  PlayCircleOutlined, 
  PauseCircleOutlined, 
  AudioOutlined,
  DownloadOutlined 
} from '@ant-design/icons';
import './VoiceMessage.css';

interface VoiceMessageProps {
  url: string;
  duration?: number;
  filename?: string;
  size?: string;
  className?: string;
}

const VoiceMessage: React.FC<VoiceMessageProps> = ({
  url,
  duration = 0,
  filename,
  size,
  className
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [audioDuration, setAudioDuration] = useState(duration);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleLoadedMetadata = () => {
      setAudioDuration(audio.duration);
    };

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    const handleError = () => {
      antMessage.error('语音消息播放失败');
      setIsPlaying(false);
    };

    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
    };
  }, []);

  const handlePlayPause = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play().catch(() => {
        antMessage.error('语音消息播放失败');
      });
    }
    setIsPlaying(!isPlaying);
  };

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'voice_message.wav';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const progressPercent = audioDuration > 0 ? (currentTime / audioDuration) * 100 : 0;

  return (
    <div className={`voice-message ${className || ''}`}>
      <audio ref={audioRef} src={url} preload="metadata" />
      
      <div className="voice-content">
        <Button
          type="text"
          icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
          size="large"
          onClick={handlePlayPause}
          className="play-button"
        />
        
        <div className="voice-info">
          <div className="voice-waveform">
            <AudioOutlined style={{ marginRight: 8, color: '#1890ff' }} />
            <Progress
              percent={progressPercent}
              showInfo={false}
              strokeColor="#1890ff"
              trailColor="#f0f0f0"
              size="small"
              style={{ flex: 1 }}
            />
          </div>
          
          <div className="voice-time">
            {formatTime(currentTime)} / {formatTime(audioDuration)}
          </div>
          
          {filename && (
            <div className="voice-filename">{filename}</div>
          )}
          
          {size && (
            <div className="voice-size">{size}</div>
          )}
        </div>
        
        <Button
          type="text"
          icon={<DownloadOutlined />}
          size="small"
          onClick={handleDownload}
          className="download-button"
        />
      </div>
    </div>
  );
};

export default VoiceMessage;