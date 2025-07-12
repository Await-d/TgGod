import React, { useState } from 'react';
import { Card, Space, Input, Button, Typography, Divider } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import MessageHighlight from '../components/Chat/MessageHighlight';
import MediaPreview from '../components/Chat/MediaPreview';
import VoiceMessage from '../components/Chat/VoiceMessage';
import MessageQuoteForward, { QuotedMessage } from '../components/Chat/MessageQuoteForward';
import '../components/Chat/MediaPreview.css';
import '../components/Chat/VoiceMessage.css';
import '../components/Chat/MessageQuoteForward.css';

const { Title, Text } = Typography;

const NewFeaturesDemo: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [quotedMessage, setQuotedMessage] = useState<any>(null);

  // 模拟消息数据
  const sampleMessage = {
    id: 1,
    group_id: 1,
    message_id: 1,
    sender_name: '张三',
    text: '这是一条包含关键词的示例消息，用于演示搜索高亮功能。',
    date: '2023-12-01T10:30:00Z',
    created_at: '2023-12-01T10:30:00Z',
    is_forwarded: false,
    is_pinned: false,
    media_type: undefined
  };

  // 模拟联系人数据
  const sampleContacts = [
    { id: '1', name: '李四', type: 'user' as const },
    { id: '2', name: '王五', type: 'user' as const },
    { id: '3', name: '技术讨论组', type: 'group' as const },
    { id: '4', name: '项目组', type: 'group' as const },
  ];

  const handleQuote = (message: any) => {
    setQuotedMessage(message);
  };

  const handleForward = (message: any, targets: string[], comment?: string) => {
    console.log('转发消息:', message, '到:', targets, '评论:', comment);
  };

  const handleRemoveQuote = () => {
    setQuotedMessage(null);
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <Title level={2}>新功能演示</Title>
      
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 消息搜索高亮 */}
        <Card title="消息搜索高亮" size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input
              placeholder="输入搜索关键词..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              prefix={<SearchOutlined />}
              style={{ marginBottom: 16 }}
            />
            <div style={{ background: '#f8f9fa', padding: '12px', borderRadius: '8px' }}>
              <Text strong>消息内容：</Text>
              <div style={{ marginTop: 8 }}>
                <MessageHighlight
                  content={sampleMessage.text || ''}
                  searchTerm={searchTerm}
                />
              </div>
            </div>
          </Space>
        </Card>

        {/* 图片/视频预览 */}
        <Card title="图片/视频预览" size="small">
          <Space direction="vertical" size="middle">
            <div>
              <Text strong>图片预览：</Text>
              <MediaPreview
                messageId={1}
                url="https://via.placeholder.com/300x200/4A90E2/ffffff?text=Sample+Image"
                type="image"
                filename="sample-image.jpg"
                size="245 KB"
                downloaded={true}
              />
            </div>
            <div>
              <Text strong>视频预览：</Text>
              <MediaPreview
                messageId={2}
                url="https://www.w3schools.com/html/mov_bbb.mp4"
                type="video"
                filename="sample-video.mp4"
                size="2.1 MB"
                downloaded={true}
              />
            </div>
          </Space>
        </Card>

        {/* 语音消息 */}
        <Card title="语音消息支持" size="small">
          <Space direction="vertical" size="middle">
            <div>
              <Text strong>语音消息：</Text>
              <VoiceMessage
                url="https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"
                duration={15}
                filename="voice-message.wav"
                size="156 KB"
              />
            </div>
          </Space>
        </Card>

        {/* 消息引用和转发 */}
        <Card title="消息引用和转发" size="small">
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <Text strong>原始消息：</Text>
              <div style={{ 
                background: '#f8f9fa', 
                padding: '12px', 
                borderRadius: '8px',
                marginTop: 8,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start'
              }}>
                <div>
                  <div style={{ fontWeight: 500, marginBottom: 4 }}>
                    {sampleMessage.sender_name}
                  </div>
                  <div>{sampleMessage.text}</div>
                </div>
                <MessageQuoteForward
                  message={sampleMessage}
                  contacts={sampleContacts}
                  onQuote={handleQuote}
                  onForward={handleForward}
                />
              </div>
            </div>
            
            {quotedMessage && (
              <div>
                <Text strong>引用消息预览：</Text>
                <QuotedMessage
                  message={quotedMessage}
                  onRemove={handleRemoveQuote}
                />
              </div>
            )}
          </Space>
        </Card>

        {/* 功能说明 */}
        <Card title="功能说明" size="small">
          <Space direction="vertical" size="small">
            <div>
              <Text strong>• 消息搜索高亮：</Text>
              <Text>实时高亮显示搜索关键词，支持大小写不敏感匹配</Text>
            </div>
            <div>
              <Text strong>• 图片/视频预览：</Text>
              <Text>缩略图预览，点击放大查看，支持下载功能</Text>
            </div>
            <div>
              <Text strong>• 语音消息：</Text>
              <Text>音频播放控制，进度条显示，支持播放/暂停/下载</Text>
            </div>
            <div>
              <Text strong>• 消息引用转发：</Text>
              <Text>支持引用消息回复，多选转发到联系人或群组</Text>
            </div>
          </Space>
        </Card>
      </Space>
    </div>
  );
};

export default NewFeaturesDemo;