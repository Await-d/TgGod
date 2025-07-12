import React, { useState } from 'react';
import { Card, Row, Col, Typography, Space, Switch, Button, Divider } from 'antd';
import MediaPreview from '../components/Chat/MediaPreview';
import MediaDownloadOverlay from '../components/Chat/MediaDownloadOverlay';
import { MediaDownloadStatus } from '../hooks/useMediaDownload';

const { Title, Text } = Typography;

const MediaDownloadTestPage: React.FC = () => {
  const [showDownloaded, setShowDownloaded] = useState(false);
  
  // 模拟下载状态数据
  const mockStatuses: Record<string, MediaDownloadStatus> = {
    not_downloaded: {
      status: 'not_downloaded',
      progress: 0
    },
    downloading: {
      status: 'downloading', 
      progress: 65
    },
    downloaded: {
      status: 'downloaded',
      progress: 100
    },
    download_failed: {
      status: 'download_failed',
      progress: 0,
      error: '网络连接超时'
    },
    file_missing: {
      status: 'file_missing',
      progress: 0
    }
  };

  const testMediaItems = [
    {
      id: 1,
      type: 'image' as const,
      filename: 'test-image.jpg',
      size: 1500000, // 1.5MB
      url: 'media/photos/test.jpg'
    },
    {
      id: 2,
      type: 'video' as const,
      filename: 'test-video.mp4',
      size: 5000000, // 5MB
      url: 'media/videos/test.mp4'
    },
    {
      id: 3,
      type: 'image' as const,
      filename: 'large-photo.png',
      size: 8500000, // 8.5MB
      url: 'media/photos/large.png'
    },
    {
      id: 4,
      type: 'video' as const,
      filename: 'demo-video.mov',
      size: 12000000, // 12MB
      url: 'media/videos/demo.mov'
    }
  ];

  const handleDownload = () => {
    console.log('Download clicked');
  };

  const handleRetry = () => {
    console.log('Retry clicked');
  };

  return (
    <div style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <Title level={2}>媒体文件下载功能测试</Title>
        <Text type="secondary">
          测试不同下载状态的媒体文件显示效果
        </Text>

        <div style={{ marginTop: 24, marginBottom: 16 }}>
          <Space>
            <Text>显示已下载状态:</Text>
            <Switch 
              checked={showDownloaded} 
              onChange={setShowDownloaded}
              checkedChildren="已下载"
              unCheckedChildren="未下载"
            />
          </Space>
        </div>

        <Divider />

        {/* 下载状态遮罩层演示 */}
        <Title level={3}>下载状态遮罩层演示</Title>
        <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
          {Object.entries(mockStatuses).map(([statusKey, status]) => (
            <Col xs={24} sm={12} md={8} lg={6} key={statusKey}>
              <Card 
                title={`状态: ${statusKey}`}
                size="small"
                style={{ height: '100%' }}
              >
                <div style={{ 
                  position: 'relative', 
                  width: 200, 
                  height: 150, 
                  background: '#f0f0f0',
                  borderRadius: 8,
                  margin: '0 auto 16px'
                }}>
                  <MediaDownloadOverlay
                    mediaType="photo"
                    downloadStatus={status}
                    fileName="test-image.jpg"
                    fileSize={1500000}
                    isLoading={statusKey === 'downloading'}
                    onDownload={handleDownload}
                    onRetry={handleRetry}
                  />
                </div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  进度: {status.progress}%
                  {status.error && <><br/>错误: {status.error}</>}
                </Text>
              </Card>
            </Col>
          ))}
        </Row>

        <Divider />

        {/* 媒体预览组件演示 */}
        <Title level={3}>媒体预览组件演示</Title>
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          集成了下载状态管理的媒体预览组件
        </Text>

        <Row gutter={[16, 16]}>
          {testMediaItems.map((item) => (
            <Col xs={24} sm={12} md={8} lg={6} key={item.id}>
              <Card 
                title={`${item.type === 'image' ? '图片' : '视频'}: ${item.filename}`}
                size="small"
                style={{ height: '100%' }}
              >
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
                  <MediaPreview
                    messageId={item.id}
                    url={item.url}
                    type={item.type}
                    filename={item.filename}
                    size={item.size}
                    downloaded={showDownloaded}
                  />
                </div>
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    文件大小: {(item.size / 1024 / 1024).toFixed(2)} MB
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    下载状态: {showDownloaded ? '已下载' : '未下载'}
                  </Text>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>

        <Divider />

        {/* 功能说明 */}
        <Title level={3}>功能说明</Title>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <Card title="下载状态" size="small">
              <Space direction="vertical" size="small">
                <Text><strong>not_downloaded:</strong> 显示下载按钮和文件信息</Text>
                <Text><strong>downloading:</strong> 显示圆形进度条和下载进度</Text>
                <Text><strong>downloaded:</strong> 正常显示媒体内容</Text>
                <Text><strong>download_failed:</strong> 显示错误信息和重试按钮</Text>
                <Text><strong>file_missing:</strong> 显示文件丢失提示</Text>
              </Space>
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="交互功能" size="small">
              <Space direction="vertical" size="small">
                <Text>• 点击下载按钮开始下载</Text>
                <Text>• 下载中显示实时进度</Text>
                <Text>• 支持取消下载操作</Text>
                <Text>• 下载失败可重试</Text>
                <Text>• 已下载文件可直接预览</Text>
              </Space>
            </Card>
          </Col>
        </Row>

        <div style={{ marginTop: 32 }}>
          <Button type="primary" onClick={() => window.location.reload()}>
            刷新页面
          </Button>
        </div>
      </div>
    </div>
  );
};

export default MediaDownloadTestPage;