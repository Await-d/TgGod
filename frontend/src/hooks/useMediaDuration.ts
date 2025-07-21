import { useState, useEffect, useCallback } from 'react';
import { TelegramMessage } from '../types';

interface MediaDurationState {
  totalDuration: number; // 总时长（秒）
  audioCount: number;    // 音频文件数量
  videoCount: number;    // 视频文件数量
  voiceCount: number;    // 语音消息数量
  isLoading: boolean;    // 加载状态
}

interface UseMediaDurationProps {
  messages: TelegramMessage[];
  enabled?: boolean;
}

export const useMediaDuration = ({ messages, enabled = true }: UseMediaDurationProps) => {
  const [state, setState] = useState<MediaDurationState>({
    totalDuration: 0,
    audioCount: 0,
    videoCount: 0,
    voiceCount: 0,
    isLoading: false
  });

  // 获取媒体文件时长
  const getMediaDuration = useCallback((url: string, type: 'audio' | 'video'): Promise<number> => {
    return new Promise((resolve) => {
      const element = type === 'audio' ? new Audio() : document.createElement('video');
      
      const handleLoadedMetadata = () => {
        const duration = element.duration || 0;
        cleanup();
        resolve(isFinite(duration) ? duration : 0);
      };

      const handleError = () => {
        cleanup();
        resolve(0);
      };

      const cleanup = () => {
        element.removeEventListener('loadedmetadata', handleLoadedMetadata);
        element.removeEventListener('error', handleError);
        if ('pause' in element) {
          element.pause();
        }
      };

      element.addEventListener('loadedmetadata', handleLoadedMetadata);
      element.addEventListener('error', handleError);
      
      // 设置超时，避免长时间等待
      setTimeout(() => {
        cleanup();
        resolve(0);
      }, 5000);

      element.src = url;
      if (type === 'video') {
        element.load();
      }
    });
  }, []);

  // 计算总时长
  const calculateTotalDuration = useCallback(async () => {
    if (!enabled || !messages.length) {
      setState({
        totalDuration: 0,
        audioCount: 0,
        videoCount: 0,
        voiceCount: 0,
        isLoading: false
      });
      return;
    }

    setState(prev => ({ ...prev, isLoading: true }));

    let totalDuration = 0;
    let audioCount = 0;
    let videoCount = 0;
    let voiceCount = 0;

    // 创建所有媒体文件的时长获取任务
    const durationPromises = messages.map(async (message) => {
      // 处理语音消息
      if (message.voice) {
        voiceCount++;
        // 语音消息的时长通常在 voice.duration 字段中
        if (message.voice.duration) {
          return message.voice.duration;
        }
        
        // 如果没有duration字段，尝试从文件获取
        if (message.voice.file_path) {
          const audioUrl = `${process.env.REACT_APP_API_URL || ''}/api/media/download/${message.id}`;
          return await getMediaDuration(audioUrl, 'audio');
        }
      }

      // 处理音频文件
      if (message.audio) {
        audioCount++;
        if (message.audio.duration) {
          return message.audio.duration;
        }
        
        if (message.audio.file_path) {
          const audioUrl = `${process.env.REACT_APP_API_URL || ''}/api/media/download/${message.id}`;
          return await getMediaDuration(audioUrl, 'audio');
        }
      }

      // 处理视频文件
      if (message.video) {
        videoCount++;
        if (message.video.duration) {
          return message.video.duration;
        }
        
        if (message.video.file_path) {
          const videoUrl = `${process.env.REACT_APP_API_URL || ''}/api/media/download/${message.id}`;
          return await getMediaDuration(videoUrl, 'video');
        }
      }

      return 0;
    });

    try {
      // 等待所有时长计算完成
      const durations = await Promise.all(durationPromises);
      totalDuration = durations.reduce((sum, duration) => sum + duration, 0);

      setState({
        totalDuration,
        audioCount,
        videoCount,
        voiceCount,
        isLoading: false
      });
    } catch (error) {
      console.error('Failed to calculate media duration:', error);
      setState(prev => ({ ...prev, isLoading: false }));
    }
  }, [messages, enabled, getMediaDuration]);

  // 当消息列表变化时重新计算
  useEffect(() => {
    calculateTotalDuration();
  }, [calculateTotalDuration]);

  // 格式化时长显示
  const formatDuration = useCallback((seconds: number): string => {
    if (!seconds || seconds === 0) return '0分';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}小时${minutes}分`;
    } else if (minutes > 0) {
      return `${minutes}分${remainingSeconds > 0 ? `${remainingSeconds}秒` : ''}`;
    } else {
      return `${remainingSeconds}秒`;
    }
  }, []);

  return {
    ...state,
    formatDuration,
    refresh: calculateTotalDuration
  };
};