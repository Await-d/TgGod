import React, { useState } from 'react';
import { Card, Row, Col, Typography, Space, Switch, Button, Divider, Tabs } from 'antd';
import MediaPreview from '../components/Chat/MediaPreview';
import EnhancedMediaPreview from '../components/Chat/EnhancedMediaPreview';
import VoiceMessageWithDownload from '../components/Chat/VoiceMessageWithDownload';
import MediaDownloadOverlay from '../components/Chat/MediaDownloadOverlay';
import { MediaDownloadStatus } from '../hooks/useMediaDownload';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

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
      type: 'audio' as const,
      filename: 'test-audio.mp3',
      size: 3200000, // 3.2MB
      url: 'media/audios/test.mp3'
    },
    {
      id: 4,
      type: 'document' as const,
      filename: 'test-document.txt',
      size: 85000, // 85KB
      url: 'media/documents/test.txt'
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
      <div style={{ maxWidth: 1400, margin: '0 auto' }}>
        <Title level={2}>媒体文件按需下载系统测试</Title>
        <Text type="secondary">
          完整测试所有媒体组件的下载功能，包括图片、视频、音频和文档
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

        <Tabs defaultActiveKey="1" type="card">
          <TabPane tab="下载遮罩演示" key="1">
            <Title level={3}>下载状态遮罩层演示</Title>
            <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
              {Object.entries(mockStatuses).map(([statusKey, status]) => (
                <Col xs={24} sm={12} md={8} lg={6} xl={4} key={statusKey}>
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
          </TabPane>

          <TabPane tab="MediaPreview 组件" key="2">
            <Title level={3}>MediaPreview 组件测试</Title>
            <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              基础媒体预览组件，支持图片和视频
            </Text>
            <Row gutter={[16, 16]}>
              {testMediaItems.filter(item => ['image', 'video'].includes(item.type)).map((item) => (
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
                        type={item.type as 'image' | 'video'}
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
          </TabPane>

          <TabPane tab="EnhancedMediaPreview 组件" key="3">
            <Title level={3}>EnhancedMediaPreview 增强媒体预览</Title>
            <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              支持所有媒体类型的增强预览组件
            </Text>
            <Row gutter={[16, 16]}>
              {testMediaItems.map((item) => (
                <Col xs={24} sm={12} md={8} lg={6} key={item.id}>
                  <Card 
                    title={`${item.filename}`}
                    size="small"
                    style={{ height: '100%' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
                      <EnhancedMediaPreview
                        messageId={item.id}
                        mediaType={item.type}
                        mediaPath={showDownloaded ? item.url : undefined}
                        filename={item.filename}
                        size={item.size}
                        downloaded={showDownloaded}
                        thumbnail={true}
                      />
                    </div>
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        类型: {item.type.toUpperCase()}
                      </Text>
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
          </TabPane>

          <TabPane tab="语音消息组件" key="4">
            <Title level={3}>VoiceMessage 语音消息组件</Title>
            <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              专门的语音消息播放和下载组件
            </Text>
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} md={8}>
                <Card title="紧凑模式语音消息" size="small">
                  <VoiceMessageWithDownload
                    messageId={5}
                    url="media/audios/test.mp3"
                    duration={120}
                    filename="voice-message.ogg"
                    size={850000}
                    downloaded={showDownloaded}
                    compact={true}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={8}>
                <Card title="完整模式语音消息" size="small">
                  <VoiceMessageWithDownload
                    messageId={6}
                    url="media/audios/test.mp3"
                    duration={180}
                    filename="long-voice.ogg"
                    size={1200000}
                    downloaded={showDownloaded}
                    compact={false}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={8}>
                <Card title="带波形语音消息" size="small">
                  <VoiceMessageWithDownload
                    messageId={7}
                    url="media/audios/test.mp3"
                    duration={90}
                    filename="waveform-voice.ogg"
                    size={650000}
                    downloaded={showDownloaded}
                    compact={false}
                    waveformData={Array.from({ length: 40 }, () => Math.random() * 100)}
                  />
                </Card>
              </Col>
            </Row>
          </TabPane>

          <TabPane tab="不同状态对比" key="5">
            <Title level={3}>不同下载状态对比</Title>
            <Row gutter={[16, 16]}>
              {Object.entries(mockStatuses).map(([statusKey, status]) => (
                <Col xs={24} lg={12} xl={8} key={statusKey}>
                  <Card title={`状态: ${statusKey}`} size="small">
                    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                      {/* 图片预览 */}
                      <div>
                        <Text strong>图片预览:</Text>
                        <div style={{ marginTop: 8, position: 'relative', display: 'inline-block' }}>
                          <div style={{ 
                            width: 120, 
                            height: 80, 
                            background: '#f5f5f5',
                            borderRadius: 8,
                            position: 'relative'
                          }}>
                            <MediaDownloadOverlay
                              mediaType="photo"
                              downloadStatus={status}
                              fileName="test.jpg"
                              fileSize={1500000}
                              isLoading={statusKey === 'downloading'}
                              onDownload={handleDownload}
                              onRetry={handleRetry}
                            />
                          </div>
                        </div>
                      </div>

                      {/* 语音消息 */}
                      <div>
                        <Text strong>语音消息:</Text>
                        <div style={{ marginTop: 8, position: 'relative' }}>
                          <div style={{
                            width: '100%',
                            height: 50,
                            background: '#f5f5f5',
                            borderRadius: 25,
                            position: 'relative'
                          }}>
                            <MediaDownloadOverlay
                              mediaType="audio"
                              downloadStatus={status}
                              fileName="voice.ogg"
                              fileSize={850000}
                              isLoading={statusKey === 'downloading'}
                              onDownload={handleDownload}
                              onRetry={handleRetry}
                            />
                          </div>
                        </div>
                      </div>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          </TabPane>
        </Tabs>

        <Divider />

        {/* 功能说明 */}
        <Title level={3}>功能说明</Title>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
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
          <Col xs={24} md={8}>
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
          <Col xs={24} md={8}>
            <Card title="支持的媒体类型" size="small">
              <Space direction="vertical" size="small">
                <Text>• 📷 图片 (JPG, PNG, GIF等)</Text>
                <Text>• 🎥 视频 (MP4, MOV, AVI等)</Text>
                <Text>• 🎵 音频 (MP3, OGG, WAV等)</Text>
                <Text>• 🎤 语音消息 (OGG, M4A等)</Text>
                <Text>• 📄 文档 (TXT, PDF, DOC等)</Text>
              </Space>
            </Card>
          </Col>
        </Row>

        <div style={{ marginTop: 32, textAlign: 'center' }}>
          <Space size="large">
            <Button type="primary" onClick={() => window.location.reload()}>
              刷新页面
            </Button>
            <Button onClick={() => setShowDownloaded(!showDownloaded)}>
              切换下载状态
            </Button>
          </Space>
        </div>
      </div>
    </div>
  );
};

export default MediaDownloadTestPage;