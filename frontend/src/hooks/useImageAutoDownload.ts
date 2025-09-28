import { useEffect, useState } from 'react';
import { TelegramMessage } from '../types';
import { mediaApi } from '../services/apiService';

interface AutoDownloadOptions {
  maxSize?: number; // 最大文件大小 (字节)，默认2MB
  enabled?: boolean; // 是否启用自动下载，默认true
}

interface AutoDownloadState {
  isAutoDownloading: boolean;
  downloadProgress: number;
  downloadUrl: string | null;
  error: string | null;
}

/**
 * 自动下载小图片的Hook
 * 用于自动下载小于指定大小的图片文件
 */
export const useImageAutoDownload = (
  message: TelegramMessage,
  options: AutoDownloadOptions = {}
) => {
  const {
    maxSize = 2 * 1024 * 1024, // 默认2MB
    enabled = true
  } = options;

  const [state, setState] = useState<AutoDownloadState>({
    isAutoDownloading: false,
    downloadProgress: 0,
    downloadUrl: null,
    error: null
  });

  useEffect(() => {
    // 检查是否需要自动下载
    const shouldAutoDownload = () => {
      if (!enabled) return false;
      if (!message.media_type || message.media_type !== 'photo') return false;
      if (!message.media_size) return false;
      if (message.media_size > maxSize) return false;
      if (message.media_downloaded) return false; // 已经下载过的不需要重复下载
      return true;
    };

    if (!shouldAutoDownload()) {
      return;
    }

    // 开始自动下载
    const startAutoDownload = async () => {
      try {
        setState(prev => ({
          ...prev,
          isAutoDownloading: true,
          downloadProgress: 0,
          error: null
        }));

        // 检查是否已有可用的下载URL
        if (message.media_filename) {
          const mediaUrl = `/api/media/download/${message.group_id}/${message.message_id}`;
          
          // 检查文件是否可访问
          try {
            const response = await fetch(mediaUrl, { method: 'HEAD' });
            if (response.ok) {
              setState(prev => ({
                ...prev,
                isAutoDownloading: false,
                downloadProgress: 100,
                downloadUrl: mediaUrl
              }));
              return;
            }
          } catch (error) {
            // 文件不存在，继续下载流程
          }
        }

        // 开始下载文件
        const downloadResponse = await mediaApi.downloadMedia(
          message.group_id,
          message.message_id,
          {
            onProgress: (progress: number) => {
              setState(prev => ({
                ...prev,
                downloadProgress: progress
              }));
            }
          }
        );

        if (downloadResponse.success) {
          setState(prev => ({
            ...prev,
            isAutoDownloading: false,
            downloadProgress: 100,
            downloadUrl: downloadResponse.download_url || downloadResponse.file_path || null
          }));
        } else {
          throw new Error(downloadResponse.message || '下载失败');
        }
      } catch (error) {
        console.error('自动下载图片失败:', error);
        setState(prev => ({
          ...prev,
          isAutoDownloading: false,
          downloadProgress: 0,
          error: error instanceof Error ? error.message : '下载失败'
        }));
      }
    };

    startAutoDownload();
  }, [message.message_id, message.group_id, message.media_type, message.media_size, message.media_downloaded, message.media_filename, maxSize, enabled]);

  return {
    ...state,
    // 辅助方法
    isEligibleForAutoDownload: message.media_type === 'photo' && 
                               message.media_size && 
                               message.media_size <= maxSize,
    fileSizeMB: message.media_size ? (message.media_size / 1024 / 1024).toFixed(2) : '0'
  };
};