import { useState, useEffect, useCallback, useRef } from 'react';
import { message } from 'antd';

export interface MediaDownloadStatus {
  status: 'not_downloaded' | 'downloading' | 'downloaded' | 'download_failed' | 'no_media' | 'file_missing';
  progress: number; // 0-100
  error?: string;
  fileSize?: number;
  filePath?: string;
  downloadUrl?: string;
}

export interface UseMediaDownloadOptions {
  messageId: number;
  autoRefresh?: boolean; // 是否自动刷新状态
  onDownloadComplete?: (filePath: string) => void;
  onDownloadError?: (error: string) => void;
}

const API_BASE = process.env.REACT_APP_API_URL || '';

export const useMediaDownload = (options: UseMediaDownloadOptions) => {
  const { messageId, autoRefresh = true, onDownloadComplete, onDownloadError } = options;
  
  const [downloadStatus, setDownloadStatus] = useState<MediaDownloadStatus>({
    status: 'not_downloaded',
    progress: 0
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const pollIntervalRef = useRef<NodeJS.Timeout>();
  const progressIntervalRef = useRef<NodeJS.Timeout>();
  const abortControllerRef = useRef<AbortController>();

  // 获取下载状态
  const fetchDownloadStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/media/download-status/${messageId}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      const newStatus: MediaDownloadStatus = {
        status: data.status,
        progress: data.progress || (data.status === 'downloaded' ? 100 : 0),
        error: data.error,
        fileSize: data.file_size || data.total_size,
        filePath: data.file_path,
        downloadUrl: data.download_url
      };

      setDownloadStatus(newStatus);
      
      // 如果检测到正在下载状态，启动轮询监控
      if (data.status === 'downloading') {
        startPolling();
      }
      
      // 如果下载完成，触发回调
      if (data.status === 'downloaded' && data.file_path && onDownloadComplete) {
        onDownloadComplete(data.file_path);
      }
      
      // 如果下载失败，触发错误回调
      if (data.status === 'download_failed' && data.error && onDownloadError) {
        onDownloadError(data.error);
      }
      
      return data;
    } catch (error) {
      console.error('Failed to fetch download status:', error);
      setDownloadStatus(prev => ({
        ...prev,
        status: 'download_failed',
        error: error instanceof Error ? error.message : 'Unknown error'
      }));
      return null;
    }
  }, [messageId, onDownloadComplete, onDownloadError, startPolling]);

  // 开始下载
  const startDownload = useCallback(async (force = false) => {
    if (isLoading) return;
    
    setIsLoading(true);
    
    // 取消之前的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    abortControllerRef.current = new AbortController();
    
    try {
      setDownloadStatus(prev => ({
        ...prev,
        status: 'downloading',
        progress: 0,
        error: undefined
      }));

      const response = await fetch(`${API_BASE}/api/media/download/${messageId}?force=${force}`, {
        method: 'POST',
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      if (result.status === 'already_downloaded') {
        setDownloadStatus(prev => ({
          ...prev,
          status: 'downloaded',
          progress: 100,
          filePath: result.file_path,
          downloadUrl: result.download_url
        }));
        
        if (result.file_path && onDownloadComplete) {
          onDownloadComplete(result.file_path);
        }
        
        message.success('文件已存在');
      } else if (result.status === 'download_started') {
        // 开始轮询下载状态
        startPolling();
        message.info('下载已开始...');
      }
      
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('Download request was aborted');
        return;
      }
      
      console.error('Failed to start download:', error);
      setDownloadStatus(prev => ({
        ...prev,
        status: 'download_failed',
        error: error.message || 'Download failed'
      }));
      
      if (onDownloadError) {
        onDownloadError(error.message || 'Download failed');
      }
      
      message.error('下载启动失败: ' + (error.message || 'Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, [messageId, isLoading, onDownloadComplete, onDownloadError]);

  // 开始轮询状态
  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }
    
    // 模拟进度增长（因为后端没有实时进度）
    let progress = 0;
    progressIntervalRef.current = setInterval(() => {
      progress += Math.random() * 15; // 随机增长
      if (progress > 95) progress = 95; // 最多到95%，等待实际完成
      
      setDownloadStatus(prev => 
        prev.status === 'downloading' 
          ? { ...prev, progress: Math.min(progress, 95) }
          : prev
      );
    }, 500);

    // 每2秒检查一次实际状态
    pollIntervalRef.current = setInterval(async () => {
      const data = await fetchDownloadStatus();
      
      if (data && (data.status === 'downloaded' || data.status === 'download_failed')) {
        if (progressIntervalRef.current) {
          clearInterval(progressIntervalRef.current);
          progressIntervalRef.current = undefined;
        }
        stopPolling();
      }
    }, 2000);
  }, [fetchDownloadStatus]);

  // 停止轮询
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = undefined;
    }
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = undefined;
    }
  }, []);

  // 重试下载
  const retryDownload = useCallback(() => {
    startDownload(true);
  }, [startDownload]);

  // 取消下载
  const cancelDownload = useCallback(async () => {
    try {
      // 取消前端HTTP请求
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      
      // 停止轮询
      stopPolling();
      
      // 调用后端API取消下载
      const response = await fetch(`${API_BASE}/api/media/cancel-download/${messageId}`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const result = await response.json();
        
        // 更新状态为已取消
        setDownloadStatus(prev => ({
          ...prev,
          status: 'not_downloaded',
          progress: 0,
          error: undefined
        }));
        
        message.success('下载已取消');
      } else {
        // 如果后端取消失败，仍然取消前端状态
        setDownloadStatus(prev => ({
          ...prev,
          status: 'not_downloaded',
          progress: 0
        }));
        
        console.warn('后端取消下载失败，但前端状态已重置');
        message.info('下载已取消');
      }
    } catch (error) {
      console.error('取消下载时发生错误:', error);
      
      // 即使出错，也重置前端状态
      setDownloadStatus(prev => ({
        ...prev,
        status: 'not_downloaded',
        progress: 0
      }));
      
      message.info('下载已取消');
    } finally {
      setIsLoading(false);
    }
  }, [messageId, stopPolling]);

  // 初始化时获取状态
  useEffect(() => {
    if (messageId && autoRefresh) {
      fetchDownloadStatus();
    }
  }, [messageId, autoRefresh, fetchDownloadStatus]);

  // 清理
  useEffect(() => {
    return () => {
      stopPolling();
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [stopPolling]);

  return {
    downloadStatus,
    isLoading,
    startDownload,
    retryDownload,
    cancelDownload,
    refreshStatus: fetchDownloadStatus
  };
};