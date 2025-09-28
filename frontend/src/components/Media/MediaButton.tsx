import React, { useState } from 'react';
import { Button, Tooltip, message as antMessage } from 'antd';
import {
  DownloadOutlined,
  EyeOutlined,
  PlayCircleOutlined
} from '@ant-design/icons';
import { TelegramMessage } from '../../types';
import { mediaApi } from '../../services/apiService';

interface MediaButtonProps {
  message: TelegramMessage;
  action: 'preview' | 'download';
  size?: 'small' | 'middle' | 'large';
  type?: 'text' | 'link' | 'default' | 'primary' | 'dashed';
  onPreview?: () => void;
}

const MediaButton: React.FC<MediaButtonProps> = ({
  message,
  action,
  size = 'small',
  type = 'text',
  onPreview
}) => {
  const [loading, setLoading] = useState(false);


  // 下载媒体文件
  const handleDownload = async () => {
    if (!message.message_id) {
      antMessage.error('消息ID不存在');
      return;
    }

    setLoading(true);

    try {
      const result = await mediaApi.downloadMedia(message.group_id, message.message_id);
      
      if (result.status === 'success' || result.status === 'exists') {
        antMessage.success('下载完成！');
        if (result.download_url) {
          // 触发文件下载
          const link = document.createElement('a');
          link.href = result.download_url;
          link.download = message.media_filename || `media_${message.message_id}`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }
      } else if (result.status === 'downloading') {
        antMessage.info('文件正在下载中，请稍候...');
      } else {
        antMessage.error(result.message || '下载失败');
      }
    } catch (error: any) {
      antMessage.error(`下载失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 预览媒体
  const handlePreview = () => {
    if (onPreview) {
      onPreview();
    }
  };

  // 检查是否为可预览的媒体类型
  const isPreviewable = ['photo', 'video'].includes(message.media_type || '');

  if (action === 'preview' && !isPreviewable) {
    return null;
  }

  const icon = action === 'preview' ?
    (message.media_type === 'video' ? <PlayCircleOutlined /> : <EyeOutlined />) :
    <DownloadOutlined />;

  return (
    <Tooltip title={action === 'preview' ? '预览' : '下载'}>
      <Button
        type={type}
        size={size}
        icon={icon}
        loading={loading}
        onClick={action === 'preview' ? handlePreview : handleDownload}
      />
    </Tooltip>
  );
};

export default MediaButton;