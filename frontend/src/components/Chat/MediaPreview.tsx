import React, { useState } from 'react';
import { Modal, Image, Button, Space } from 'antd';
import { EyeOutlined, DownloadOutlined, PlayCircleOutlined } from '@ant-design/icons';

interface MediaPreviewProps {
  url: string;
  type: 'image' | 'video';
  filename?: string;
  size?: string;
  className?: string;
}

const MediaPreview: React.FC<MediaPreviewProps> = ({
  url,
  type,
  filename,
  size,
  className
}) => {
  const [previewVisible, setPreviewVisible] = useState(false);

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (type === 'image') {
    return (
      <div className={`media-preview ${className || ''}`}>
        <div className="media-thumbnail" onClick={() => setPreviewVisible(true)}>
          <Image
            src={url}
            alt={filename}
            style={{ maxWidth: 200, maxHeight: 150, objectFit: 'cover' }}
            preview={false}
          />
          <div className="media-overlay">
            <EyeOutlined style={{ fontSize: 24, color: 'white' }} />
          </div>
        </div>
        <div className="media-info">
          <div className="media-filename">{filename}</div>
          {size && <div className="media-size">{size}</div>}
          <Space>
            <Button 
              type="text" 
              icon={<EyeOutlined />} 
              size="small"
              onClick={() => setPreviewVisible(true)}
            >
              预览
            </Button>
            <Button 
              type="text" 
              icon={<DownloadOutlined />} 
              size="small"
              onClick={handleDownload}
            >
              下载
            </Button>
          </Space>
        </div>
        
        <Modal
          visible={previewVisible}
          footer={null}
          onCancel={() => setPreviewVisible(false)}
          width="80%"
          style={{ maxWidth: 800 }}
        >
          <Image src={url} alt={filename} style={{ width: '100%' }} />
        </Modal>
      </div>
    );
  }

  if (type === 'video') {
    return (
      <div className={`media-preview ${className || ''}`}>
        <div className="video-thumbnail" onClick={() => setPreviewVisible(true)}>
          <video
            src={url}
            style={{ maxWidth: 200, maxHeight: 150, objectFit: 'cover' }}
            muted
          />
          <div className="media-overlay">
            <PlayCircleOutlined style={{ fontSize: 32, color: 'white' }} />
          </div>
        </div>
        <div className="media-info">
          <div className="media-filename">{filename}</div>
          {size && <div className="media-size">{size}</div>}
          <Space>
            <Button 
              type="text" 
              icon={<PlayCircleOutlined />} 
              size="small"
              onClick={() => setPreviewVisible(true)}
            >
              播放
            </Button>
            <Button 
              type="text" 
              icon={<DownloadOutlined />} 
              size="small"
              onClick={handleDownload}
            >
              下载
            </Button>
          </Space>
        </div>
        
        <Modal
          visible={previewVisible}
          footer={null}
          onCancel={() => setPreviewVisible(false)}
          width="80%"
          style={{ maxWidth: 800 }}
        >
          <video 
            src={url} 
            controls 
            style={{ width: '100%', maxHeight: '70vh' }}
            autoPlay
          />
        </Modal>
      </div>
    );
  }

  return null;
};

export default MediaPreview;